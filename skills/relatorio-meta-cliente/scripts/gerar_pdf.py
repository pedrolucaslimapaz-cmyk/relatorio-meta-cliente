#!/usr/bin/env python3
"""
Renderiza o HTML montado em PDF A4 (Chromium headless via Playwright), ou tira
uma captura PNG para prévia.

Uso:
  gerar_pdf.py <relatorio-pdf.html> <saida.pdf>
  gerar_pdf.py <pagina.html> <saida.png> --png [--largura 390] [--altura 844] [--pagina-inteira]

Com --png no HTML do PDF (relatorio-pdf.html), a captura sai na largura A4 e com a mídia
de impressão, para bater com o PDF (sem isso o layout de tela quebra e parece erro).

Espera o template sinalizar window.__pronto antes de imprimir (os gráficos são
desenhados por JavaScript). Rodapé com "página X de Y" em todas as páginas.

Saída 0 = ok · 2 = entrada inválida · 3 = Playwright/Chromium indisponível
(não finja que gerou: entregue o HTML e diga como instalar).
"""

from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

RODAPE = ('<div style="width:100%;font-size:7.5pt;color:#8A8F99;padding:0 14mm;display:flex;'
          'justify-content:space-between;font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif">'
          '<span>{texto}</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("entrada")
    ap.add_argument("saida")
    ap.add_argument("--png", action="store_true")
    ap.add_argument("--largura", type=int, default=390)
    ap.add_argument("--altura", type=int, default=844)
    ap.add_argument("--pagina-inteira", action="store_true")
    a = ap.parse_args()

    entrada = Path(a.entrada).expanduser().resolve()
    saida = Path(a.saida).expanduser().resolve()
    if not entrada.exists():
        print(f"HTML não encontrado: {entrada}", file=sys.stderr)
        return 2
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("O Playwright não está instalado, então não dá para gerar o PDF.\n"
              "Próximo passo: rode  pip3 install playwright  e depois  python3 -m playwright install chromium",
              file=sys.stderr)
        return 3

    saida.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as p:
            navegador = p.chromium.launch()
            if a.png:
                pg = navegador.new_page(viewport={"width": a.largura, "height": a.altura}, device_scale_factor=2)
            else:
                pg = navegador.new_page()
            pg.emulate_media(reduced_motion="reduce")
            pg.goto(entrada.as_uri())
            try:
                pg.wait_for_function("window.__pronto === true", timeout=15000)
            except Exception:
                print("Aviso: o template não sinalizou que terminou de desenhar; seguindo mesmo assim.", file=sys.stderr)
            pg.wait_for_load_state("networkidle")
            if a.png:
                if pg.evaluate("!!document.querySelector('meta[name=rodape]')"):
                    # HTML do PDF: captura como impressão A4 (794 px = 210 mm a 96 dpi)
                    pg.emulate_media(media="print", reduced_motion="reduce")
                    pg.set_viewport_size({"width": 794, "height": a.altura})
                    pg.wait_for_timeout(300)
                pg.screenshot(path=str(saida), full_page=a.pagina_inteira)
            else:
                rodape = pg.evaluate("(document.querySelector('meta[name=rodape]')||{}).content || ''")
                pg.pdf(path=str(saida), format="A4", print_background=True, prefer_css_page_size=True,
                       display_header_footer=True, header_template="<div></div>",
                       footer_template=RODAPE.format(texto=html.escape(rodape)))
            navegador.close()
    except Exception as e:
        msg = str(e).splitlines()[0]
        print(f"Não consegui abrir o Chromium ({msg}).\n"
              "Próximo passo: rode  python3 -m playwright install chromium  e tente de novo.", file=sys.stderr)
        return 3

    if a.png:
        print(f"OK: {saida}")
        return 0
    if not saida.exists() or saida.stat().st_size < 3000:
        print("O PDF saiu vazio ou quebrado.", file=sys.stderr)
        return 3
    try:
        from pypdf import PdfReader
        r = PdfReader(str(saida))
        vazias = [i + 1 for i, pg in enumerate(r.pages) if len((pg.extract_text() or "").strip()) < 25]
        print(f"OK: {saida} ({len(r.pages)} página(s))" + (f" · ATENÇÃO: página(s) quase vazia(s): {vazias}" if vazias else ""))
    except ImportError:
        print(f"OK: {saida} ({saida.stat().st_size} bytes; instale pypdf para conferir páginas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
