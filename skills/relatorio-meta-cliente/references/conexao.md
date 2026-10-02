# Modo A — Conexão

Pesquisado em setembro de 2026. Comandos e nomes da Meta mudam: se um passo não bater com o
que a pessoa vê na tela, pesquise a documentação atual antes de insistir (links no fim).

## 0. Checagem do ambiente

```bash
python3 <skill>/scripts/checar_ambiente.py
```

| Item | Para quê | Instalar |
|---|---|---|
| Python 3.9+ | tudo | python.org (ou `brew install python`, se o Mac tiver Homebrew) |
| Playwright | PDF e prévias | `pip3 install playwright` |
| Chromium | PDF e prévias | `python3 -m playwright install chromium` |
| pypdf (opcional) | conferir páginas do PDF | `pip3 install pypdf` |
| Pillow (opcional) | ler cores da logo | `pip3 install pillow` |
| openpyxl (opcional) | ler planilha XLSX | `pip3 install openpyxl` |
| Node.js 22+ | publicar o HTML | instalador LTS em nodejs.org (ou `brew install node`, se tiver Homebrew) |
| Wrangler | publicar o HTML | roda via `npx wrangler` (baixa sozinho) ou `npm install -g wrangler` |

Para cada item faltando, pergunte [Instalar agora] [Pular por enquanto]. Rode o comando só
depois do "sim". O `checar_ambiente.py` já mostra o comando certo para o computador (sem
Homebrew no Mac, ele indica o instalador do site). No Windows, troque `python3`/`pip3` por
`python`/`pip`. Se `pip3 install` reclamar de "externally-managed-environment", use
`pip3 install --user playwright` ou `python3 -m pip install --user playwright`.

## 1. Fonte de dados

### Opção 1 (recomendada): MCP oficial do Meta Ads

Servidor remoto da Meta, `https://mcp.facebook.com/ads`, transporte HTTP. É o caminho mais
rápido e estável: os dados vêm direto da API, sem navegar em tela.

1. No terminal (fora do Claude Code), adicionar o servidor com o nome `meta-ads`, valendo
   para todas as pastas (`--scope user`). O nome importa: a skill bloqueia as ferramentas de
   escrita por esse nome.
   ```bash
   claude mcp add --scope user --transport http meta-ads https://mcp.facebook.com/ads
   ```
   Quem tem app próprio no Meta for Developers pode passar o ID do app:
   ```bash
   claude mcp add --scope user --transport http --client-id <ID_DO_APP> meta-ads https://mcp.facebook.com/ads
   ```
2. Abrir o Claude Code de novo, rodar `/mcp`, escolher `meta-ads` → **Authenticate**. O
   navegador abre o "Login do Facebook para Empresas". Entrar com a conta que tem acesso às
   BMs dos clientes e aprovar as permissões.
3. Voltar ao Claude Code. Em `/mcp`, o `meta-ads` deve aparecer como conectado.

**Bloquear escrita (recomendado).** O MCP da Meta também cria, edita, apaga e ativa
campanhas, públicos, criativos, pixels e catálogos. Esta skill nunca usa essas ferramentas.
O Claude Code só as tira do alcance no turno em que a skill começa; da segunda mensagem em
diante, quem segura é a regra da skill. Para um bloqueio de verdade, que vale sempre e com
qualquer nome de conector, sugira adicionar ao `~/.claude/settings.json`:

```json
{
  "permissions": {
    "deny": [
      "mcp__*__ads_create_*", "mcp__*__ads_update_*", "mcp__*__ads_delete_*",
      "mcp__*__ads_activate_entity", "mcp__*__ads_boost_ig_post",
      "mcp__*__ads_creative_*", "mcp__*__ads_finalize_local_ad_image_upload",
      "mcp__*__ads_pixel_*_create", "mcp__*__ads_pixel_*_update", "mcp__*__ads_pixel_*_delete",
      "mcp__*__ads_catalog_*create*", "mcp__*__ads_catalog_*update*", "mcp__*__ads_catalog_*delete*",
      "mcp__*__ads_catalog_event_source_connect", "mcp__*__ads_catalog_event_source_disconnect",
      "mcp__*__ads_experiment_*_create_test", "mcp__*__ads_experiment_*_update_test"
    ]
  }
}
```

Isso vale para o Claude Code inteiro, não só para o relatório: com o bloqueio ativo, nenhuma
conversa cria ou altera nada no Meta. As leituras (`ads_get_*`, `ads_insights_*`) continuam
liberadas. Mostre o trecho e deixe a pessoa decidir. Não edite `settings.json` sem um "sim"
explícito. Se o arquivo já existir, junte a lista ao `permissions.deny` que já estiver lá.

Se o conector do Meta estiver ligado por outro caminho (ex.: conector do claude.ai), as
ferramentas aparecem com outro prefixo (`mcp__claude_ai_...`). O bloqueio acima cobre esse
caso. Use só as ferramentas `ads_*` de leitura, qualquer que seja o prefixo.

### Opção 2: Claude in Chrome

Para quem não conseguiu liberar o MCP. O Claude abre o Gerenciador de Anúncios no Chrome já
logado e exporta a tabela.

Requisitos: Chrome (ou Edge, Brave, Arc), extensão "Claude in Chrome" 1.0.36+, plano Pro, Max,
Team ou Enterprise, e login no Claude Code com `/login` (com chave de API a integração fica
desligada).

1. Instalar a extensão na Chrome Web Store e entrar com a mesma conta do Claude.
2. Iniciar com `claude --chrome`, ou rodar `/chrome` e escolher "Enabled by default".
3. Conferir em `/chrome`: "Status: Enabled" e "Extension: Installed". Se a extensão não for
   detectada, reiniciar o Chrome.

No uso, o fluxo é: abrir `https://adsmanager.facebook.com/`, escolher a conta, ajustar o
período, selecionar as campanhas e exportar a tabela em CSV (mesmo caminho da opção 3),
depois converter com `csv_para_json.py`. Login, 2FA e CAPTCHA são sempre da pessoa: pare e
peça para ela resolver. Nunca digite senha.

### Opção 3: CSV exportado à mão

1. Abrir o Gerenciador de Anúncios no computador (não funciona no celular).
2. Escolher a conta, o período e o nível (Campanhas).
3. Em **Colunas**, usar "Desempenho" ou personalizar com: Valor usado, Resultados, Custo por
   resultado, Alcance, Impressões, Frequência, Cliques no link, CTR (taxa de cliques no link),
   Compras, Valor de conversão de compras, Leads, ThruPlays.
4. Para ter gráfico dia a dia: **Detalhamento → Por tempo → Dia**. Nesse caso, exporte
   também uma vez sem divisão por dia, porque alcance não pode ser somado entre dias.
5. **Relatórios → Exportar dados da tabela → CSV** (o nome do botão pode variar um pouco).
6. Informar o caminho do arquivo (ou arrastar para a conversa).

O conversor aceita cabeçalhos em português ou inglês. Coluna que ele não reconhecer aparece
em `colunas_ignoradas`: se for importante, avise a pessoa.

## 2. Teste de acesso (MCP)

Chame `ads_get_ad_accounts`. Mostre uma tabela: BM (se vier), conta, ID, moeda, status e se
dá para consultar. Depois pergunte "Essas são todas as contas? [Sim, está completo]
[Falta alguma]".

Conta que não pode ser consultada (campo `is_queryable` falso, ou erro ao consultar):

| Sinal | O que dizer | Próximo passo |
|---|---|---|
| `is_ads_mcp_enabled: false` | A Meta ainda não liberou o MCP para essa conta. A liberação é gradual e não depende de nós. | Usar Chrome ou CSV para essa conta até liberar. |
| `is_queryable: false` ou erro de permissão | O usuário conectado não tem acesso de leitura a essa conta. | Na BM do cliente, dar acesso de Analista (ou mais) ao usuário, e reconectar em `/mcp`. |
| Conta desativada / com pagamento pendente | A conta está com restrição na Meta. | Resolver no Gerenciador; o relatório de períodos passados ainda pode funcionar. |

"Falta alguma": o motivo quase sempre é acesso. Explique que a conta precisa estar
compartilhada com o usuário do Facebook que autenticou, e que depois é só reautenticar em
`/mcp`.

Não grave IDs de conta em nenhum lugar além de `clientes.json` (feito no Modo C).

## Fontes

- Meta Ads MCP: developers.facebook.com/documentation/ads-commerce/ads-ai-connectors/ads-mcp-server/
- Claude in Chrome: code.claude.com/docs/en/chrome
- Wrangler / Pages: developers.cloudflare.com/workers/wrangler/commands/pages/
