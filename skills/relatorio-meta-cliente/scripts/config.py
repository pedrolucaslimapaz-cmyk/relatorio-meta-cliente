#!/usr/bin/env python3
"""
Lê e grava a configuração do usuário em ~/.relatorio-meta-cliente/ (ou RMC_HOME).

Comandos:
  status                                  diz em que modo a skill está (A, B ou C) e o que falta
  init --fonte meta_mcp|chrome|csv        cria/atualiza config.json
  set <chave.pontilhada> <valor>          ex.: set publicacao.cloudflare true
  identidades                             lista as identidades visuais
  identidade-nova --nome "Marca" --logo <arquivo> [--padrao]
  identidade-padrao <slug>
  identidade-set <slug> <chave.pontilhada> <valor>   ex.: identidade-set minha-marca aprovada true
  cliente --conta act_123 --nome "Cliente" [--identidade slug] [--projeto nome-no-cloudflare] [--contato "Ana"]
          (sem ID de conta, como no CSV, use --conta csv:<nome-do-cliente>)
  cliente-buscar --conta act_123
  emitido --conta act_123 --inicio AAAA-MM-DD --fim AAAA-MM-DD [--campanha ID]
  registrar --arquivo registro.json       acrescenta um relatório ao controle.json

Nunca grava token, senha ou chave de API. Se receber um, recusa.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _comum import ASSETS, agora_iso, gravar_json, ler_json, pasta_config, slug  # noqa: E402

FONTES = ("meta_mcp", "chrome", "csv")
PROIBIDO = ("token", "senha", "password", "secret", "api_key", "apikey")


def _cfg_path() -> Path:
    return pasta_config() / "config.json"


def _cfg() -> dict:
    return ler_json(_cfg_path(), {}) or {}


def _identidades() -> list[dict]:
    base = pasta_config() / "identidades"
    saida = []
    if base.exists():
        for d in sorted(base.iterdir()):
            ident = ler_json(d / "identidade.json")
            if ident:
                saida.append({"slug": d.name, "marca": ident.get("marca"),
                              "cores_definidas": bool(ident.get("cores_aprovadas")),
                              "aprovada": bool(ident.get("aprovada")),
                              "logo": ident.get("logo")})
    return saida


def cmd_status(_a) -> int:
    cfg = _cfg()
    idents = _identidades()
    clientes = ler_json(pasta_config() / "clientes.json", {}) or {}
    pend = []
    if not cfg.get("fonte_dados"):
        pend.append("Conexão com os dados do Meta ainda não configurada (Modo A).")
    if not idents:
        pend.append("Nenhuma identidade visual criada (Modo B).")
    elif not any(i["aprovada"] for i in idents):
        pend.append("Identidade visual criada mas ainda não aprovada (Modo B, passo 5).")
    pub = cfg.get("publicacao", {})
    if pub.get("cloudflare") is None:
        pend.append("Publicação do HTML não decidida (opcional).")
    elif pub.get("cloudflare") == "pendente":
        pend.append("Publicação do HTML ficou para depois: ofereça configurar o Cloudflare quando o gestor pedir link.")

    if not cfg.get("fonte_dados"):
        modo = "A"
    elif not any(i["aprovada"] for i in idents):
        modo = "B"
    else:
        modo = "C"

    print(json.dumps({
        "pasta_config": str(pasta_config()),
        "modo": modo,
        "fonte_dados": cfg.get("fonte_dados"),
        "identidades": idents,
        "identidade_padrao": cfg.get("identidade_padrao"),
        "clientes_cadastrados": len(clientes.get("contas", {})),
        "publicacao": pub,
        "pendencias": pend,
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_init(a) -> int:
    cfg = _cfg()
    cfg.setdefault("schema", 1)
    cfg.setdefault("criado_em", agora_iso())
    cfg["fonte_dados"] = a.fonte
    cfg.setdefault("publicacao", {"cloudflare": None})
    cfg["atualizado_em"] = agora_iso()
    gravar_json(_cfg_path(), cfg)
    print(f"OK: config.json salvo em {_cfg_path()} (fonte de dados: {a.fonte})")
    return 0


def _valor(txt: str):
    for conv in (json.loads,):
        try:
            return conv(txt)
        except Exception:
            pass
    return txt


def cmd_set(a) -> int:
    if any(p in a.chave.lower() for p in PROIBIDO):
        print("Recusado: credenciais nunca são gravadas na configuração. "
              "Use 'wrangler login' ou a variável de ambiente CLOUDFLARE_API_TOKEN.", file=sys.stderr)
        return 2
    cfg = _cfg()
    alvo = cfg
    partes = a.chave.split(".")
    for p in partes[:-1]:
        alvo = alvo.setdefault(p, {})
    alvo[partes[-1]] = _valor(a.valor)
    cfg["atualizado_em"] = agora_iso()
    gravar_json(_cfg_path(), cfg)
    print(f"OK: {a.chave} = {alvo[partes[-1]]!r}")
    return 0


def cmd_identidades(_a) -> int:
    print(json.dumps({"padrao": _cfg().get("identidade_padrao"), "identidades": _identidades()},
                     ensure_ascii=False, indent=2))
    return 0


def cmd_identidade_nova(a) -> int:
    logo = Path(a.logo).expanduser()
    if not logo.exists():
        print(f"Não encontrei a logo em: {logo}\n"
              "Próximo passo: arraste o arquivo da logo para a conversa ou informe o caminho completo "
              "(ex.: /Users/seunome/Desktop/logo.png).", file=sys.stderr)
        return 2
    if logo.suffix.lower() not in (".png", ".jpg", ".jpeg", ".svg", ".webp"):
        print("Formato de logo não suportado. Use PNG (de preferência com fundo transparente), JPG, SVG ou WEBP.",
              file=sys.stderr)
        return 2
    s = slug(a.slug or a.nome)
    pasta = pasta_config() / "identidades" / s
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / f"logo{logo.suffix.lower()}"
    shutil.copy2(logo, destino)

    ident = ler_json(pasta / "identidade.json") or ler_json(ASSETS / "identidade.template.json")
    ident["marca"] = a.nome
    ident["logo"] = destino.name
    ident["atualizado_em"] = agora_iso()
    gravar_json(pasta / "identidade.json", ident)

    cfg = _cfg()
    if a.padrao or not cfg.get("identidade_padrao"):
        cfg["identidade_padrao"] = s
        gravar_json(_cfg_path(), cfg)
    print(json.dumps({"slug": s, "pasta": str(pasta), "logo": str(destino)}, ensure_ascii=False))
    return 0


def cmd_identidade_padrao(a) -> int:
    if not (pasta_config() / "identidades" / a.slug / "identidade.json").exists():
        print(f"Identidade '{a.slug}' não existe. Rode 'identidades' para ver as disponíveis.", file=sys.stderr)
        return 2
    cfg = _cfg()
    cfg["identidade_padrao"] = a.slug
    gravar_json(_cfg_path(), cfg)
    print(f"OK: identidade padrão = {a.slug}")
    return 0


def cmd_identidade_set(a) -> int:
    if any(p in a.chave.lower() for p in PROIBIDO):
        print("Recusado: credenciais nunca são gravadas na configuração.", file=sys.stderr)
        return 2
    arq = pasta_config() / "identidades" / a.slug / "identidade.json"
    ident = ler_json(arq)
    if ident is None:
        print(f"Identidade '{a.slug}' não existe. Rode 'identidades' para ver as disponíveis.", file=sys.stderr)
        return 2
    alvo = ident
    partes = a.chave.split(".")
    for p in partes[:-1]:
        alvo = alvo.setdefault(p, {})
    alvo[partes[-1]] = _valor(a.valor)
    ident["atualizado_em"] = agora_iso()
    gravar_json(arq, ident)
    print(f"OK: {a.slug}.{a.chave} = {alvo[partes[-1]]!r}")
    return 0


def _clientes() -> dict:
    return ler_json(pasta_config() / "clientes.json", {"schema": 1, "contas": {}}) or {"schema": 1, "contas": {}}


def cmd_cliente(a) -> int:
    dados = _clientes()
    reg = dados["contas"].get(a.conta, {})
    reg["cliente"] = a.nome
    if a.identidade:
        reg["identidade"] = a.identidade
    if a.projeto:
        reg["projeto_cloudflare"] = slug(a.projeto)
    if a.contato:
        reg["contato"] = a.contato
    reg.setdefault("projeto_cloudflare", slug(a.nome))
    reg["atualizado_em"] = agora_iso()
    dados["contas"][a.conta] = reg
    gravar_json(pasta_config() / "clientes.json", dados)
    print(json.dumps({a.conta: reg}, ensure_ascii=False))
    return 0


def cmd_cliente_buscar(a) -> int:
    reg = _clientes()["contas"].get(a.conta)
    print(json.dumps(reg, ensure_ascii=False) if reg else "null")
    return 0 if reg else 1


def _controle() -> dict:
    return ler_json(pasta_config() / "controle.json", {"schema": 1, "relatorios": []}) or {"schema": 1, "relatorios": []}


def cmd_emitido(a) -> int:
    achados = [r for r in _controle()["relatorios"]
               if r.get("conta") == a.conta and r.get("inicio") == a.inicio and r.get("fim") == a.fim
               and (r.get("campanha_id") or None) == (a.campanha or None)]
    if not achados:
        print("Nenhum relatório emitido para esse recorte. Pode gerar.")
        return 0
    ult = achados[-1]
    print(json.dumps({"ja_emitido": True, "versoes": len(achados), "ultimo": ult,
                      "proxima_versao": len(achados) + 1}, ensure_ascii=False, indent=2))
    return 1


def cmd_registrar(a) -> int:
    reg = json.loads(Path(a.arquivo).read_text(encoding="utf-8"))
    if any(p in json.dumps(reg).lower() for p in ("cloudflare_api_token", "access_token")):
        print("Recusado: o registro contém algo que parece credencial.", file=sys.stderr)
        return 2
    reg.setdefault("registrado_em", agora_iso())
    ctrl = _controle()
    ctrl["relatorios"].append(reg)
    gravar_json(pasta_config() / "controle.json", ctrl)
    print(f"OK: registrado ({len(ctrl['relatorios'])} relatórios no controle)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status").set_defaults(f=cmd_status)
    p = sub.add_parser("init"); p.add_argument("--fonte", choices=FONTES, required=True); p.set_defaults(f=cmd_init)
    p = sub.add_parser("set"); p.add_argument("chave"); p.add_argument("valor"); p.set_defaults(f=cmd_set)
    sub.add_parser("identidades").set_defaults(f=cmd_identidades)
    p = sub.add_parser("identidade-nova"); p.add_argument("--nome", required=True); p.add_argument("--logo", required=True)
    p.add_argument("--slug"); p.add_argument("--padrao", action="store_true"); p.set_defaults(f=cmd_identidade_nova)
    p = sub.add_parser("identidade-padrao"); p.add_argument("slug"); p.set_defaults(f=cmd_identidade_padrao)
    p = sub.add_parser("identidade-set"); p.add_argument("slug"); p.add_argument("chave"); p.add_argument("valor")
    p.set_defaults(f=cmd_identidade_set)
    p = sub.add_parser("cliente"); p.add_argument("--conta", required=True); p.add_argument("--nome", required=True)
    p.add_argument("--identidade"); p.add_argument("--projeto"); p.add_argument("--contato")
    p.set_defaults(f=cmd_cliente)
    p = sub.add_parser("cliente-buscar"); p.add_argument("--conta", required=True); p.set_defaults(f=cmd_cliente_buscar)
    p = sub.add_parser("emitido"); p.add_argument("--conta", required=True); p.add_argument("--inicio", required=True)
    p.add_argument("--fim", required=True); p.add_argument("--campanha"); p.set_defaults(f=cmd_emitido)
    p = sub.add_parser("registrar"); p.add_argument("--arquivo", required=True); p.set_defaults(f=cmd_registrar)
    a = ap.parse_args()
    return a.f(a)


if __name__ == "__main__":
    raise SystemExit(main())
