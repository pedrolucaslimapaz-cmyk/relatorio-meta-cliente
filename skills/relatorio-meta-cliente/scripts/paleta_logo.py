#!/usr/bin/env python3
"""
Lê as cores da logo e monta 3 paletas prontas para o relatório (PDF + HTML),
todas com contraste conferido (texto legível e destaque visível nos dois fundos).

Uso:
  paleta_logo.py --identidade <slug>                    gera paletas.json na pasta da identidade e imprime
  paleta_logo.py --identidade <slug> --aplicar 2        grava a paleta 2 na identidade.json
  paleta_logo.py --identidade <slug> --hex "#0A2540,#FF7A00" --aplicar hex
                                                        monta a paleta a partir dos códigos informados

Lê a logo com Pillow; se Pillow faltar ou a logo for SVG, usa o Chromium do Playwright.
"""

from __future__ import annotations

import argparse
import base64
import colorsys
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _comum import agora_iso, gravar_json, ler_json, pasta_config  # noqa: E402

# ------------------------------------------------------------------ cor e contraste

def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if not re.fullmatch(r"[0-9a-fA-F]{6}", h):
        raise ValueError(f"código de cor inválido: #{h}")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_hex(rgb) -> str:
    return "#" + "".join(f"{max(0, min(255, round(c))):02X}" for c in rgb)


def luminancia(rgb) -> float:
    def canal(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (canal(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a, b) -> float:
    la, lb = sorted((luminancia(a), luminancia(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def hls(rgb):
    return colorsys.rgb_to_hls(*(c / 255 for c in rgb))


def de_hls(h, l, s):
    return tuple(c * 255 for c in colorsys.hls_to_rgb(h, max(0, min(1, l)), max(0, min(1, s))))


def ajustar_contraste(cor, fundo, alvo: float):
    """Escurece ou clareia `cor` (mantendo o matiz) até atingir `alvo` contra `fundo`."""
    if contraste(cor, fundo) >= alvo:
        return cor
    h, l, s = hls(cor)
    clarear = luminancia(fundo) < 0.2
    for _ in range(100):
        l = l + 0.01 if clarear else l - 0.01
        c = de_hls(h, l, s)
        if contraste(c, fundo) >= alvo or l <= 0 or l >= 1:
            return c
    return cor


def texto_sobre(cor) -> str:
    return "#FFFFFF" if contraste(cor, (255, 255, 255)) >= contraste(cor, (17, 17, 17)) else "#111111"


def tingir(base, matiz_de, quanto: float):
    """Mistura um pouco do matiz da marca num neutro (fundos que 'conversam' com a logo)."""
    return tuple(b * (1 - quanto) + m * quanto for b, m in zip(base, matiz_de))


# ------------------------------------------------------------------ leitura da logo

def pixels_pillow(caminho: Path):
    from PIL import Image
    img = Image.open(caminho).convert("RGBA")
    img.thumbnail((96, 96))
    return list(img.getdata())


def pixels_chromium(caminho: Path):
    from playwright.sync_api import sync_playwright
    mime = {".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg", ".webp": "image/webp"}[caminho.suffix.lower()]
    uri = f"data:{mime};base64," + base64.b64encode(caminho.read_bytes()).decode()
    js = """async (uri) => {
      const img = new Image(); img.src = uri; await img.decode();
      const w = 96, h = Math.max(1, Math.round(96 * (img.naturalHeight || 96) / (img.naturalWidth || 96)));
      const c = document.createElement('canvas'); c.width = w; c.height = h;
      const x = c.getContext('2d'); x.drawImage(img, 0, 0, w, h);
      return Array.from(x.getImageData(0, 0, w, h).data);
    }"""
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        dados = pg.evaluate(js, uri)
        b.close()
    return [tuple(dados[i:i + 4]) for i in range(0, len(dados), 4)]


def ler_pixels(caminho: Path):
    if caminho.suffix.lower() != ".svg":
        try:
            return pixels_pillow(caminho)
        except ImportError:
            pass
    return pixels_chromium(caminho)


def analisar_logo(caminho: Path) -> dict:
    px = [p for p in ler_pixels(caminho) if p[3] >= 160]
    if not px:
        return {"cores": [], "logo_clara": False, "logo_escura": False, "transparente": True}
    transparente = len(px) < 0.9 * len(ler_pixels(caminho)) if caminho.suffix.lower() == ".png" else False
    baldes = Counter((p[0] // 24, p[1] // 24, p[2] // 24) for p in px)
    soma: dict = {}
    for p in px:
        k = (p[0] // 24, p[1] // 24, p[2] // 24)
        s = soma.setdefault(k, [0, 0, 0])
        s[0] += p[0]; s[1] += p[1]; s[2] += p[2]
    cores = []
    for k, n in baldes.most_common(40):
        rgb = tuple(v / n for v in soma[k])
        h, l, s = hls(rgb)
        cores.append({"hex": rgb_hex(rgb), "peso": round(n / len(px), 3),
                      "saturada": s > 0.25 and 0.12 < l < 0.9})
    # une cores quase iguais
    unicas = []
    for c in cores:
        if all(contraste(hex_rgb(c["hex"]), hex_rgb(u["hex"])) > 1.35 for u in unicas):
            unicas.append(c)
        else:
            for u in unicas:
                if contraste(hex_rgb(c["hex"]), hex_rgb(u["hex"])) <= 1.35:
                    u["peso"] = round(u["peso"] + c["peso"], 3)
                    break
    lum_media = sum(luminancia(p[:3]) * 1 for p in px) / len(px)
    return {"cores": unicas[:6], "logo_clara": lum_media > 0.6, "logo_escura": lum_media < 0.25,
            "transparente": transparente}


# ------------------------------------------------------------------ paletas

BRANCO, QUASE_PRETO = (255, 255, 255), (17, 19, 24)
SUGESTOES_NEUTRAS = ["#1D4ED8", "#0F766E", "#B45309"]


def montar(marca_rgb, destaque_rgb, tema_html: str, header_neutro: bool) -> dict:
    fundo_pdf = BRANCO
    fundo_html = tingir((14, 16, 21), destaque_rgb, 0.05) if tema_html == "escuro" else (250, 250, 251)
    sup_html = tingir((24, 27, 34), destaque_rgb, 0.06) if tema_html == "escuro" else (255, 255, 255)
    txt_html = (243, 244, 246) if tema_html == "escuro" else (20, 22, 26)
    suave_html = (160, 166, 178) if tema_html == "escuro" else (94, 100, 112)
    linha_html = (42, 46, 55) if tema_html == "escuro" else (226, 228, 232)
    faixa = QUASE_PRETO if header_neutro else marca_rgb
    return {
        "marca": rgb_hex(faixa),
        "sobre_marca": texto_sobre(faixa),
        "positivo": "#15803D", "negativo": "#B42318",
        "pdf": {
            "fundo": rgb_hex(fundo_pdf), "superficie": rgb_hex(tingir((244, 245, 247), destaque_rgb, 0.04)),
            "texto": "#14161A", "texto_suave": "#5E6470", "linha": "#E2E4E8",
            "destaque": rgb_hex(ajustar_contraste(destaque_rgb, fundo_pdf, 3.2)),
        },
        "html": {
            "fundo": rgb_hex(fundo_html), "superficie": rgb_hex(sup_html),
            "texto": rgb_hex(txt_html), "texto_suave": rgb_hex(suave_html), "linha": rgb_hex(linha_html),
            "destaque": rgb_hex(ajustar_contraste(destaque_rgb, sup_html, 3.2)),
        },
    }


def paletas_da_logo(info: dict) -> list[dict]:
    saturadas = [hex_rgb(c["hex"]) for c in info["cores"] if c["saturada"]]
    escuras = [hex_rgb(c["hex"]) for c in info["cores"] if luminancia(hex_rgb(c["hex"])) < 0.08]
    monocromatica = not saturadas
    principal = saturadas[0] if saturadas else hex_rgb(SUGESTOES_NEUTRAS[0])
    segunda = saturadas[1] if len(saturadas) > 1 else (escuras[0] if escuras else None)
    base_marca = escuras[0] if escuras else principal

    ps = [
        {"id": 1, "nome": "Marca em destaque",
         "descricao": "Faixa do topo e números principais na cor mais forte da logo. PDF claro, HTML escuro.",
         "cores": montar(principal, principal, "escuro", False), "html_tema": "escuro"},
        {"id": 2, "nome": "Sóbrio",
         "descricao": "Base quase preta, a cor da logo só nos números e gráficos. Visual mais executivo.",
         "cores": montar(principal, principal, "escuro", True), "html_tema": "escuro"},
    ]
    if segunda is not None and contraste(segunda, principal) > 1.4:
        ps.append({"id": 3, "nome": "Duas cores da logo",
                   "descricao": "Faixa na segunda cor da logo e destaque na principal. HTML claro.",
                   "cores": montar(segunda if segunda != base_marca or escuras else base_marca, principal, "claro", False),
                   "html_tema": "claro"})
    else:
        ps.append({"id": 3, "nome": "Claro nos dois formatos",
                   "descricao": "Fundo claro também no HTML, cor da logo na faixa e nos destaques.",
                   "cores": montar(principal, principal, "claro", False), "html_tema": "claro"})
    if monocromatica:
        for p, sug in zip(ps, SUGESTOES_NEUTRAS):
            p["cores"] = montar(QUASE_PRETO, hex_rgb(sug), p["html_tema"], True)
            p["descricao"] = (f"A logo é monocromática, então sugeri {sug} como cor de destaque. "
                              + p["descricao"].split(". ", 1)[-1])
    return ps


def paleta_hex(codigos: list[str]) -> dict:
    cores = [hex_rgb(c) for c in codigos if c.strip()]
    if not cores:
        raise ValueError("informe ao menos um código de cor, ex.: #0A2540")
    marca = cores[0]
    destaque = cores[1] if len(cores) > 1 else cores[0]
    return {"id": "hex", "nome": "Cores informadas", "descricao": "Montada com os códigos que você passou.",
            "cores": montar(marca, destaque, "escuro", False), "html_tema": "escuro"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--identidade", required=True)
    ap.add_argument("--aplicar")
    ap.add_argument("--hex")
    a = ap.parse_args()

    pasta = pasta_config() / "identidades" / a.identidade
    ident = ler_json(pasta / "identidade.json")
    if ident is None:
        print(f"Identidade '{a.identidade}' não encontrada em {pasta}.", file=sys.stderr)
        return 2

    try:
        if a.hex:
            paletas = [paleta_hex(a.hex.split(","))]
            info = None
        else:
            logo = pasta / (ident.get("logo") or "")
            if not ident.get("logo") or not logo.exists():
                print("A identidade ainda não tem logo. Rode 'config.py identidade-nova' primeiro.", file=sys.stderr)
                return 2
            info = analisar_logo(logo)
            paletas = paletas_da_logo(info)
    except ValueError as e:
        print(f"Erro: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # Pillow e Chromium ausentes, imagem corrompida…
        py = "python" if sys.platform == "win32" else "python3"
        if isinstance(e, ImportError):
            motivo = (f"falta o Pillow ou o Playwright no computador. Para ler as cores sozinho, instale um deles: "
                      f"{py} -m pip install pillow")
        elif "Executable doesn't exist" in str(e) or "playwright install" in str(e):
            motivo = f"o navegador do Playwright não está instalado. Instale com: {py} -m playwright install chromium"
        else:
            motivo = "o arquivo da logo não abriu (pode estar corrompido ou num formato diferente da extensão)"
        print(f"Não consegui ler as cores da logo: {motivo}.\n"
              "Outra saída: informe os códigos das cores da marca (ex.: #0A2540,#FF7A00) e rode com --hex.",
              file=sys.stderr)
        return 3

    gravar_json(pasta / "paletas.json", {"gerado_em": agora_iso(), "logo": info, "paletas": paletas})

    if a.aplicar:
        escolha = next((p for p in paletas if str(p["id"]) == str(a.aplicar)), None)
        if escolha is None:
            print(f"Paleta '{a.aplicar}' não existe.", file=sys.stderr)
            return 2
        ident["cores"] = escolha["cores"]
        ident.setdefault("html", {})["tema"] = escolha["html_tema"]
        if info is not None:
            ident["logo_fundo"] = "escuro" if info["logo_clara"] else ("claro" if info["logo_escura"] else "auto")
        ident["cores_aprovadas"] = True
        ident["paleta_nome"] = escolha["nome"]
        ident["atualizado_em"] = agora_iso()
        gravar_json(pasta / "identidade.json", ident)
        print(f"OK: paleta '{escolha['nome']}' aplicada em {a.identidade}")
        return 0

    print(json.dumps({"logo": info, "paletas": [{k: p[k] for k in ("id", "nome", "descricao", "html_tema")}
                                                 | {"marca": p["cores"]["marca"],
                                                    "destaque_pdf": p["cores"]["pdf"]["destaque"],
                                                    "destaque_html": p["cores"]["html"]["destaque"]}
                                                 for p in paletas]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
