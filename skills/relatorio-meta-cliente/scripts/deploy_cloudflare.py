#!/usr/bin/env python3
"""
Publica o dashboard HTML no Cloudflare Pages da conta do próprio gestor.

Uso:
  deploy_cloudflare.py --checar
  deploy_cloudflare.py --dashboard <pasta>/dashboard/index.html --projeto <cliente> --pasta 2026-09
  deploy_cloudflare.py --despublicar --projeto <cliente> --pasta 2026-09-3f9a1c0e7b2d4a65

Como funciona:
  - Um projeto do Cloudflare Pages por cliente  →  https://<projeto>.pages.dev
  - Uma pasta por relatório                      →  https://<projeto>.pages.dev/2026-09-3f9a1c0e7b2d4a65/
    (o script acrescenta um código aleatório de 16 caracteres à pasta para o link não ser
     adivinhável; use --sem-codigo para desligar)
  - Só o index.html do dashboard é publicado. Nada mais da pasta do relatório sobe.
  - Cada deploy substitui o site inteiro, então a pasta local
    ~/.relatorio-meta-cliente/publicar/<projeto>/ guarda TODOS os relatórios já publicados
    desse cliente. Assim os links antigos continuam funcionando.

Autenticação: 'npx wrangler login' (uma vez) ou as variáveis de ambiente
CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID. O token nunca é lido, gravado nem impresso
por este script: ele só passa o ambiente adiante para o wrangler.

Saída 0 = publicado e respondendo (imprime JSON com "url")
      2 = entrada inválida · 5 = sem login no Cloudflare · 6 = deploy falhou
      7 = deploy feito mas o link não respondeu (não envie o link ainda)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shlex
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _comum import pasta_config, slug  # noqa: E402

RAIZ_HTML = """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="robots" content="noindex, nofollow"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Relatórios</title></head><body style="font-family:system-ui,sans-serif;padding:32px;color:#555">
<p>Use o link completo do relatório que você recebeu.</p></body></html>
"""
HEADERS = "/*\n  X-Robots-Tag: noindex, nofollow\n  Referrer-Policy: no-referrer\n"


def wrangler() -> list[str]:
    cmd = os.environ.get("RMC_WRANGLER")  # permite apontar para outro binário (testes, instalação global)
    if cmd:
        return [cmd] if os.path.isfile(cmd) else shlex.split(cmd)
    # caminho completo: no Windows, wrangler/npx são .cmd e o subprocess não os acha pelo nome
    if shutil.which("wrangler"):
        return [shutil.which("wrangler")]
    return [shutil.which("npx") or "npx", "--yes", "wrangler"]


def rodar(args: list[str], timeout=300):
    try:
        r = subprocess.run(wrangler() + args, capture_output=True, text=True, timeout=timeout, env=os.environ.copy())
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except FileNotFoundError:
        return 127, "wrangler/npx não encontrado"
    except subprocess.TimeoutExpired:
        return 124, "tempo esgotado"


def limpar(txt: str) -> str:
    """Tira da saída qualquer coisa com cara de token antes de mostrar."""
    return re.sub(r"[A-Za-z0-9_\-]{32,}", "[oculto]", txt)


def checar(saida=sys.stdout) -> int:
    if os.environ.get("CLOUDFLARE_API_TOKEN"):
        cod, out = rodar(["whoami"], timeout=120)
        if cod == 0:
            print("OK: autenticado no Cloudflare pela variável CLOUDFLARE_API_TOKEN.", file=saida)
            return 0
    cod, out = rodar(["whoami"], timeout=120)
    if cod == 0 and "not authenticated" not in out.lower():
        conta = re.search(r"associated with the email (\S+)", out)
        print("OK: autenticado no Cloudflare" + (f" ({conta.group(1).rstrip('.')})" if conta else "") + ".", file=saida)
        return 0
    if cod == 127:
        print("Não encontrei o Node/npx, que é necessário para publicar.\n"
              "Próximo passo: instale o Node.js 22 ou mais novo (https://nodejs.org) e rode de novo.", file=sys.stderr)
        return 5
    if "requires at least node" in out.lower():
        print("Seu Node.js é antigo para a ferramenta do Cloudflare.\n"
              "Próximo passo: instale o Node.js 22 ou mais novo (versão LTS em https://nodejs.org) e rode de novo.",
              file=sys.stderr)
        return 5
    print("Você ainda não está conectado ao Cloudflare.\n"
          "Próximo passo: rode  npx wrangler login  no terminal, autorize no navegador que abrir e volte aqui.",
          file=sys.stderr)
    return 5


def publicar(base: Path, projeto: str) -> tuple[int, str]:
    rodar(["pages", "project", "create", projeto, "--production-branch", "main"], timeout=180)
    # não é fatal se falhar: o projeto pode já existir; o deploy confirma
    return rodar(["pages", "deploy", str(base), "--project-name", projeto, "--branch", "main",
                  "--commit-dirty=true"], timeout=600)


def despublicar(projeto: str | None, pasta: str | None) -> int:
    if not (projeto and pasta):
        print("Use --despublicar com --projeto e --pasta (o nome completo da pasta, com o código).", file=sys.stderr)
        return 2
    projeto = slug(projeto)[:58].strip("-")
    base = pasta_config() / "publicar" / projeto
    alvo = base / slug(pasta)
    if not (alvo / "index.html").exists():
        existentes = sorted(p.name for p in base.iterdir() if p.is_dir()) if base.exists() else []
        print(f"Não achei o relatório publicado '{pasta}' no projeto '{projeto}'. "
              f"Publicados: {', '.join(existentes) or 'nenhum'}.", file=sys.stderr)
        return 2
    if checar(saida=sys.stderr) != 0:
        return 5
    shutil.rmtree(alvo)
    cod, out = publicar(base, projeto)
    if cod != 0:
        print(json.dumps({"ok": False, "motivo": "deploy_falhou", "detalhe": limpar(out)[-1200:]},
                         ensure_ascii=False, indent=2))
        print("Apaguei a cópia local, mas o novo deploy falhou, então o link ainda pode estar no ar. "
              "Próximo passo: rode o mesmo comando de novo.", file=sys.stderr)
        return 6
    print(json.dumps({"ok": True, "despublicado": pasta, "projeto": projeto}, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checar", action="store_true")
    ap.add_argument("--dashboard")
    ap.add_argument("--projeto")
    ap.add_argument("--pasta")
    ap.add_argument("--sem-codigo", action="store_true")
    ap.add_argument("--despublicar", action="store_true",
                    help="tira do ar a pasta --pasta (nome completo, com o código) do projeto --projeto")
    a = ap.parse_args()

    if a.checar:
        return checar()
    if a.despublicar:
        return despublicar(a.projeto, a.pasta)
    if not (a.dashboard and a.projeto and a.pasta):
        print("Use --dashboard, --projeto e --pasta (ou --checar).", file=sys.stderr)
        return 2
    arq = Path(a.dashboard).expanduser()
    if not arq.exists():
        print(f"Dashboard não encontrado: {arq}", file=sys.stderr)
        return 2
    if arq.name != "index.html" or arq.parent.name != "dashboard":
        print("Só publico o dashboard gerado pelo montar_relatorio.py (<pasta do relatório>/dashboard/index.html). "
              f"Recebi: {arq.name}", file=sys.stderr)
        return 2

    projeto = slug(a.projeto)[:58].strip("-")
    pasta = slug(a.pasta) + ("" if a.sem_codigo else "-" + secrets.token_hex(8))
    base = pasta_config() / "publicar" / projeto
    (base / pasta).mkdir(parents=True, exist_ok=True)
    # só o index.html: o dashboard é autossuficiente, e o que estiver ao lado dele
    # (relatorio.json, mensagem, PNG de conferência) não pode virar público
    shutil.copy2(arq, base / pasta / "index.html")
    if not (base / "index.html").exists():
        (base / "index.html").write_text(RAIZ_HTML, encoding="utf-8")
    (base / "_headers").write_text(HEADERS, encoding="utf-8")

    if checar(saida=sys.stderr) != 0:
        shutil.rmtree(base / pasta, ignore_errors=True)
        print(json.dumps({"ok": False, "motivo": "sem_login", "arquivo_local": str(arq)}, ensure_ascii=False))
        return 5

    cod, out = publicar(base, projeto)
    if cod != 0:
        shutil.rmtree(base / pasta, ignore_errors=True)  # não deixa relatório não entregue subir no próximo deploy
        print(json.dumps({"ok": False, "motivo": "deploy_falhou", "detalhe": limpar(out)[-1200:],
                          "arquivo_local": str(arq)}, ensure_ascii=False, indent=2))
        print("O deploy no Cloudflare falhou. O relatório continua salvo como arquivo local "
              f"({arq}). Próximo passo: veja o detalhe acima; se for login, rode  npx wrangler login.",
              file=sys.stderr)
        return 6

    m = re.search(r"https://[a-z0-9]+\.([a-z0-9\-]+)\.pages\.dev", out)
    dominio = f"{m.group(1)}.pages.dev" if m else f"{projeto}.pages.dev"
    url = f"https://{dominio}/{pasta}/"

    status = None
    for _ in range(8):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, method="GET"), timeout=15) as r:
                status = r.status
        except urllib.error.HTTPError as e:
            status = e.code
        except Exception:
            status = None
        if status == 200:
            break
        time.sleep(4)
    if status != 200:
        print(json.dumps({"ok": False, "motivo": "link_nao_respondeu", "url_esperada": url, "http": status,
                          "arquivo_local": str(arq)}, ensure_ascii=False, indent=2))
        print("O deploy terminou, mas o link ainda não respondeu. Não envie esse link ao cliente antes de abrir "
              "e conferir. Pode levar 1 a 2 minutos na primeira publicação do projeto.", file=sys.stderr)
        return 7

    print(json.dumps({"ok": True, "url": url, "projeto": projeto, "pasta": pasta,
                      "pasta_local_publicada": str(base)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
