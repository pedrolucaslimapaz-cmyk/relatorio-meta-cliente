#!/usr/bin/env python3
"""
Testes automáticos dos scripts da skill.
Uso: python3 tests/testar.py        (sai 0 se tudo passou; precisa do Playwright e do Chromium)
Cada teste roda com RMC_HOME numa pasta temporária: não toca na configuração real.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "skills" / "relatorio-meta-cliente"
SC = SKILL / "scripts"
EX = json.loads((SKILL / "assets" / "exemplo-relatorio.json").read_text())
LOGO = ('<svg xmlns="http://www.w3.org/2000/svg" width="400" height="120"><rect x="0" y="10" width="100" '
        'height="100" rx="20" fill="{c}"/><text x="120" y="80" font-size="60" font-family="Arial" '
        'font-weight="700" fill="#17324D">{t}</text></svg>')
resultados = []


def run(args, home, env_extra=None):
    env = dict(os.environ, RMC_HOME=str(home), **(env_extra or {}))
    r = subprocess.run([sys.executable] + [str(a) for a in args], capture_output=True, text=True, env=env)
    return r.returncode, r.stdout, r.stderr


def check(nome, cond, detalhe=""):
    resultados.append((nome, bool(cond), detalhe))


def configurar(home, tmp, marcas=(("Acme Tráfego", "#E4572E"),)):
    run([SC / "config.py", "init", "--fonte", "meta_mcp"], home)
    slugs = []
    for nome, cor in marcas:
        logo = tmp / f"logo-{len(slugs)}.svg"
        logo.write_text(LOGO.format(c=cor, t=nome.split()[0].upper()))
        _, out, _ = run([SC / "config.py", "identidade-nova", "--nome", nome, "--logo", logo], home)
        s = json.loads(out)["slug"]
        run([SC / "paleta_logo.py", "--identidade", s, "--aplicar", "1"], home)
        run([SC / "config.py", "identidade-set", s, "aprovada", "true"], home)
        slugs.append(s)
    return slugs


def main():
    tmp = Path(tempfile.mkdtemp(prefix="rmc-teste-"))
    try:
        # 1. primeira execução → Modo A
        h = tmp / "h1"
        cod, out, _ = run([SC / "config.py", "status"], h)
        st = json.loads(out)
        check("1. sem configuração → modo A", st["modo"] == "A", st["modo"])

        # 2. tudo configurado → modo C, foco vendas, os dois formatos
        h = tmp / "h2"
        configurar(h, tmp)
        st = json.loads(run([SC / "config.py", "status"], h)[1])
        check("2a. configurado → modo C", st["modo"] == "C", st["modo"])
        rel = dict(EX, exemplo=False)
        (tmp / "r2.json").write_text(json.dumps(rel))
        cod, out, err = run([SC / "montar_relatorio.py", tmp / "r2.json", "--formatos", "pdf,html",
                             "--saida", tmp / "o2", "--link", "https://loja.pages.dev/2026-06-abc/"], h)
        check("2b. montar sai 0", cod == 0, err[-300:])
        cod, out, err = run([SC / "gerar_pdf.py", tmp / "o2" / "relatorio-pdf.html", tmp / "o2" / "r.pdf"], h)
        check("2c. PDF gerado", cod == 0 and (tmp / "o2" / "r.pdf").stat().st_size > 20000, out + err)
        check("2d. dashboard gerado", (tmp / "o2" / "dashboard" / "index.html").exists())
        msg = (tmp / "o2" / "mensagem.txt").read_text()
        check("2e. mensagem com link real e ROAS", "https://loja.pages.dev/2026-06-abc/" in msg and "ROAS" in msg and "🚀" in msg, msg)
        html = (tmp / "o2" / "dashboard" / "index.html").read_text()
        check("2f. identidade aplicada (logo embutida, sem CDN de script)", "data:image/svg+xml;base64" in html and "<script src" not in html)

        # 3. leads abaixo da média → sem foguete
        r3 = dict(EX, foco="leads", desempenho="abaixo", exemplo=False, anterior=None, serie_diaria=[],
                  totais={"investimento": 900, "leads": 45, "impressoes": 80000, "alcance": 30000, "cliques_link": 900},
                  periodo={"tipo": "campanha", "inicio": "2026-08-04", "fim": "2026-08-31", "campanha": "Captação"})
        (tmp / "r3.json").write_text(json.dumps(r3))
        cod, out, err = run([SC / "montar_relatorio.py", tmp / "r3.json", "--formatos", "pdf", "--saida", tmp / "o3"], h)
        msg = (tmp / "o3" / "mensagem.txt").read_text() if cod == 0 else ""
        check("3. leads abaixo → sem 🚀 e com linha de ajuste",
              cod == 0 and "🚀" not in msg and "o que vamos ajustar na próxima" in msg and "anexo" in msg, msg or err)

        # 4. foco ROAS sem evento de compra → avisa e sugere outro
        r4 = dict(r3, foco="vendas", desempenho="dentro")
        (tmp / "r4.json").write_text(json.dumps(r4))
        cod, out, err = run([SC / "montar_relatorio.py", tmp / "r4.json", "--so-validar"], h)
        j = json.loads(out) if cod == 4 else {}
        check("4. vendas sem compras → código 4 e sugere leads", cod == 4 and j.get("sugestao") == "leads", out + err)
        cod2, _, _ = run([SC / "montar_relatorio.py", tmp / "r4.json", "--saida", tmp / "o4"], h)
        check("4b. não gera arquivo com foco sem dados", cod2 == 4 and not (tmp / "o4" / "mensagem.txt").exists())

        # 5. só CSV → relatório
        csv = tmp / "export.csv"
        csv.write_text("﻿Nome da campanha,Dia,Tipo de resultado,Resultados,Alcance,Impressões,Valor usado (BRL),"
                       "Cliques no link,Compras,Valor de conversão de compras,Início dos relatórios,Término dos relatórios\n"
                       ",,,,,,,,,,,\n"
                       '"Vendas | Inverno",2026-08-01,Compras no site,3,1200,2500,37.5,40,3,"450,00",2026-08-01,2026-08-01\n'
                       '"Vendas | Inverno",2026-08-02,Compras no site,2,1100,2300,30.4,35,2,310.5,2026-08-02,2026-08-02\n'
                       '"Remarketing",2026-08-01,Compras no site,1,300,900,11,12,1,99.9,2026-08-01,2026-08-01\n', encoding="utf-8")
        cod, out, err = run([SC / "csv_para_json.py", csv, "--saida", tmp / "r5.json", "--cliente", "Loja CSV"], h)
        d = json.loads((tmp / "r5.json").read_text()) if cod == 0 else {}
        check("5a. CSV convertido (soma e decimal com vírgula)",
              cod == 0 and d["totais"].get("investimento") == 78.9 and d["totais"].get("valor_compras") == 860.4
              and d["totais"].get("compras") == 6 and len(d["serie_diaria"]) == 2, json.dumps(d.get("totais")))
        check("5b. CSV declara limitações (alcance diário, sem criativos)", len(d.get("limitacoes", [])) >= 2)
        d.update(foco="vendas", periodo=dict(d["periodo"], tipo="personalizado"))
        (tmp / "r5.json").write_text(json.dumps(d))
        cod, out, err = run([SC / "montar_relatorio.py", tmp / "r5.json", "--formatos", "pdf,html", "--saida", tmp / "o5"], h)
        check("5c. relatório gerado a partir do CSV", cod == 0 and "exportação do Gerenciador" in (tmp / "o5" / "relatorio-pdf.html").read_text(), err[-300:])

        # 6. deploy falha → HTML como arquivo, sem link
        fake = tmp / "fakewr.sh"
        fake.write_text('#!/bin/sh\ncase "$1" in whoami) echo "associated with the email a@b.com."; exit 0;; '
                        'pages) [ "$2" = "deploy" ] && { echo "ERROR Authentication error token=abcdefghijklmnopqrstuvwxyz0123456789ABCD"; exit 1; }; exit 0;; esac\n')
        fake.chmod(0o755)
        cod, out, err = run([SC / "deploy_cloudflare.py", "--dashboard", tmp / "o2" / "dashboard" / "index.html",
                             "--projeto", "Loja Exemplo", "--pasta", "2026-06"], h, {"RMC_WRANGLER": str(fake)})
        j = json.loads(out) if out.strip().startswith("{") else {}
        pub = h / "publicar" / "loja-exemplo"
        check("6a. deploy falho → código 6, sem url, com arquivo local",
              cod == 6 and "url" not in j and j.get("arquivo_local"), out + err)
        check("6b. token mascarado na saída", "abcdefghijklmnopqrstuvwxyz0123456789ABCD" not in out + err)
        check("6c. pasta do relatório falho não fica para o próximo deploy",
              not any(p.is_dir() for p in pub.iterdir()) if pub.exists() else True)
        fake_ok = tmp / "fakewr_ok.sh"
        fake_ok.write_text('#!/bin/sh\ncase "$1" in whoami) echo "not authenticated"; exit 1;; esac\nexit 0\n')
        fake_ok.chmod(0o755)
        cod, out, err = run([SC / "deploy_cloudflare.py", "--dashboard", tmp / "o2" / "dashboard" / "index.html",
                             "--projeto", "x", "--pasta", "2026-06"], h, {"RMC_WRANGLER": str(fake_ok)})
        check("6d. sem login → código 5 com próximo passo", cod == 5 and "wrangler login" in err, err)

        # 7. máquina sem Node/Wrangler → checagem orienta
        env = {"PATH": "/usr/bin:/bin"}
        r = subprocess.run([sys.executable, SC / "checar_ambiente.py", "--json"], capture_output=True, text=True,
                           env=dict(os.environ, **env))
        j = json.loads(r.stdout)
        itens = {i["item"]: i for i in j["itens"]}
        check("7. sem Node → aponta node e wrangler com comando de instalação",
              not itens["node"]["ok"] and itens["node"]["instalar"] and not itens["wrangler"]["ok"]
              and itens["wrangler"]["instalar"], json.dumps(itens["node"]))

        # 8. duas identidades → status lista as duas; cada uma sai com a sua marca
        h8 = tmp / "h8"
        s1, s2 = configurar(h8, tmp, (("Acme Tráfego", "#E4572E"), ("Beta Ads", "#1D7A5F")))
        st = json.loads(run([SC / "config.py", "status"], h8)[1])
        check("8a. duas identidades listadas", len(st["identidades"]) == 2)
        run([SC / "montar_relatorio.py", tmp / "r2.json", "--identidade", s2, "--formatos", "html", "--saida", tmp / "o8"], h8)
        html = (tmp / "o8" / "dashboard" / "index.html").read_text()
        check("8b. relatório usa a identidade escolhida", '"nome": "Beta Ads"' in html and '"nome": "Acme Tráfego"' not in html)

        # extras de segurança
        cod, _, err = run([SC / "config.py", "set", "cloudflare_api_token", "abc"], h)
        check("x1. config recusa gravar token", cod == 2)
        r_inj = dict(EX, exemplo=False)
        r_inj["campanhas"] = [{"nome": "</script><script>alert(1)</script>", "investimento": 10, "compras": 1}]
        (tmp / "rx.json").write_text(json.dumps(r_inj))
        run([SC / "montar_relatorio.py", tmp / "rx.json", "--formatos", "html", "--saida", tmp / "ox"], h)
        html = (tmp / "ox" / "dashboard" / "index.html").read_text()
        check("x2. nome de campanha malicioso não fecha o <script> de dados",
              "alert(1)" in html and "<script>alert(1)" not in html and "<\\/script><script>" not in html)

        # regressões do teste com conta real (1.0.1)
        r_mix = dict(EX, exemplo=False)
        r_mix["campanhas"] = [{"nome": "Vendas", "investimento": 100, "compras": 20},
                              {"nome": "Tráfego perfil", "investimento": 30, "resultados": 1200}]
        r_mix["criativos"] = [{"nome": f"Criativo {i}", "investimento": 10, "compras": 2} for i in range(1, 5)]
        (tmp / "rm.json").write_text(json.dumps(r_mix))
        run([SC / "montar_relatorio.py", tmp / "rm.json", "--formatos", "pdf,html", "--saida", tmp / "om"], h)
        html = (tmp / "om" / "relatorio-pdf.html").read_text()
        check("x3. foco vendas não põe resultado de outro tipo na coluna de vendas",
              '"1.200"' not in html and '"resultados": "—"' in html)
        tpl = (SKILL / "assets" / "template-pdf.html").read_text()
        check("x4. PDF limita criativos a 3 (dashboard mantém até 6)",
              "D.criativos.slice(0,3)" in tpl
              and "Criativo 4" in (tmp / "om" / "dashboard" / "index.html").read_text())
        r_sem = dict(EX, exemplo=False, serie_granularidade="semana")
        (tmp / "rs.json").write_text(json.dumps(r_sem))
        run([SC / "montar_relatorio.py", tmp / "rs.json", "--formatos", "pdf,html", "--saida", tmp / "os"], h)
        tpl_pdf = (SKILL / "assets" / "template-pdf.html").read_text()
        check("x5. série semanal chega ao template e troca o título do gráfico",
              '"granularidade": "semana"' in (tmp / "os" / "relatorio-pdf.html").read_text()
              and "Evolução semana a semana" in tpl_pdf)

        # CSV de campanhas no formato atual do Gerenciador (pt-BR), 2 campanhas com resultados diferentes
        (tmp / "camp.csv").write_text(
            '"Início dos relatórios","Encerramento dos relatórios","Nome da campanha",Resultados,"Indicador de resultados",'
            '"Valor usado (BRL)",Impressões,Alcance,"Valor de conversão da compra no site",Compras,"Valor de conversão da compra"\n'
            '2025-01-01,2026-08-05,"Vendas 01",100,actions:offsite_conversion.fb_pixel_purchase,300,40000,9000,5000,100,5200\n'
            '2025-01-01,2026-08-05,"Perfil 01",800,profile_visit_view,150,30000,12000,,,\n', encoding="utf-8")
        cod, out, err = run([SC / "csv_para_json.py", tmp / "camp.csv", "--saida", tmp / "rc.json", "--cliente", "Teste"], h)
        rc = json.loads((tmp / "rc.json").read_text()) if cod == 0 else {}
        tc = rc.get("totais", {})
        check("x6. CSV pt-BR: data final, valor de compra (geral), sem somar alcance nem resultados misturados",
              cod == 0 and rc["periodo"]["fim"] == "2026-08-05" and tc.get("valor_compras") == 5200
              and tc.get("alcance") is None and tc.get("resultados") is None
              and not any("actions:" in l or "profile_visit" in l for l in rc.get("limitacoes", [])), err[-300:])

        # foco leads com nome próprio (campanha de mensagens): nada de "lead" no que vai para o cliente
        r_msg = dict(EX, exemplo=False, foco="leads")
        r_msg["totais"] = {"investimento": 1000, "impressoes": 100000, "alcance": 20000, "cliques_link": 800, "leads": 250,
                           "rotulo_leads": {"plural": "conversas no WhatsApp", "singular": "conversa"}}
        r_msg["anterior"] = {"rotulo": "agosto", "investimento": 500, "leads": 100}
        r_msg["serie_diaria"] = [{"data": "2026-09-0%d" % d, "investimento": 30, "leads": 9} for d in range(1, 4)]
        r_msg["campanhas"], r_msg["criativos"] = [], []
        (tmp / "rmsg.json").write_text(json.dumps(r_msg))
        cod, out, err = run([SC / "montar_relatorio.py", tmp / "rmsg.json", "--formatos", "pdf,html", "--saida", tmp / "omsg"], h)
        htm = (tmp / "omsg" / "relatorio-pdf.html").read_text() if cod == 0 else ""
        msg = (tmp / "omsg" / "mensagem.txt").read_text() if cod == 0 else ""
        dados = htm[htm.find('id="dados"'):] if 'id="dados"' in htm else htm
        check("x7. foco leads com rotulo_leads troca todos os textos (sem 'lead')",
              cod == 0 and "250 conversas no WhatsApp" in msg and "Custo por conversa" in htm
              and "por lead" not in dados and "Leads e CPL" not in dados and "Custo por lead" not in dados, err[-300:])

        # 1.2.0: publicação só do index.html, recusa de outro arquivo, despublicar
        h9 = tmp / "h9 com espaco"
        (tmp / "o2" / "dashboard" / "relatorio.json").write_text("{}")  # não pode subir junto
        lista = tmp / "lista.txt"
        fake_ls = tmp / "fake ls.sh"
        fake_ls.write_text('#!/bin/sh\ncase "$1" in whoami) echo "associated with the email a@b.com."; exit 0;; '
                           f'pages) [ "$2" = "deploy" ] && {{ ls -R "$3" > "{lista}"; exit 1; }}; exit 0;; esac\n')
        fake_ls.chmod(0o755)
        cod, out, err = run([SC / "deploy_cloudflare.py", "--dashboard", tmp / "o2" / "dashboard" / "index.html",
                             "--projeto", "Loja", "--pasta", "2026-06"], h9, {"RMC_WRANGLER": str(fake_ls)})
        enviado = lista.read_text() if lista.exists() else ""
        check("x8. deploy envia só o index.html, com código de 16 caracteres (e aceita caminho com espaço)",
              cod == 6 and "index.html" in enviado and "relatorio.json" not in enviado
              and re.search(r"2026-06-[0-9a-f]{16}", enviado), out + err + enviado)
        cod, out, err = run([SC / "deploy_cloudflare.py", "--dashboard", tmp / "o2" / "relatorio-pdf.html",
                             "--projeto", "Loja", "--pasta", "2026-06"], h9, {"RMC_WRANGLER": str(fake_ls)})
        check("x9. deploy recusa arquivo que não é dashboard/index.html", cod == 2, err)
        alvo = h9 / "publicar" / "loja" / "2026-05-0123456789abcdef"
        alvo.mkdir(parents=True)
        (alvo / "index.html").write_text("x")
        fake_dep = tmp / "fake_dep.sh"
        fake_dep.write_text('#!/bin/sh\ncase "$1" in whoami) echo "associated with the email a@b.com."; exit 0;; esac\nexit 0\n')
        fake_dep.chmod(0o755)
        cod, out, err = run([SC / "deploy_cloudflare.py", "--despublicar", "--projeto", "Loja",
                             "--pasta", "2026-05-0123456789abcdef"], h9, {"RMC_WRANGLER": str(fake_dep)})
        check("x10. despublicar apaga a pasta e publica de novo", cod == 0 and not alvo.exists(), out + err)

        # 1.2.0: imagem de criativo só de dentro da pasta do JSON e só imagem
        pasta_img = tmp / "img"
        pasta_img.mkdir()
        (pasta_img / "c1.png").write_bytes(bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da63f8ffff3f0005fe02fea7d6a5ad0000000049454e44ae426082"))
        r_img = dict(EX, exemplo=False)
        r_img["criativos"] = [{"nome": "Dentro", "imagem": "c1.png", "investimento": 10, "compras": 1},
                              {"nome": "Fora", "imagem": "/etc/hosts", "investimento": 5, "compras": 1}]
        (pasta_img / "relatorio.json").write_text(json.dumps(r_img))
        cod, out, err = run([SC / "montar_relatorio.py", pasta_img / "relatorio.json", "--formatos", "html",
                             "--saida", tmp / "oimg"], h)
        htm = (tmp / "oimg" / "dashboard" / "index.html").read_text() if cod == 0 else ""
        j = json.loads(out) if cod == 0 else {}
        check("x11. imagem de criativo: PNG da pasta entra, arquivo de fora não, e avisa",
              cod == 0 and "data:image/png;base64" in htm and "octet-stream" not in htm
              and any("hosts" in a for a in j.get("avisos", [])), out + err)

        # 1.2.0: CSV salvo no Excel pt-BR (ponto de milhar, vírgula decimal, DD/MM/AAAA) com código do Meta
        (tmp / "br.csv").write_text(
            "Nome da campanha;Início dos relatórios;Encerramento dos relatórios;Indicador de resultados;Resultados;"
            "Valor usado (BRL);Impressões;Alcance;Cliques no link\n"
            '"Perfil";01/09/2026;30/09/2026;profile_visit_view;1.020;1.234,56;34.567;12.500;1.020\n',
            encoding="latin-1")
        cod, out, err = run([SC / "csv_para_json.py", tmp / "br.csv", "--saida", tmp / "rbr.json"], h)
        rb = json.loads((tmp / "rbr.json").read_text()) if cod == 0 else {}
        tb = rb.get("totais", {})
        check("x12. CSV pt-BR: milhar, datas DD/MM/AAAA e código do Meta traduzido",
              cod == 0 and tb.get("impressoes") == 34567 and tb.get("alcance") == 12500 and tb.get("cliques_link") == 1020
              and tb.get("investimento") == 1234.56 and rb["periodo"] == {"inicio": "2026-09-01", "fim": "2026-09-30"}
              and tb.get("rotulo_resultado") == "visitas ao perfil", json.dumps(rb.get("totais")) + err[-300:])
        r_dt = dict(EX, exemplo=False, periodo=dict(EX["periodo"], inicio="01/08/2026"))
        (tmp / "rdt.json").write_text(json.dumps(r_dt))
        cod, out, err = run([SC / "montar_relatorio.py", tmp / "rdt.json", "--so-validar"], h)
        check("x13. data fora do formato é recusada já na validação, em português", cod == 2 and "AAAA-MM-DD" in err, err)

        # 1.2.0: frontmatter com o nome documentado e todas as ferramentas de escrita do Meta
        fm = (SKILL / "SKILL.md").read_text().split("---")[1]
        check("x14. SKILL.md usa disallowed-tools com as 42 ferramentas de escrita",
              "disallowed-tools:" in fm and "disallowedTools" not in fm and fm.count("mcp__meta-ads__ads_") == 42)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    ok = sum(1 for _, p, _ in resultados if p)
    for nome, p, det in resultados:
        print(("✓ " if p else "✗ ") + nome + ("" if p else f"\n    {det[:400]}"))
    print(f"\n{ok}/{len(resultados)} passaram")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    raise SystemExit(main())
