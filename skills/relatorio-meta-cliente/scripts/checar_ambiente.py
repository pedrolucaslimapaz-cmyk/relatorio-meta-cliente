#!/usr/bin/env python3
"""
Confere o que a skill precisa na máquina e diz como instalar o que falta.

Uso:  checar_ambiente.py [--json]

Itens:
  python     Python 3.9+                       obrigatório
  playwright pacote Python do Playwright       para PDF e prévias
  chromium   navegador do Playwright           para PDF e prévias
  pypdf      conferência de páginas do PDF     opcional
  pillow     leitura das cores da logo         opcional (o Chromium substitui)
  openpyxl   leitura de planilha XLSX          opcional (CSV não precisa)
  node       Node.js 22+                       para publicar o HTML (Cloudflare)
  wrangler   CLI do Cloudflare                 para publicar o HTML (roda via npx)

Não instala nada: só lista o comando de cada item faltando.
"""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys

for _f in (sys.stdout, sys.stderr):  # Windows em pt-BR usa cp1252 e quebra com ✓/✗
    try:
        _f.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

NODE_MINIMO = 22  # o wrangler atual exige Node 22+
NODE_SITE = f"Baixe o instalador da versão LTS ({NODE_MINIMO} ou mais nova) em https://nodejs.org"


def rodar(cmd, timeout=40):
    exe = shutil.which(cmd[0]) or cmd[0]  # no Windows, npx/node são .cmd e precisam do caminho completo
    try:
        r = subprocess.run([exe] + cmd[1:], capture_output=True, text=True, timeout=timeout)
        return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()
    except Exception as e:
        return 1, str(e)


def item(nome, ok, detalhe, instalar, necessario_para):
    return {"item": nome, "ok": ok, "detalhe": detalhe, "instalar": None if ok else instalar,
            "necessario_para": necessario_para}


def main() -> int:
    mac = platform.system() == "Darwin"
    brew = mac and shutil.which("brew")
    py = "python3" if platform.system() != "Windows" else "python"
    pip = "pip3" if platform.system() != "Windows" else "pip"
    itens = []
    v = sys.version_info
    itens.append(item("python", v >= (3, 9), f"{v.major}.{v.minor}.{v.micro}",
                      "brew install python" if brew else "Instale o Python 3 em https://www.python.org/downloads/",
                      "tudo"))

    try:
        import playwright  # noqa: F401
        pw = True
    except ImportError:
        pw = False
    itens.append(item("playwright", pw, "instalado" if pw else "ausente", f"{pip} install playwright", "PDF e prévias"))

    if pw:
        cod, saida = rodar([sys.executable, "-c",
                            "from playwright.sync_api import sync_playwright\n"
                            "p=sync_playwright().start();b=p.chromium.launch();print(b.version);b.close();p.stop()"])
        if cod == 0:
            detalhe = saida.splitlines()[-1][:80] if saida else "instalado"
        elif "Executable doesn't exist" in saida or "playwright install" in saida:
            detalhe = "navegador não instalado"
        else:
            detalhe = "não consegui abrir o navegador"
        itens.append(item("chromium", cod == 0, detalhe, f"{py} -m playwright install chromium", "PDF e prévias"))
    else:
        itens.append(item("chromium", False, "depende do playwright", f"{py} -m playwright install chromium",
                          "PDF e prévias"))

    for mod, nome, para in (("pypdf", "pypdf", "conferir páginas do PDF (opcional)"),
                            ("PIL", "pillow", "ler cores da logo (opcional)"),
                            ("openpyxl", "openpyxl", "ler planilha XLSX (opcional; CSV não precisa)")):
        try:
            __import__(mod)
            itens.append(item(nome, True, "instalado", None, para))
        except ImportError:
            itens.append(item(nome, False, "ausente", f"{pip} install {nome}", para))

    instalar_node = "brew install node" if brew else NODE_SITE
    node = shutil.which("node")
    node_ok = False
    if node:
        _, nv = rodar(["node", "-v"])
        try:
            maior = int(nv.lstrip("v").split(".")[0])
        except ValueError:
            maior = 0
        node_ok = maior >= NODE_MINIMO
        itens.append(item("node", node_ok, nv if node_ok else f"{nv} (precisa da {NODE_MINIMO} ou mais nova)",
                          "brew upgrade node" if brew else NODE_SITE, "publicar o HTML"))
    else:
        itens.append(item("node", False, "ausente", instalar_node, "publicar o HTML"))

    if not node_ok:
        itens.append(item("wrangler", False, "precisa do Node.js " + str(NODE_MINIMO) + "+",
                          "Instale o Node.js primeiro; o wrangler baixa sozinho depois", "publicar o HTML"))
    elif shutil.which("wrangler"):
        _, wv = rodar(["wrangler", "--version"])
        itens.append(item("wrangler", True, wv.splitlines()[-1] if wv else "instalado", None, "publicar o HTML"))
    elif shutil.which("npx"):
        cod, wv = rodar(["npx", "--yes", "wrangler@latest", "--version"], timeout=120)
        if cod == 0:
            detalhe = (wv.splitlines()[-1] if wv else "")[:80]
        elif "requires at least Node" in wv:
            detalhe = "o Node.js instalado é antigo para o wrangler"
        else:
            detalhe = "o npx não conseguiu baixar (sem internet?)"
        itens.append(item("wrangler", cod == 0, detalhe, "npm install -g wrangler", "publicar o HTML"))
    else:
        itens.append(item("wrangler", False, "npx não encontrado", "Reinstale o Node.js (o npx vem junto)",
                          "publicar o HTML"))

    faltando = [i for i in itens if not i["ok"]]
    if "--json" in sys.argv:
        print(json.dumps({"ok": not faltando, "itens": itens}, ensure_ascii=False, indent=2))
    else:
        for i in itens:
            print(f"{'✓' if i['ok'] else '✗'} {i['item']:<10} {i['detalhe']}"
                  + ("" if i["ok"] else f"\n    para: {i['necessario_para']}\n    instalar: {i['instalar']}"))
    obrig = any(i["item"] == "python" and not i["ok"] for i in itens)
    return 1 if obrig else 0


if __name__ == "__main__":
    raise SystemExit(main())
