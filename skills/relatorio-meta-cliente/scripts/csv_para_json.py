#!/usr/bin/env python3
"""
Converte o CSV (ou XLSX) exportado do Gerenciador de Anúncios em um relatorio.json
parcial, no formato que o montar_relatorio.py entende.

Uso:
  csv_para_json.py <arquivo.csv|xlsx> --saida dados.json [--cliente "Nome"] [--moeda BRL]
                   [--campanha "trecho do nome"]   (filtra só as campanhas que contêm o trecho)

Aceita cabeçalhos em português ou inglês, vírgula ou ponto decimal (com ou sem ponto de
milhar, como fica depois de salvar no Excel em português), separador , ; ou tab, datas
AAAA-MM-DD ou DD/MM/AAAA, e UTF-8/UTF-16/Latin-1. Linhas por dia (coluna "Dia") viram série
diária. Códigos do Meta no tipo de resultado ("profile_visit_view") viram texto legível.

O que não der para ler vira item em "limitacoes" — nada é estimado.
Saída 0 = ok · 2 = arquivo ilegível · 4 = nenhuma coluna reconhecida.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import unicodedata
from collections import OrderedDict, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _comum import agora_iso, gravar_json  # noqa: E402


def norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", t).strip()


# chave interna -> padrões (regex sobre o cabeçalho normalizado)
COLUNAS = OrderedDict([
    ("campanha", [r"^nome da campanha$", r"^campaign name$", r"^campanha$"]),
    ("conjunto", [r"^nome do conjunto de anuncios$", r"^ad set name$"]),
    ("anuncio", [r"^nome do anuncio$", r"^ad name$"]),
    ("dia", [r"^dia$", r"^day$", r"^data$", r"^date$"]),
    ("inicio", [r"^inicio dos relatorios$", r"^reporting starts$"]),
    ("fim", [r"^termino dos relatorios$", r"^encerramento dos relatorios$", r"^reporting ends$"]),
    ("tipo_resultado", [r"^tipo de resultado$", r"^indicador de resultados?$", r"^result type$", r"^result indicator$"]),
    ("investimento", [r"^valor usado", r"^amount spent", r"^valor gasto"]),
    ("custo_por_resultado", [r"^custo por resultado", r"^cost per result"]),
    ("resultados", [r"^resultados$", r"^results$"]),
    ("alcance", [r"^alcance$", r"^reach$"]),
    ("impressoes", [r"^impressoes$", r"^impressions$"]),
    ("frequencia", [r"^frequencia$", r"^frequency$"]),
    ("cliques_link", [r"^cliques no link$", r"^link clicks$"]),
    ("ctr", [r"^ctr \(taxa de cliques no link\)", r"^ctr \(link click-through rate\)"]),
    ("cpc", [r"^cpc \(custo por clique no link\)", r"^cpc \(cost per link click\)"]),
    ("cpm", [r"^cpm"]),
    ("valor_compras", [r"^valor de conversao (de|das) compras", r"^purchases conversion value",
                       r"^valor de conversao da compra( no site)?$",
                       r"^valor de conversao de compras no site", r"^website purchases conversion value"]),
    ("roas", [r"^roas (de|das) compras", r"^purchase roas", r"^roas de compras no site", r"^website purchase roas",
              r"^roas de resultados", r"^results roas"]),
    ("compras", [r"^compras$", r"^purchases$", r"^compras no site$", r"^website purchases$"]),
    ("leads", [r"^leads$", r"^leads no site$", r"^website leads$", r"^cadastros$"]),
    ("thruplays", [r"^thruplays$", r"^reproducoes do video ate 15 segundos", r"^thruplay"]),
    ("engajamentos", [r"^engajamento com a publicacao$", r"^post engagements?$"]),
])
SOMAVEIS = ["investimento", "resultados", "impressoes", "cliques_link", "valor_compras", "compras",
            "leads", "thruplays", "engajamentos"]
CONTAGENS = {"resultados", "alcance", "impressoes", "cliques_link", "compras", "leads", "thruplays", "engajamentos"}

# indicador de resultado (código do Meta) -> rótulo para o cliente
INDICADORES = {
    "offsite_conversion.fb_pixel_purchase": "compras", "purchase": "compras", "omni_purchase": "compras",
    "onsite_web_purchase": "compras", "onsite_conversion.purchase": "compras",
    "offsite_conversion.fb_pixel_lead": "leads", "lead": "leads", "leads": "leads",
    "onsite_conversion.lead_grouped": "leads", "onsite_conversion.lead": "leads",
    "onsite_conversion.messaging_conversation_started_7d": "conversas iniciadas",
    "profile_visit_view": "visitas ao perfil", "link_click": "cliques no link", "link_clicks": "cliques no link",
    "landing_page_view": "visualizações da página de destino", "reach": "pessoas alcançadas",
    "impressions": "impressões", "post_engagement": "engajamentos com a publicação",
    "video_thruplay_watched_actions": "ThruPlays", "thruplay": "ThruPlays", "page_like": "curtidas na página",
    "like": "curtidas na página", "offsite_conversion.fb_pixel_add_to_cart": "adições ao carrinho",
    "offsite_conversion.fb_pixel_initiate_checkout": "finalizações de compra iniciadas",
    "offsite_conversion.fb_pixel_complete_registration": "cadastros concluídos",
}


def rotulo_indicador(bruto: str) -> str | None:
    """Texto do cliente para o tipo de resultado. None = código do Meta sem tradução conhecida."""
    t = str(bruto or "").strip()
    chave = re.sub(r"^actions?:", "", t.lower())
    if chave in INDICADORES:
        return INDICADORES[chave]
    if " " not in chave and re.search(r"[:_.]", chave):
        return None
    return t.lower() or None


def data_iso(bruto) -> str:
    """AAAA-MM-DD a partir de AAAA-MM-DD, DD/MM/AAAA, DD/MM/AA (ou MM/DD/AAAA quando não houver dúvida)."""
    t = str(bruto or "").strip()
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", t)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.match(r"^(\d{1,2})[/.](\d{1,2})[/.](\d{2}|\d{4})\b", t)
    if m:
        a, b, ano = int(m.group(1)), int(m.group(2)), int(m.group(3))
        ano += 2000 if ano < 100 else 0
        for dia, mes in ((a, b), (b, a)):  # pt-BR primeiro
            try:
                return date(ano, mes, dia).isoformat()
            except ValueError:
                continue
    return t[:10]


def usa_virgula_decimal(linhas: list[dict], colunas: list[str]) -> bool:
    """Arquivo salvo no Excel em português: vírgula decimal e ponto de milhar."""
    for l in linhas:
        for c in colunas:
            t = re.sub(r"[^\d,.\-]", "", str(l.get(c) or ""))
            if re.fullmatch(r"-?\d{1,3}(\.\d{3})*,\d+|-?\d+,\d{1,2}", t):
                return True
    return False


def num(txt, contagem=False, virgula_decimal=False):
    if txt is None:
        return None
    if isinstance(txt, (int, float)):
        return float(txt)
    t = str(txt).strip()
    if t in ("", "-", "—", "–", "N/A", "n/a"):
        return None
    t = re.sub(r"[^\d,.\-]", "", t)
    if not t or t in ("-", ".", ","):
        return None
    if "." in t and "," not in t and (virgula_decimal or contagem) and re.fullmatch(r"-?\d{1,3}(\.\d{3})+", t):
        t = t.replace(".", "")  # "34.567" = 34567 (ponto de milhar)
    if "," in t and "." in t:
        if t.rfind(",") > t.rfind("."):
            t = t.replace(".", "").replace(",", ".")
        else:
            t = t.replace(",", "")
    elif "," in t:
        # "1,234,567" = milhar em inglês; "1234,56" ou "1,5" = decimal em português
        t = t.replace(",", "") if re.fullmatch(r"-?\d{1,3}(,\d{3}){2,}", t) else t.replace(",", ".")
        if t.count(".") > 1:
            return None
    elif t.count(".") > 1:
        t = t.replace(".", "")
    try:
        return float(t)
    except ValueError:
        return None


def ler_linhas(caminho: Path) -> list[dict]:
    if caminho.suffix.lower() in (".xlsx", ".xlsm"):
        try:
            import openpyxl
        except ImportError:
            raise RuntimeError("Para ler XLSX instale o openpyxl (pip3 install openpyxl) ou exporte como CSV.")
        wb = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
        ws = wb.active
        linhas = list(ws.iter_rows(values_only=True))
        cab = [str(c or "").strip() for c in linhas[0]]
        return [dict(zip(cab, l)) for l in linhas[1:] if any(v not in (None, "") for v in l)]
    bruto = caminho.read_bytes()
    # UTF-16 só com BOM ou com bytes nulos: senão um arquivo Latin-1 de tamanho par
    # "decodifica" como UTF-16 e vira lixo (CSV salvo no Excel em português)
    if bruto[:2] in (b"\xff\xfe", b"\xfe\xff"):
        encs = ("utf-16",)
    elif bruto.count(b"\x00") > len(bruto) // 4:
        encs = ("utf-16-le", "utf-16-be")
    else:
        encs = ("utf-8-sig", "cp1252", "latin-1")
    for enc in encs:
        try:
            texto = bruto.decode(enc)
            if "\x00" in texto:
                continue
            break
        except UnicodeDecodeError:
            continue
    else:
        raise RuntimeError("não consegui descobrir a codificação do arquivo")
    amostra = texto[:5000]
    delim = max([",", ";", "\t"], key=lambda d: amostra.splitlines()[0].count(d) if amostra else 0)
    leitor = csv.DictReader(io.StringIO(texto), delimiter=delim)
    return [dict(l) for l in leitor if any((v or "").strip() for v in l.values() if isinstance(v, str))]


def mapear(cabecalhos) -> tuple[dict, list[str], str | None]:
    mapa, sobras, moeda = {}, [], None
    for c in cabecalhos:
        n = norm(c)
        chave = next((k for k, pads in COLUNAS.items() if k not in mapa and any(re.search(p, n) for p in pads)), None)
        if chave:
            mapa[chave] = c
            m = re.search(r"\(([A-Z]{3})\)", c or "")
            if chave == "investimento" and m:
                moeda = m.group(1)
        elif c:
            sobras.append(c)
    # quando o arquivo traz as duas versões, prefere o valor de todas as compras ao "só no site"
    geral = next((c for c in cabecalhos if norm(c) == "valor de conversao da compra"), None)
    if geral and mapa.get("valor_compras") != geral:
        sobras.append(mapa["valor_compras"])
        mapa["valor_compras"] = geral
        sobras.remove(geral) if geral in sobras else None
    return mapa, sobras, moeda


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("arquivo")
    ap.add_argument("--saida", required=True)
    ap.add_argument("--cliente")
    ap.add_argument("--moeda")
    ap.add_argument("--campanha")
    a = ap.parse_args()

    caminho = Path(a.arquivo).expanduser()
    if not caminho.exists():
        print(f"Arquivo não encontrado: {caminho}\nPróximo passo: confira o caminho ou arraste o arquivo para a conversa.",
              file=sys.stderr)
        return 2
    try:
        linhas = ler_linhas(caminho)
    except Exception as e:
        print(f"Não consegui ler o arquivo ({e}).\nPróximo passo: exporte de novo pelo Gerenciador em CSV.",
              file=sys.stderr)
        return 2
    if not linhas:
        print("O arquivo está vazio.", file=sys.stderr)
        return 2

    mapa, sobras, moeda_cab = mapear(list(linhas[0].keys()))
    if "investimento" not in mapa:
        print("Não reconheci as colunas desse arquivo (falta pelo menos 'Valor usado' / 'Amount spent').\n"
              f"Colunas encontradas: {', '.join(list(linhas[0].keys())[:15])}\n"
              "Próximo passo: exporte a tabela do Gerenciador de Anúncios com as colunas padrão de desempenho.",
              file=sys.stderr)
        return 4

    br = usa_virgula_decimal(linhas, [mapa[k] for k in mapa if k not in ("campanha", "conjunto", "anuncio", "dia",
                                                                      "inicio", "fim", "tipo_resultado")])

    def v(l, k):
        return num(l.get(mapa[k]), contagem=k in CONTAGENS, virgula_decimal=br) if k in mapa else None

    def txt(l, k):
        return str(l.get(mapa[k]) or "").strip() if k in mapa else ""

    limit = []   # vai para o relatório do cliente
    avisos = []  # só para o gestor, na conversa
    # linha de total (nome da campanha vazio) — o Gerenciador inclui uma no topo ou no fim
    total_meta = None
    dados = []
    for l in linhas:
        if "campanha" in mapa and not txt(l, "campanha"):
            total_meta = l
            continue
        if a.campanha and a.campanha.lower() not in txt(l, "campanha").lower():
            continue
        dados.append(l)
    if not dados and total_meta is not None:
        dados = [total_meta]
        total_meta = None
    if not dados:
        print(f"Nenhuma linha com campanha contendo '{a.campanha}'.", file=sys.stderr)
        return 2
    if a.campanha:
        total_meta = None  # o total do arquivo mistura campanhas fora do filtro

    brutos = {txt(l, "tipo_resultado") for l in dados if txt(l, "tipo_resultado")}
    tipos = {rotulo_indicador(b) or b for b in brutos}  # códigos diferentes podem ser o mesmo resultado
    resultados_misturados = len(tipos) > 1

    tot: dict = {}
    for k in SOMAVEIS:
        if k in mapa:
            vals = [v(l, k) for l in dados]
            vals = [x for x in vals if x is not None]
            tot[k] = round(sum(vals), 2) if vals else None
    if resultados_misturados:
        tot["resultados"] = None
        limit.append("As campanhas medem resultados diferentes (visitas, cliques, compras...), "
                     "então não existe um total único de \"resultados\".")
        avisos.append("Tipos de resultado encontrados: " + ", ".join(sorted(brutos)) + ".")
    elif brutos:
        rot = rotulo_indicador(next(iter(brutos)))
        if rot:
            tot["rotulo_resultado"] = rot
        else:
            avisos.append(f"Não reconheci o tipo de resultado \"{next(iter(brutos))}\": o relatório vai chamar de "
                          "\"resultados\". Se souber o nome certo, informe em totais.rotulo_resultado.")

    if total_meta is not None and "alcance" in mapa:
        tot["alcance"] = v(total_meta, "alcance")
    elif "alcance" in mapa:
        por_campanha = defaultdict(float)
        diario = "dia" in mapa
        if diario:
            limit.append("Alcance total não disponível neste recorte dos dados.")
            avisos.append("Alcance não pode ser somado dia a dia. Para ter o alcance total, exporte também "
                          "sem a divisão por dia e informe o valor em totais.alcance.")
            tot["alcance"] = None
        else:
            for l in dados:
                por_campanha[txt(l, "campanha")] += v(l, "alcance") or 0
            if len(por_campanha) > 1:
                # alcance não se soma entre campanhas (a mesma conta conta de novo): sem linha de total, fica sem
                tot["alcance"] = None
                limit.append("Alcance total não exibido: o Meta não permite somar o alcance de campanhas diferentes.")
                avisos.append("Para ter o alcance total, exporte com a linha de total do Gerenciador (ela vem por padrão) "
                              "ou informe o valor em totais.alcance.")
            else:
                tot["alcance"] = round(sum(por_campanha.values())) or None
    if total_meta is not None and "frequencia" in mapa and tot.get("alcance"):
        tot["frequencia"] = v(total_meta, "frequencia")

    # série diária
    serie = []
    if "dia" in mapa:
        por_dia = defaultdict(lambda: defaultdict(float))
        for l in dados:
            d = data_iso(txt(l, "dia"))
            for k in ("investimento", "resultados", "compras", "leads", "valor_compras", "impressoes"):
                if k in mapa and v(l, k) is not None:
                    por_dia[d][k] += v(l, k)
        for d in sorted(por_dia):
            item = {"data": d}
            item.update({k: round(x, 2) for k, x in por_dia[d].items()})
            serie.append(item)

    # por campanha
    camp = OrderedDict()
    for l in dados:
        nome = txt(l, "campanha") or "Todas as campanhas"
        c = camp.setdefault(nome, defaultdict(float))
        for k in ("investimento", "resultados", "compras", "leads", "valor_compras", "cliques_link", "impressoes"):
            if k in mapa and v(l, k) is not None:
                c[k] += v(l, k)
        if txt(l, "tipo_resultado"):
            c["_tipo"] = txt(l, "tipo_resultado")
    campanhas = []
    for nome, c in camp.items():
        item = {"nome": nome}
        item.update({k: round(x, 2) for k, x in c.items() if not k.startswith("_")})
        if c.get("_tipo") and rotulo_indicador(c["_tipo"]):
            item["rotulo_resultado"] = rotulo_indicador(c["_tipo"])
        campanhas.append(item)
    campanhas.sort(key=lambda c: c.get("investimento", 0), reverse=True)

    inicios = sorted(filter(None, (data_iso(txt(l, "inicio")) for l in dados)))
    fins = sorted(filter(None, (data_iso(txt(l, "fim")) for l in dados)))
    if serie and not inicios:
        inicios, fins = [serie[0]["data"]], [serie[-1]["data"]]

    ausentes = [k for k in ("compras", "valor_compras", "leads", "alcance", "cliques_link", "thruplays")
                if k not in mapa]
    if ausentes:
        nomes = {"compras": "compras", "valor_compras": "valor de conversão de compras", "leads": "leads",
                 "alcance": "alcance", "cliques_link": "cliques no link", "thruplays": "ThruPlays"}
        avisos.append("Colunas que não vieram no arquivo exportado: " + ", ".join(nomes[k] for k in ausentes)
                      + ". Se alguma for importante para o foco escolhido, exporte de novo com ela.")
    limit.append("Dados de exportação manual (CSV) do Gerenciador de Anúncios: sem criativos, público ou "
                 "histórico de alterações, a menos que tenham sido exportados à parte.")

    saida = {
        "schema": 1,
        "fonte": "csv",
        "arquivo_origem": caminho.name,
        "cliente": a.cliente or "",
        "moeda": a.moeda or moeda_cab or "BRL",
        "periodo": {"inicio": inicios[0] if inicios else None, "fim": fins[-1] if fins else None},
        "totais": {k: x for k, x in tot.items() if x is not None},
        "serie_diaria": serie,
        "campanhas": campanhas,
        "limitacoes": limit,
        "avisos_gestor": avisos,
        "colunas_reconhecidas": {k: mapa[k] for k in mapa},
        "colunas_ignoradas": sobras,
        "gerado_em": agora_iso(),
    }
    gravar_json(Path(a.saida), saida)
    print(json.dumps({"ok": True, "saida": a.saida, "linhas": len(dados), "campanhas": len(campanhas),
                      "dias": len(serie), "periodo": saida["periodo"], "totais": saida["totais"],
                      "limitacoes": limit, "avisos_gestor": avisos}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
