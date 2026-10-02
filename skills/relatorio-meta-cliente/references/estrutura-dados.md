# relatorio.json — formato de entrada do montar_relatorio.py

Um arquivo por relatório. Valores monetários em unidades normais da moeda (não centavos).
Percentuais como número de 0 a 100 (`1.8` = 1,8%). Datas `AAAA-MM-DD`.
**Campo sem dado = omitir** (ou `null`). Zero só quando o Meta disse zero: o script trata
`null` como "não medido" e `0` como "medido, deu zero", e isso muda a validação do foco.

Exemplo completo: `assets/exemplo-relatorio.json`.

```jsonc
{
  "schema": 1,
  "fonte": "meta_mcp",                 // meta_mcp | chrome | csv
  "cliente": "Loja Exemplo",           // nome que aparece no relatório
  "contato_cliente": "Ana",            // opcional: nome usado no "Olá, ...!" da mensagem
  "conta": {"id": "act_123", "nome": "Loja Exemplo - BM"},
  "periodo": {
    "tipo": "mensal",                  // mensal | semanal | campanha | personalizado
    "inicio": "2026-08-01",
    "fim": "2026-08-31",
    "rotulo": "Agosto de 2026",        // opcional; sem ele, vira "1 a 31 de agosto de 2026"
    "campanha": null                   // nome limpo da campanha, quando tipo = campanha
  },
  "foco": "vendas",                    // vendas | leads | cac | alcance
  "moeda": "BRL",
  "desempenho": "dentro",              // acima | dentro | abaixo  (abaixo muda o tom da mensagem)

  "totais": {
    "investimento": 2890.09,           // obrigatório
    "impressoes": 184320, "alcance": 61240, "frequencia": 3.01,
    "cliques_link": 3105, "ctr": 1.68, "cpc": 0.93, "cpm": 15.68,
    "resultados": 77, "rotulo_resultado": "compras no site", "custo_por_resultado": 37.53,
    "compras": 77, "valor_compras": 12664.72, "roas": 4.38,
    "leads": null, "taxa_conversao_pagina": null,
    "thruplays": 12880, "engajamentos": null,
    "vendas_reais": null,              // só no foco CAC, se o gestor informar
    "rotulo_leads": null               // foco leads: nome do resultado, ex.
                                       // {"plural": "conversas no WhatsApp", "singular": "conversa"}
                                       // para campanhas de mensagem (sem ele, fica "leads")
  },
  "anterior": {                        // opcional: mesmo formato de totais + rotulo
    "rotulo": "julho", "investimento": 2890.4, "compras": 61, "valor_compras": 9310.2
  },
  "serie_diaria": [
    {"data": "2026-08-01", "investimento": 95.2, "compras": 3, "leads": null, "resultados": 3}
  ],
  "serie_granularidade": "dia",        // dia | semana | mes. Acima de ~60 dias, use semana (data = segunda-feira
                                       // da semana) ou mes (data = dia 1): barra diária fica fina demais.
  "campanhas": [
    {"nome": "Vendas | Coleção Inverno", "investimento": 1791.86, "compras": 51, "valor_compras": 8612.0}
  ],
  "criativos": [
    {"nome": "Vídeo provador 15s", "selo": "Melhor custo por venda",
     "descricao": "Vídeo vertical com três looks no provador.",
     "imagem": "criativo-1.jpg",       // arquivo PNG/JPG/WebP/GIF na pasta do JSON, ou data URI de imagem;
                                       // nunca URL remota (o script ignora o resto e avisa)
     "investimento": 820.5, "compras": 31, "ctr": 2.1}
  ],
  "publico": {
    "metrica": "Vendas",               // o que os valores medem
    "idade": [{"rotulo": "25-34", "valor": 31}],
    "genero": [], "posicionamento": [], "regiao": [], "dispositivo": []
  },
  "alteracoes": [{"data": "2026-08-10", "descricao": "Orçamento aumentado de R$ 60 para R$ 80 por dia."}],
  "leitura": {
    "resumo": "…",
    "funcionou": ["…"], "nao_funcionou": ["…"], "proximos_passos": ["…"]
  },
  "limitacoes": ["Sem dados de público: volume pequeno para conclusão."],
  "aviso_atribuicao": null             // null = aviso padrão; "" = sem aviso (período bem antigo)
}
```

## O que o script calcula sozinho (e marca como calculado)

frequência (impressões ÷ alcance), CTR, CPC, CPM, custo por resultado, custo por venda, CPL,
custo por ThruPlay, CAC de mídia (investimento ÷ compras), CAC real (investimento ÷
vendas_reais), ROAS (valor de compras ÷ investimento) ou valor de compras (ROAS ×
investimento). Não calcule você: deixe o script fazer, para ficar consistente e registrado.

## Nomes

- `campanhas[].nome` e `periodo.campanha`: limpe códigos internos ("[CBO][BR] VD_01 - Inverno"
  → "Vendas | Inverno") se o gestor concordar na conferência.
- `conta.id` serve só para controle e não aparece no relatório. Não coloque tokens nem
  dados pessoais dos compradores do cliente no JSON.
