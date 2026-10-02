# Coleta de dados do Meta (Modo C, passo 5)

Somente ferramentas de **leitura**. Nunca chame ferramenta que cria, altera, ativa ou pausa.

## Ferramentas

| Necessidade | Ferramenta | Observações |
|---|---|---|
| Contas | `ads_get_ad_accounts` | Confira `is_queryable` / `is_ads_mcp_enabled` antes de consultar. |
| Campanha, conjuntos, anúncios, métricas | `ads_get_ad_entities` | Ferramenta central. `level` = account / campaign / adset / ad. `time_range` com `since` e `until`. |
| Série diária | `ads_get_ad_entities` + `time_increment: "1"` | Não existe ferramenta separada de série temporal. |
| Idade, gênero, região, posicionamento, dispositivo | `ads_get_ad_entities` + `breakdowns` | **Um breakdown por chamada.** Se vier vazio, registre em limitações. |
| Validar um campo | `ads_get_field_context` | Antes de usar qualquer campo que você não tenha certeza que existe. |
| Textos e mídia dos criativos | `ads_get_creatives` | Listagem traz só id/nome; chame de novo com `creative_ids` para body, title, image_url, thumbnail_url. |
| Imagem e vídeo | `ads_get_ad_images` / `ads_get_ad_videos` | Para URLs válidas. |
| Histórico de alterações | `ads_account_get_activity_logs` | Explica picos e quedas: pausa, orçamento, troca de criativo. |
| Teste A/B no período | `ads_experiment_list_tests` | Se houve, diga no relatório: muda a leitura. |
| Benchmark de mercado | `ads_insights_industry_benchmark` | Só se o gestor pedir. Sempre rotulado como referência externa. |

## Campos úteis

Nomes aceitos pelo MCP oficial (conferidos com `ads_get_field_context` em 26/09/2026):
`amount_spent` (alias `spend`), `impressions`, `reach`, `frequency`, `link_click`
(cliques no link), `website_ctr` (CTR de link, já em %), `cpm`, `results`, `cost_per_result`,
`omni_purchase` (compras), `omni_purchase_values` (valor das compras), `purchase_roas`,
`cost_per_omni_purchase`, `lead`, `omni_landing_page_view`, `video_thruplay_watched_actions`,
`post_engagement`, `objective`, `effective_status`.

Não existem neste MCP (voltam em `unknown_fields`): `inline_link_clicks`,
`inline_link_click_ctr`, `cost_per_inline_link_click`, `actions`, `action_values`,
`inline_post_engagement`. Os tipos de ação viram campos próprios (`omni_purchase`, `lead`,
`link_click`). Na dúvida, rode `ads_get_field_context` antes.

Cuidados verificados:
- `cost_per_result` não existe em nível de conta (só campanha, conjunto, anúncio).
- `omni_purchase_values` e `video_thruplay_watched_actions` não são filtráveis.
- Valores monetários podem vir na menor unidade da moeda (centavos). Confira com
  `ads_get_field_context` ou comparando com o Gerenciador, e **converta para reais antes de
  gravar no JSON**. O JSON é sempre em unidades normais (R$ 1.234,56 = `1234.56`).
- Compras: use `omni_purchase` (já consolida pixel e compras no Meta). Não some com outros
  tipos de compra, senão conta em dobro.
- Leads: `lead`. Mesmo cuidado de não somar tipos que se sobrepõem.
- Campo que volta `null` = o Meta não mediu. Grave `null`, não `0`.
- ROAS: `purchase_roas` já é valor de compra ÷ investimento. Grave `valor_compras`
  (preferível) ou `roas`; o script calcula o outro.

## Ordem da coleta

1. `level: "campaign"`, período inteiro → totais, nomes, objetivos. Se o relatório é da conta
   inteira, some as campanhas **com gasto** ou use `level: "account"` (para alcance total,
   prefira `account`: alcance não se soma entre campanhas).
2. Mesmo nível, `time_increment: "1"` → `serie_diaria`.
3. `level: "adset"` → só para explicar o que puxou o resultado (entra na leitura, não em
   tabela).
4. `level: "ad"` → desempenho por anúncio. Escolha os criativos por ordem de importância
   (maior volume e melhor custo por resultado com volume): **o PDF mostra os 3 primeiros**
   (uma linha), o dashboard até 6.
   Cuidados verificados no MCP:
   - `sort` e `filtering` em `level: "ad"` não são confiáveis (a ordenação é ignorada e o
     filtro devolve anúncios sem métrica). Traga tudo numa chamada (`limit` 500,
     filtro só de `amount_spent > 0`) e ordene/agrupe você.
   - Contas que duplicam campanhas toda semana repetem o mesmo anúncio com o mesmo nome.
     Agrupe por nome do anúncio (somando gasto, compras, valor, cliques e impressões) e use
     o `creative_id` de maior gasto do grupo para a imagem.
   - Muitas campanhas com nomes de código: agrupe por objetivo na tabela de `campanhas`
     (ex.: "Vendas | Loja online (4 campanhas semanais)"), explique em `limitacoes`
     e confirme com o gestor na conferência.
5. `ads_get_creatives` com os `creative_ids` escolhidos → texto e imagem. Baixe a imagem
   (`curl -sL -o <pasta>/criativo-1.jpg "<url>"`, na mesma pasta do `relatorio.json`) e
   grave o nome do arquivo em `criativos[].imagem`. URL remota não entra no relatório: expira
   e deixa buraco. O script só embute PNG, JPG, WebP ou GIF de dentro dessa pasta.
   Criativo de vídeo: o `thumbnail_url` vem com 64 px. Use `ads_get_ad_videos` com
   `video_ids` e o campo `picture` (160×284). Não tire o parâmetro de tamanho da URL: ela é
   assinada e deixa de funcionar. Se a imagem ficar pequena, anote em `limitacoes`.
6. Breakdowns, um por chamada, só os que fazem sentido: `age`, `gender`,
   `publisher_platform` + `platform_position`, `region`, `impression_device`.
   Com menos de ~30 resultados no total, não tire conclusão de público: deixe `publico`
   vazio e escreva em limitações "volume pequeno para conclusão sobre público".
7. `ads_account_get_activity_logs` no período → `alteracoes` (só as relevantes, em linguagem
   de cliente: "Orçamento aumentado de R$ 60 para R$ 80 por dia").
   Essa ferramenta ainda está sendo liberada aos poucos pela Meta. Se responder "is being
   gradually rolled out", deixe `alteracoes` vazio e anote em `limitacoes` que o histórico
   não estava disponível para a conta.
8. **Período anterior equivalente** (mesmo tamanho, imediatamente antes; na campanha, a
   campanha anterior de mesmo objetivo, se houver) → só totais, em `anterior`. Uma chamada.

Semanal: agregue a partir da série diária, sem chamada extra.

## Chrome (sem MCP)

Use o navegador só para ler e exportar: escolher conta e período no Gerenciador, exportar a
tabela em CSV (níveis Campanha e, se possível, Anúncio; um com detalhamento por dia), e
converter com `csv_para_json.py`. Se a exportação não for possível, leia a tabela da tela
(`get_page_text`) e monte o JSON à mão, anotando em limitações que os dados foram lidos da
tela. Nunca clique em Publicar, Editar, Ativar ou Desativar.

## Leitura do período (texto do relatório)

Você escreve `leitura` no JSON. Base: só o que está nos dados.

- `resumo`: 2 a 3 frases. O que o período entregou, a que custo, comparado com o anterior.
  Se foi pior, comece por isso.
- `funcionou` / `nao_funcionou`: 1 a 3 itens cada, concretos ("vídeo de 15s no provador:
  menor custo por venda do mês"), nunca genéricos ("bons criativos").
- `proximos_passos`: 1 a 3 itens, cada um ancorado em algo observado. Linguagem de negócio.
  Recomendação técnica detalhada ("subir o lance do conjunto X") fica fora do relatório do
  cliente; se for útil, diga ao gestor no chat.
- Muitos leads e poucas vendas? O gargalo pode estar fora do Meta (atendimento,
  qualificação). Pode dizer isso, com cuidado.
