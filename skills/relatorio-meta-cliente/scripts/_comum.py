"""
Funções compartilhadas pelos scripts da skill relatorio-meta-cliente.

A configuração do usuário fica FORA da pasta da skill, para que atualizar a skill
nunca apague nada:

    ~/.relatorio-meta-cliente/          (ou o caminho em RMC_HOME)
    ├── config.json                     fonte de dados, identidade padrão, publicação
    ├── clientes.json                   conta de anúncio ↔ cliente
    ├── controle.json                   relatórios emitidos
    ├── identidades/<slug>/identidade.json + logo.*
    ├── relatorios/<cliente>/<periodo>/ arquivos gerados
    └── publicar/<projeto>/             pasta enviada ao Cloudflare Pages
"""

from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

for _f in (sys.stdout, sys.stderr):  # Windows em pt-BR usa cp1252 e quebra com acentos e emoji
    try:
        _f.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

PASTA_SKILL = Path(__file__).resolve().parent.parent
ASSETS = PASTA_SKILL / "assets"


def pasta_config() -> Path:
    base = os.environ.get("RMC_HOME")
    return Path(base).expanduser() if base else Path.home() / ".relatorio-meta-cliente"


def ler_json(caminho: Path, padrao=None):
    caminho = Path(caminho)
    if not caminho.exists():
        return padrao
    return json.loads(caminho.read_text(encoding="utf-8"))


def gravar_json(caminho: Path, dados) -> None:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_suffix(caminho.suffix + ".tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(caminho)


def slug(texto: str) -> str:
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    return t or "sem-nome"


def agora_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


# ---------------------------------------------------------------- formatação pt-BR

def _milhar(inteiro: str) -> str:
    neg = inteiro.startswith("-")
    d = inteiro.lstrip("-")
    partes = []
    while len(d) > 3:
        partes.insert(0, d[-3:])
        d = d[:-3]
    partes.insert(0, d)
    return ("-" if neg else "") + ".".join(partes)


def num_br(valor: float, casas: int = 0) -> str:
    s = f"{valor:.{casas}f}"
    if casas:
        inteiro, dec = s.split(".")
        return f"{_milhar(inteiro)},{dec}"
    return _milhar(s)


SIMBOLOS = {"BRL": "R$", "USD": "US$", "EUR": "€", "ARS": "AR$", "MXN": "MX$", "CLP": "CLP$", "COP": "COL$", "PYG": "₲", "UYU": "$U"}


def moeda_br(valor: float, moeda: str = "BRL") -> str:
    return f"{SIMBOLOS.get(moeda, moeda)}\u00a0{num_br(valor, 2)}"  # espaço que não quebra linha


def formatar(valor, tipo: str, moeda: str = "BRL") -> str:
    if valor is None:
        return "—"
    if tipo == "moeda":
        return moeda_br(valor, moeda)
    if tipo == "int":
        return num_br(round(valor), 0)
    if tipo == "dec":
        return num_br(valor, 2)
    if tipo == "pct":
        return num_br(valor, 2 if abs(valor) < 10 else 1) + "%"
    if tipo == "roas":
        return num_br(valor, 2) + "x"
    return str(valor)


def data_br(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        return datetime.strptime(iso[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return iso


MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]


def periodo_extenso(inicio: str, fim: str) -> str:
    a = datetime.strptime(inicio[:10], "%Y-%m-%d")
    b = datetime.strptime(fim[:10], "%Y-%m-%d")
    if a.year == b.year and a.month == b.month:
        return f"{a.day} a {b.day} de {MESES[b.month - 1]} de {b.year}"
    if a.year == b.year:
        return f"{a.day} de {MESES[a.month - 1]} a {b.day} de {MESES[b.month - 1]} de {b.year}"
    return f"{data_br(inicio)} a {data_br(fim)}"
