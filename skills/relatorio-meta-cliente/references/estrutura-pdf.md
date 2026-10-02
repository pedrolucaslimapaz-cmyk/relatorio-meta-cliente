# Estrutura do PDF (A4)

Template: `assets/template-pdf.html`. Formal, para anexar e imprimir. Fundo branco, uma cor
de destaque, a cor da marca só no bloco principal. Gerado por `gerar_pdf.py` (Chromium),
com rodapé "marca · cliente · período" e "página X / Y" em todas as páginas.

Normalmente 2 a 3 páginas. Seções sem dados não aparecem, e o motivo vai para "Sobre estes
dados".

1. **Página 1: capa e resumo**
   - Topo: logo (ou nome da marca) à esquerda; tipo de relatório e foco à direita.
   - Nome do cliente, período por extenso e datas; campanha, se for relatório de campanha.
   - Bloco principal na cor da marca: número grande do foco, frase de apoio, variação contra
     o período anterior.
   - Números principais (3) e outros indicadores (até 6), com variação.
   - CAC de mídia × real, quando houver.
   - Resumo da leitura (2 a 3 frases) com régua na cor de destaque.
2. **Evolução e campanhas** (nova página)
   - Dois gráficos de barras (dia a dia, semana a semana ou mês a mês, conforme
     `serie_granularidade`): resultado do foco e investimento, com o total.
   - Tabela de campanhas: investimento, resultados, custo por resultado, ROAS (se houver),
     barra de participação no investimento.
3. **Criativos e público** (continua o fluxo)
   - Até 3 criativos numa linha, com imagem (ou descrição, se não houver imagem), selo e
     métricas. O dashboard mostra até 6.
   - Barras de idade, gênero, posicionamento, região ou dispositivo (participação no
     resultado).
4. **Leitura, mudanças e limitações** (continua o fluxo)
   - O que funcionou · o que não funcionou · próximos passos.
   - O que mudou nas campanhas (histórico de alterações).
   - Sobre estes dados: aviso de atribuição, limitações, métricas calculadas, "contas da
     Meta".
   - Contato e fonte.

## Conferência

Depois de gerar, o script imprime o número de páginas e avisa se alguma saiu quase vazia.
Se acontecer, o motivo mais comum é um bloco grande quebrando no fim da página: normalmente
some ao reduzir a lista de criativos ou de campanhas no JSON.
