#!/usr/bin/env python3
"""
Monta os arquivos do relatório a partir de um relatorio.json (formato em
references/estrutura-dados.md) e de uma identidade visual.

Uso:
  montar_relatorio.py <relatorio.json> [--identidade slug] [--saida pasta]
                      [--formatos pdf,html] [--link URL] [--so-validar]

Gera na pasta de saída:
  relatorio-pdf.html     página A4 (vira PDF com gerar_pdf.py)
  dashboard/index.html   página mobile, autossuficiente, pronta para publicar
  mensagem.txt           mensagem para WhatsApp
  resumo.json            números conferíveis (o que foi calculado e o que veio pronto)

Códigos de saída:
  0 ok · 2 erro de entrada · 4 o foco escolhido não tem dados (a mensagem sugere outro foco)
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _comum import (ASSETS, MESES, agora_iso, data_br, formatar, gravar_json, ler_json,  # noqa: E402
                    pasta_config, periodo_extenso, slug)

# chave: (rótulo, tipo de formato, direção boa: +1 subir é bom, -1 cair é bom, 0 neutro)
METRICAS = {
    "investimento": ("Investimento", "moeda", 0),
    "resultados": ("Resultados", "int", 1),
    "custo_por_resultado": ("Custo por resultado", "moeda", -1),
    "compras": ("Vendas", "int", 1),
    "valor_compras": ("Faturamento", "moeda", 1),
    "roas": ("ROAS", "roas", 1),
    "custo_por_compra": ("Custo por venda", "moeda", -1),
    "leads": ("Leads", "int", 1),
    "cpl": ("Custo por lead", "moeda", -1),
    "taxa_conversao_pagina": ("Conversão da página", "pct", 1),
    "cac_midia": ("CAC de mídia", "moeda", -1),
    "cac_real": ("CAC real", "moeda", -1),
    "vendas_reais": ("Vendas reais (informadas)", "int", 1),
    "alcance": ("Alcance", "int", 1),
    "impressoes": ("Impressões", "int", 1),
    "frequencia": ("Frequência", "dec", 0),
    "cpm": ("CPM", "moeda", -1),
    "thruplays": ("ThruPlays", "int", 1),
    "custo_por_thruplay": ("Custo por ThruPlay", "moeda", -1),
    "cliques_link": ("Cliques no link", "int", 1),
    "ctr": ("CTR", "pct", 1),
    "cpc": ("CPC", "moeda", -1),
    "engajamentos": ("Engajamentos", "int", 1),
}
NOTAS = {
    "alcance": "contas da Meta",
    "roas": "retorno sobre o investimento em anúncios",
    "cac_midia": "vendas atribuídas pelo Meta",
    "cac_real": "com as vendas informadas pelo cliente",
    "valor_compras": "atribuído pelo Meta",
    "frequencia": "vezes, em média, por conta",
}

FOCOS = {
    "vendas": {
        "rotulo": "Vendas e ROAS",
        "requer": ["compras"],
        "principais": ["investimento", "compras", "custo_por_compra"],
        "secundarias": ["roas", "valor_compras", "cliques_link", "ctr", "alcance", "cpm", "frequencia"],
    },
    "leads": {
        "rotulo": "Leads e CPL",
        "requer": ["leads"],
        "principais": ["investimento", "leads", "cpl"],
        "secundarias": ["taxa_conversao_pagina", "cliques_link", "ctr", "cpc", "alcance", "frequencia"],
    },
    "cac": {
        "rotulo": "CAC",
        "requer": ["compras"],
        "principais": ["investimento", "compras", "cac_midia"],
        "secundarias": ["cac_real", "vendas_reais", "roas", "valor_compras", "ctr", "alcance"],
    },
    "alcance": {
        "rotulo": "Alcance e engajamento",
        "requer": ["alcance"],
        "principais": ["investimento", "alcance", "cpm"],
        "secundarias": ["frequencia", "impressoes", "thruplays", "custo_por_thruplay", "engajamentos", "ctr", "cliques_link"],
    },
}
ORDEM_SUGESTAO = ["vendas", "leads", "alcance"]


# ------------------------------------------------------------------ cálculos

def _div(a, b):
    return a / b if a is not None and b not in (None, 0) else None


def derivar(t: dict) -> tuple[dict, list[str]]:
    """Completa métricas calculáveis. Devolve (totais, lista do que foi calculado)."""
    t = {k: v for k, v in (t or {}).items() if v is not None}
    calc = []

    def pôr(chave, valor):
        if chave not in t and valor is not None:
            t[chave] = valor
            calc.append(chave)

    inv = t.get("investimento")
    pôr("frequencia", _div(t.get("impressoes"), t.get("alcance")))
    pôr("ctr", (_div(t.get("cliques_link"), t.get("impressoes")) or 0) * 100 if t.get("cliques_link") is not None and t.get("impressoes") else None)
    pôr("cpc", _div(inv, t.get("cliques_link")))
    pôr("cpm", (_div(inv, t.get("impressoes")) or 0) * 1000 if t.get("impressoes") else None)
    pôr("custo_por_resultado", _div(inv, t.get("resultados")))
    pôr("custo_por_compra", _div(inv, t.get("compras")))
    pôr("cpl", _div(inv, t.get("leads")))
    pôr("custo_por_thruplay", _div(inv, t.get("thruplays")))
    pôr("cac_midia", _div(inv, t.get("compras")))
    pôr("cac_real", _div(inv, t.get("vendas_reais")))
    # ROAS só com valor de compra confiável (> 0). Sem isso, não existe ROAS.
    if t.get("valor_compras"):
        pôr("roas", _div(t["valor_compras"], inv))
    elif t.get("roas") and inv:
        pôr("valor_compras", t["roas"] * inv)  # purchase_roas já é valor de compra ÷ investimento
    else:
        t.pop("roas", None)  # ROAS zerado sem valor de compra não é ROAS, é ausência de dado
    return t, calc


def checar_foco(foco: str, t: dict) -> tuple[bool, str | None]:
    faltando = [k for k in FOCOS[foco]["requer"] if t.get(k) is None]
    if not faltando:
        return True, None
    for f in ORDEM_SUGESTAO:
        if f != foco and all(t.get(k) is not None for k in FOCOS[f]["requer"]):
            return False, f
    return False, None


def delta(chave, atual, anterior):
    if atual is None or anterior in (None, 0):
        return None
    var = (atual - anterior) / abs(anterior) * 100
    direcao = METRICAS[chave][2]
    if abs(var) < 0.5:
        return {"texto": "estável", "bom": None, "var": 0}
    bom = None if direcao == 0 else (var > 0) == (direcao > 0)
    seta = "▲" if var > 0 else "▼"
    return {"texto": f"{seta} {formatar(abs(var), 'pct').replace('%', '')}%", "bom": bom, "var": round(var, 1)}


def rot_leads(t: dict) -> tuple[str, str]:
    """Nome do resultado no foco leads: (plural, singular). Ex.: conversas no WhatsApp / conversa."""
    r = t.get("rotulo_leads") or {}
    return (r.get("plural") or "leads", r.get("singular") or "lead")


def cap(txt: str) -> str:
    return txt[:1].upper() + txt[1:]


def metrica(chave, t, ant, moeda, rotulo_resultado=None):
    if t.get(chave) is None:
        return None
    rot, tipo, _ = METRICAS[chave]
    if chave == "resultados" and rotulo_resultado:
        rot = rotulo_resultado[:1].upper() + rotulo_resultado[1:]
    if chave in ("leads", "cpl") and t.get("rotulo_leads"):
        rot = cap(rot_leads(t)[0]) if chave == "leads" else f"Custo por {rot_leads(t)[1]}"
    d = delta(chave, t.get(chave), (ant or {}).get(chave)) if ant else None
    return {"chave": chave, "rotulo": rot, "valor": t[chave], "tipo": tipo, "moeda": moeda,
            "fmt": formatar(t[chave], tipo, moeda), "nota": NOTAS.get(chave), "delta": d}


# ------------------------------------------------------------------ mensagem

def mensagem(r: dict, t: dict, foco: str, link: str | None, formatos: list[str]) -> str:
    moeda = r.get("moeda", "BRL")
    nome = r.get("contato_cliente") or r.get("cliente") or ""
    per = r["periodo"]
    if per.get("campanha"):
        abertura = f"Segue o relatório da nossa última campanha ({per['campanha']})."
    else:
        rot_per = per.get("rotulo") or periodo_extenso(per["inicio"], per["fim"])
        if rot_per.split(" ")[0].lower() in MESES:
            abertura = f"Segue o relatório das campanhas de {rot_per[0].lower() + rot_per[1:]}."
        else:
            abertura = f"Segue o relatório das campanhas do período de {rot_per}."

    if foco in ("vendas", "cac"):
        qtd, rot, cpr = t.get("compras"), "vendas", t.get("custo_por_compra")
    elif foco == "leads":
        qtd, rot, cpr = t.get("leads"), rot_leads(t)[0], t.get("cpl")
    else:
        qtd = t.get("resultados")
        rot = (t.get("rotulo_resultado") or "resultados").lower()
        cpr = t.get("custo_por_resultado")
    if qtd is not None and round(qtd) == 1 and rot.endswith("s"):
        rot = rot[:-1]

    linhas = [f"Olá, {nome}!", "", abertura, "",
              f"💰 Investimento: {formatar(t.get('investimento'), 'moeda', moeda)}"]
    if foco == "alcance" and qtd is None:
        linhas.append(f"🎯 Resultado: {formatar(t.get('alcance'), 'int')} contas da Meta alcançadas")
        cpr = t.get("cpm")
        linhas.append(f"📉 Custo por mil impressões (CPM): {formatar(cpr, 'moeda', moeda)}")
    else:
        linhas.append(f"🎯 Resultado: {formatar(qtd, 'int')} {rot}")
        linhas.append(f"📉 Custo por resultado: {formatar(cpr, 'moeda', moeda)}")

    destaque = None
    if foco == "vendas" and t.get("roas") is not None:
        destaque = f"ROAS de {formatar(t['roas'], 'roas')}: {formatar(t['valor_compras'], 'moeda', moeda)} em vendas atribuídas"
    elif foco == "vendas" and t.get("valor_compras"):
        destaque = f"Faturamento atribuído de {formatar(t['valor_compras'], 'moeda', moeda)}"
    elif foco == "leads" and t.get("taxa_conversao_pagina") is not None:
        destaque = f"Conversão da página: {formatar(t['taxa_conversao_pagina'], 'pct')}"
    elif foco == "cac":
        destaque = f"CAC de mídia: {formatar(t.get('cac_midia'), 'moeda', moeda)} (vendas atribuídas pelo Meta)"
        if t.get("cac_real") is not None:
            destaque += f" · CAC real: {formatar(t['cac_real'], 'moeda', moeda)}"
    elif foco == "alcance" and t.get("thruplays"):
        destaque = f"{formatar(t['thruplays'], 'int')} ThruPlays (vídeos assistidos até o fim ou por 15s)"
    elif foco == "alcance" and t.get("engajamentos"):
        destaque = f"{formatar(t['engajamentos'], 'int')} engajamentos com as publicações"

    abaixo = r.get("desempenho") == "abaixo"
    if destaque:
        linhas.append(destaque if abaixo else f"{destaque} 🚀")
    linhas.append("")
    if abaixo:
        linhas += ["No relatório mostramos o que funcionou, o que não funcionou e o que vamos ajustar na próxima.", ""]
    if "html" in formatos and link:
        linhas.append(f"Acesse o relatório completo: {link}")
        if "pdf" in formatos:
            linhas.append("O PDF também vai em anexo.")
    elif "html" in formatos and "pdf" in formatos:
        linhas.append("O relatório completo vai em anexo (PDF e página para abrir no celular).")
    else:
        linhas.append("Relatório completo em anexo.")
    return "\n".join(linhas) + "\n"


# ------------------------------------------------------------------ view model

IMAGENS = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif"}
AVISOS: list[str] = []


def data_uri(p: Path | None, svg: bool = False) -> str | None:
    """Embute uma imagem no HTML. Só aceita imagem: a página pode virar um link público."""
    if not p or not p.is_file():
        return None
    mime = {**IMAGENS, **({".svg": "image/svg+xml"} if svg else {})}.get(p.suffix.lower())
    if not mime:
        return None
    return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"


def imagem_criativo(valor, base: Path) -> str | None:
    if not valor:
        return None
    v = str(valor)
    if v.startswith("data:"):
        if v.startswith(tuple(f"data:{m};base64," for m in IMAGENS.values())):
            return v
        AVISOS.append("Imagem de criativo ignorada: o data URI não é PNG, JPG, WebP ou GIF.")
        return None
    p = Path(v).expanduser()
    if not p.is_absolute():
        p = base / p
    # só arquivos dentro da pasta do relatorio.json (URL remota também não entra: expira e quebra a página)
    try:
        dentro = base.resolve() in p.resolve().parents
    except OSError:
        dentro = False
    uri = data_uri(p) if dentro else None
    if not uri:
        AVISOS.append(f"Imagem de criativo ignorada: {p.name} (precisa ser PNG, JPG, WebP ou GIF dentro da pasta "
                      "do relatorio.json).")
    return uri


def montar_vm(r, t, ant, foco, ident, pasta_ident, calc, base_json: Path, link) -> dict:
    moeda = r.get("moeda", "BRL")
    cfg = FOCOS[foco]
    rot_res = t.get("rotulo_resultado")
    principais = [m for m in (metrica(k, t, ant, moeda, rot_res) for k in cfg["principais"]) if m]
    secundarias = [m for m in (metrica(k, t, ant, moeda, rot_res) for k in cfg["secundarias"]) if m][:6]

    # número herói
    if foco == "vendas" and t.get("valor_compras"):
        heroi = metrica("valor_compras", t, ant, moeda)
        heroi["apoio"] = (f"ROAS de {formatar(t['roas'], 'roas')}: cada {formatar(1, 'moeda', moeda)} investido "
                          f"voltou {formatar(t['roas'], 'moeda', moeda)} em vendas atribuídas") if t.get("roas") else None
    elif foco == "vendas":
        heroi = metrica("compras", t, ant, moeda)
        heroi["apoio"] = f"a {formatar(t.get('custo_por_compra'), 'moeda', moeda)} por venda"
    elif foco == "leads":
        heroi = metrica("leads", t, ant, moeda)
        heroi["apoio"] = f"a {formatar(t.get('cpl'), 'moeda', moeda)} por {rot_leads(t)[1]}"
    elif foco == "cac":
        heroi = metrica("cac_real" if t.get("cac_real") is not None else "cac_midia", t, ant, moeda)
        heroi["apoio"] = ("custo de mídia para cada venda atribuída pelo Meta" if heroi["chave"] == "cac_midia"
                          else "custo de mídia para cada venda real informada")
    else:
        heroi = metrica("alcance", t, ant, moeda)
        heroi["apoio"] = "contas da Meta alcançadas"
        if t.get("frequencia") is not None:
            heroi["apoio"] += f", com frequência média de {formatar(t['frequencia'], 'dec')}"

    cac_comp = None
    if foco == "cac" and t.get("cac_real") is not None:
        cac_comp = {"midia": formatar(t["cac_midia"], "moeda", moeda), "real": formatar(t["cac_real"], "moeda", moeda),
                    "vendas_meta": formatar(t.get("compras"), "int"), "vendas_reais": formatar(t.get("vendas_reais"), "int")}

    # série
    serie = None
    sd = r.get("serie_diaria") or []
    if len(sd) >= 2:
        chave_res = {"vendas": "compras", "cac": "compras", "leads": "leads"}.get(foco, "resultados")
        res = [d.get(chave_res, d.get("resultados")) for d in sd]
        serie = {"datas": [d["data"] for d in sd], "investimento": [d.get("investimento") for d in sd],
                 "resultados": res if any(x is not None for x in res) else None,
                 "rotulo_resultado": {"compras": "Vendas", "leads": cap(rot_leads(t)[0])}.get(chave_res, (rot_res or "Resultados").capitalize()),
                 "moeda": moeda,
                 # períodos longos: a série pode vir por semana ou por mês (data = 1º dia do bloco)
                 "granularidade": r.get("serie_granularidade") if r.get("serie_granularidade") in ("dia", "semana", "mes") else "dia"}

    campanhas = []
    total_inv = sum((c.get("investimento") or 0) for c in r.get("campanhas") or []) or None
    for c in (r.get("campanhas") or [])[:8]:
        cc, _ = derivar(c)
        chave_res = {"vendas": "compras", "cac": "compras", "leads": "leads"}.get(foco, "resultados")
        # Foco de vendas/leads: só conta o resultado do foco. Cair em "resultados" genéricos
        # misturaria visitas ou alcance na coluna de vendas (ex.: "1.200 a R$ 0,25").
        qtd = cc.get(chave_res) if chave_res != "resultados" else cc.get("resultados")
        cpr = _div(cc.get("investimento"), qtd)
        campanhas.append({
            "nome": c.get("nome"),
            "investimento": formatar(cc.get("investimento"), "moeda", moeda),
            "resultados": formatar(qtd, "int") if qtd is not None else "—",
            "custo": formatar(cpr, "moeda", moeda) if cpr else "—",
            "roas": formatar(cc["roas"], "roas") if foco in ("vendas", "cac") and cc.get("roas") else None,
            "participacao": round((cc.get("investimento") or 0) / total_inv, 4) if total_inv else 0,
        })

    criativos = []
    for c in (r.get("criativos") or [])[:6]:
        cc, _ = derivar(c)
        chave_res = {"vendas": "compras", "cac": "compras", "leads": "leads"}.get(foco, "resultados")
        qtd = cc.get(chave_res) if chave_res != "resultados" else cc.get("resultados")
        mets = []
        if cc.get("investimento") is not None:
            mets.append(["Investimento", formatar(cc["investimento"], "moeda", moeda)])
        if qtd is not None:
            mets.append([{"compras": "Vendas", "leads": cap(rot_leads(t)[0])}.get(chave_res, "Resultados"), formatar(qtd, "int")])
            cpr = _div(cc.get("investimento"), qtd)
            if cpr:
                mets.append(["Custo por resultado", formatar(cpr, "moeda", moeda)])
        if cc.get("ctr") is not None:
            mets.append(["CTR", formatar(cc["ctr"], "pct")])
        criativos.append({"nome": c.get("nome"), "selo": c.get("selo"), "descricao": c.get("descricao"),
                          "texto": c.get("texto"), "imagem": imagem_criativo(c.get("imagem"), base_json.parent),
                          "metricas": mets})

    publico = []
    titulos = {"idade": "Idade", "genero": "Gênero", "posicionamento": "Posicionamento", "regiao": "Região",
               "dispositivo": "Dispositivo"}
    pub = r.get("publico") or {}
    for chave, titulo in titulos.items():
        itens = pub.get(chave) or []
        if not itens:
            continue
        total = sum((i.get("valor") or 0) for i in itens) or 0
        if total <= 0:
            continue
        publico.append({"titulo": titulo, "metrica": pub.get("metrica", "Resultados"),
                        "itens": [{"rotulo": i["rotulo"], "valor": formatar(i.get("valor"), "int"),
                                   "pct": round((i.get("valor") or 0) / total, 4)}
                                  for i in sorted(itens, key=lambda i: i.get("valor") or 0, reverse=True)[:6]]})

    per = r["periodo"]
    tipo_rot = {"mensal": "Relatório mensal", "semanal": "Relatório semanal", "campanha": "Relatório de campanha",
                "personalizado": "Relatório do período"}.get(per.get("tipo"), "Relatório")
    ctt = ident.get("contato") or {}
    contato = " · ".join(x for x in [ctt.get("whatsapp"), ctt.get("email"), ctt.get("instagram"), ctt.get("site")] if x)

    limitacoes = list(r.get("limitacoes") or [])
    exibidas = {heroi["chave"]} | {m["chave"] for m in principais + secundarias}
    calc = [c for c in calc if c in exibidas]
    if calc:
        nomes = {"cpl": f"Custo por {rot_leads(t)[1]}", "leads": cap(rot_leads(t)[0])} if t.get("rotulo_leads") else {}
        rot = ", ".join(nomes.get(c, METRICAS[c][0]) for c in calc if c in METRICAS)
        limitacoes.append(f"Calculado a partir dos dados do Meta (não veio pronto): {rot}.")
    if foco == "cac":
        limitacoes.append("CAC de mídia considera só o investimento em anúncios e só as vendas que o Meta atribuiu "
                          "aos anúncios. Não inclui outros custos de aquisição.")
    aviso_atrib = r.get("aviso_atribuicao")
    if aviso_atrib is None:
        aviso_atrib = ("Os números dos últimos dias podem mudar um pouco: o Meta continua atribuindo conversões "
                       "por alguns dias depois que elas acontecem.")

    return {
        "exemplo": bool(r.get("exemplo")),
        "tema_html": (ident.get("html") or {}).get("tema", "escuro"),
        "marca": {"nome": ident.get("marca") or "", "responsavel": ident.get("responsavel") or "",
                  "logo": data_uri(pasta_ident / ident["logo"], svg=True) if ident.get("logo") else None,
                  "logo_fundo": ident.get("logo_fundo", "auto"),
                  "contato": contato, "rodape": ident.get("rodape") or ""},
        "cliente": r.get("cliente") or "",
        "tipo": tipo_rot,
        "periodo": per.get("rotulo") or periodo_extenso(per["inicio"], per["fim"]),
        "datas": f"{data_br(per['inicio'])} a {data_br(per['fim'])}" if per.get("rotulo") else "",
        "campanha": per.get("campanha"),
        "foco": foco,
        "foco_rotulo": (f"{cap(rot_leads(t)[0])} e custo por {rot_leads(t)[1]}" if foco == "leads" and t.get("rotulo_leads")
                        else FOCOS[foco]["rotulo"]),
        "desempenho": r.get("desempenho") or "dentro",
        "comparado_com": (ant or {}).get("rotulo"),
        "heroi": heroi, "principais": principais, "secundarias": secundarias, "cac": cac_comp,
        "serie": serie, "campanhas": campanhas, "criativos": criativos, "publico": publico,
        "alteracoes": r.get("alteracoes") or [],
        "leitura": r.get("leitura") or {},
        "limitacoes": limitacoes,
        "mostra_alcance": "alcance" in exibidas,
        "aviso_atribuicao": aviso_atrib,
        "fonte": {"meta_mcp": "Meta Ads (API oficial)", "chrome": "Gerenciador de Anúncios do Meta",
                  "csv": "exportação do Gerenciador de Anúncios do Meta"}.get(
                      (ler_json(pasta_config() / "config.json", {}) or {}).get("fonte_dados") if r.get("exemplo")
                      else r.get("fonte"), "Meta Ads"),
        "gerado_em": data_br(agora_iso()),
        "link": link,
    }


def css_vars(cores: dict, alvo: str) -> str:
    p = cores[alvo]
    pares = {"--marca": cores["marca"], "--sobre-marca": cores["sobre_marca"], "--positivo": cores["positivo"],
             "--negativo": cores["negativo"], "--fundo": p["fundo"], "--superficie": p["superficie"],
             "--texto": p["texto"], "--texto-suave": p["texto_suave"], "--linha": p["linha"], "--destaque": p["destaque"]}
    return ":root{" + ";".join(f"{k}:{v}" for k, v in pares.items()) + "}"


def preencher(template: Path, vm: dict, ident: dict, alvo: str) -> str:
    h = template.read_text(encoding="utf-8")
    fonte = ident.get("fonte_google")
    link_fonte = (f'<link rel="preconnect" href="https://fonts.googleapis.com">'
                  f'<link href="https://fonts.googleapis.com/css2?family={fonte.replace(" ", "+")}:wght@400;500;600;700;800&display=swap" rel="stylesheet">'
                  if fonte else "")
    familia = f"'{fonte}', " if fonte else ""
    dados = json.dumps(vm, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e")
    titulo = f"{vm['cliente']} · {vm['periodo']}" if vm["cliente"] else vm["periodo"]
    return (h.replace("{{CSS_VARS}}", css_vars(ident["cores"], alvo))
             .replace("{{FONTE_LINK}}", link_fonte)
             .replace("{{FONTE_FAMILIA}}", familia)
             .replace("{{TITULO}}", html.escape(titulo))
             .replace("{{DADOS_JSON}}", dados))


# ------------------------------------------------------------------ main

def carregar_identidade(nome: str | None) -> tuple[dict, Path]:
    cfg = ler_json(pasta_config() / "config.json", {}) or {}
    nome = nome or cfg.get("identidade_padrao")
    if nome:
        pasta = pasta_config() / "identidades" / nome
        ident = ler_json(pasta / "identidade.json")
        if ident:
            return ident, pasta
        raise SystemExit(f"Identidade '{nome}' não encontrada em {pasta}. Rode 'config.py identidades'.")
    # sem identidade configurada: padrão neutro da skill
    return ler_json(ASSETS / "identidade.template.json"), ASSETS


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("relatorio")
    ap.add_argument("--identidade")
    ap.add_argument("--saida")
    ap.add_argument("--formatos", default="pdf,html")
    ap.add_argument("--link")
    ap.add_argument("--so-validar", action="store_true")
    a = ap.parse_args()

    arq = Path(a.relatorio).expanduser().resolve()
    r = ler_json(arq)
    if r is None:
        print(f"Não encontrei {arq}.", file=sys.stderr)
        return 2
    foco = r.get("foco")
    if foco not in FOCOS:
        print(f"Foco inválido: {foco!r}. Use um de: {', '.join(FOCOS)}.", file=sys.stderr)
        return 2
    per = r.get("periodo") or {}
    if not per.get("inicio") or not per.get("fim"):
        print("Faltou periodo.inicio / periodo.fim no relatorio.json.", file=sys.stderr)
        return 2
    datas = [("periodo.inicio", per["inicio"]), ("periodo.fim", per["fim"])] + [
        (f"serie_diaria[{i}].data", d.get("data")) for i, d in enumerate(r.get("serie_diaria") or [])]
    for campo, valor in datas:
        try:
            datetime.strptime(str(valor), "%Y-%m-%d")
        except ValueError:
            print(f"Data fora do formato em {campo}: {valor!r}. Use AAAA-MM-DD (ex.: 2026-09-30).", file=sys.stderr)
            return 2
    if (r.get("totais") or {}).get("investimento") is None:
        print("Faltou totais.investimento: sem investimento não existe relatório.", file=sys.stderr)
        return 2

    t, calc = derivar(r.get("totais"))
    ant = None
    if r.get("anterior"):
        ant, _ = derivar(r["anterior"])
        ant["rotulo"] = r["anterior"].get("rotulo")

    ok, sugestao = checar_foco(foco, t)
    if not ok:
        faltou = ", ".join(METRICAS[k][0].lower() for k in FOCOS[foco]["requer"])
        print(json.dumps({"erro": "foco_sem_dados", "foco": foco, "faltou": faltou, "sugestao": sugestao,
                          "mensagem": f"O foco '{FOCOS[foco]['rotulo']}' precisa de {faltou}, que não veio nos dados "
                                      f"(ex.: campanha sem evento de compra/pixel). "
                                      + (f"Os dados sustentam o foco '{FOCOS[sugestao]['rotulo']}'." if sugestao
                                         else "Nenhum outro foco tem dados suficientes.")},
                         ensure_ascii=False, indent=2))
        return 4
    if foco == "vendas" and t.get("roas") is None:
        r.setdefault("limitacoes", []).append("ROAS não exibido: não veio valor de compra confiável nos dados.")

    resumo = {"foco": foco, "totais": t, "calculado": calc, "anterior": ant}
    if a.so_validar:
        print(json.dumps({"ok": True, **resumo}, ensure_ascii=False, indent=2, default=str))
        return 0

    ident, pasta_ident = carregar_identidade(a.identidade)
    formatos = [f.strip() for f in a.formatos.split(",") if f.strip()]
    cfg = ler_json(pasta_config() / "config.json", {}) or {}
    raiz = Path(cfg["pasta_relatorios"]).expanduser() if cfg.get("pasta_relatorios") else pasta_config() / "relatorios"
    saida = Path(a.saida).expanduser() if a.saida else (
        raiz / slug(r.get("cliente") or "cliente") / f"{per['inicio']}_{per['fim']}")
    saida.mkdir(parents=True, exist_ok=True)

    vm = montar_vm(r, t, ant, foco, ident, pasta_ident, calc, arq, a.link)
    gerados = []
    if "pdf" in formatos:
        (saida / "relatorio-pdf.html").write_text(preencher(ASSETS / "template-pdf.html", vm, ident, "pdf"), encoding="utf-8")
        gerados.append(str(saida / "relatorio-pdf.html"))
    if "html" in formatos:
        (saida / "dashboard").mkdir(exist_ok=True)
        (saida / "dashboard" / "index.html").write_text(
            preencher(ASSETS / "template-dashboard.html", vm, ident, "html"), encoding="utf-8")
        gerados.append(str(saida / "dashboard" / "index.html"))
    msg = mensagem(r, t, foco, a.link, formatos)
    (saida / "mensagem.txt").write_text(msg, encoding="utf-8")
    gravar_json(saida / "resumo.json", resumo)
    print(json.dumps({"ok": True, "pasta": str(saida), "arquivos": gerados + [str(saida / "mensagem.txt")],
                      "calculado": calc, "avisos": AVISOS, "mensagem": msg}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
