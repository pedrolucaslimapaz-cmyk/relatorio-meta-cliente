# Métricas por foco e mensagem para o cliente

O foco escolhido no passo 4 muda o número grande do topo, os três números principais, a
ordem dos indicadores, a série do gráfico e a mensagem. O `montar_relatorio.py` já aplica
isso; esta página explica o porquê para você conseguir conversar com o gestor sobre a escolha.

| Foco | Número grande | Principais | Exige nos dados |
|---|---|---|---|
| Vendas e ROAS | Faturamento atribuído (com ROAS na linha de apoio); sem valor de compra, nº de vendas | Investimento · Vendas · Custo por venda | `compras` |
| Leads e CPL | Leads (com CPL no apoio) | Investimento · Leads · Custo por lead | `leads` |
| CAC | CAC real (se informado) ou CAC de mídia | Investimento · Vendas · CAC de mídia | `compras` |
| Alcance e engajamento | Alcance em contas da Meta (com frequência no apoio) | Investimento · Alcance · CPM | `alcance` |

## Regras por foco

**Vendas e ROAS.** Compras, valor de compras, ROAS, custo por compra. ROAS só aparece se houver
valor de compra confiável (> 0). Com compras mas sem valor, o relatório mostra vendas e custo
por venda, e a limitação "ROAS não exibido" é incluída automaticamente.

**Leads e CPL.** Leads, custo por lead e, quando houver, taxa de conversão da página
(leads ÷ visualizações da página de destino × 100, só se as duas vierem do Meta).

**CAC.** O script calcula "CAC de mídia (vendas atribuídas pelo Meta)" = investimento ÷
compras atribuídas. Pergunte se o gestor tem o número real de vendas do cliente no período
(vindo do caixa, CRM, loja). Se tiver, grave em `totais.vendas_reais`: o relatório mostra os
dois lado a lado e a limitação explica que o CAC de mídia não inclui outros custos.
O CAC real costuma ser maior ou menor que o de mídia: nenhum dos dois está "errado", medem
coisas diferentes. Explique isso em uma frase na leitura.

**Alcance e engajamento.** Alcance (sempre "contas da Meta", nunca "pessoas"), frequência,
CPM, ThruPlays e engajamentos.

## Foco sem dados

Se o foco pedido não tem a métrica que exige (ex.: vendas numa campanha de mensagens, sem
pixel de compra), o `--so-validar` sai com código 4 e sugere o foco que os dados sustentam.
Avise **antes** de gerar e deixe o gestor escolher. Nunca preencha a métrica que falta.

## Classificação do desempenho

Você propõe, o gestor confirma na conferência. Sem meta formal, compare com o período
anterior:
- **abaixo**: o custo do resultado principal piorou mais de ~15% ou o volume caiu mais de
  ~15% sem queda proporcional de investimento, ou o gestor diz que ficou abaixo.
- **acima**: melhora clara nos dois (custo e volume) ou meta do cliente batida.
- **dentro**: o resto, ou quando não há período anterior para comparar.
Se o gestor tiver uma meta do cliente, use a meta, e cite-a na leitura.

## Mensagem para o cliente

O script gera `mensagem.txt` seguindo este modelo (ênfase no resultado financeiro e de
conversão):

```
Olá, [nome do cliente]!

Segue o relatório da nossa última campanha ([nome da campanha]).    ← ou "das campanhas de agosto de 2026."

💰 Investimento: R$ [valor]
🎯 Resultado: [quantidade] [vendas/leads]
📉 Custo por resultado: R$ [valor]
[linha da métrica de destaque] 🚀

Acesse o relatório completo: [link]
```

- Linha de destaque: vendas → "ROAS de 4,38x: R$ 12.664,72 em vendas atribuídas"; leads →
  conversão da página (se houver); CAC → CAC de mídia e real; alcance → ThruPlays ou
  engajamentos. Sem dado para a linha, ela some (nunca inventada).
- Só PDF: a última linha vira "Relatório completo em anexo." Os dois: link + "O PDF também
  vai em anexo."
- **Abaixo do esperado** (`"desempenho": "abaixo"`): sem 🚀, sem tom de comemoração, e entra
  a linha "No relatório mostramos o que funcionou, o que não funcionou e o que vamos ajustar
  na próxima."
- Use `contato_cliente` quando o gestor souber o primeiro nome de quem recebe.
- Entregue a mensagem num bloco de código para copiar. Se o gestor pedir ajuste de tom,
  edite o texto, mas nunca mude os números.
- O link só entra se o deploy devolveu `ok: true`. Sem link real, a mensagem sai na versão
  "em anexo" e você explica por quê.
