# Estrutura do HTML (dashboard mobile)

Template: `assets/template-dashboard.html`. Pensado primeiro para o celular, porque o
cliente abre pelo WhatsApp. Um único arquivo `index.html`, sem dependências externas (a logo
e as imagens dos criativos vão embutidas), marcado como `noindex`.

De cima para baixo:

1. Logo (em quadro claro ou escuro quando a logo pede) e o tipo de relatório.
2. Nome do cliente, período e datas; campanha, se houver.
3. **Card principal**: número grande do foco, com contagem animada, frase de apoio e
   variação.
4. Números principais em cards (o primeiro ocupa a linha inteira no celular).
5. **Em resumo**: 2 a 3 frases da leitura, logo depois dos números.
6. CAC de mídia × real, quando houver.
7. Outros indicadores, em grade de 2.
8. **Dia a dia**: barras com abas (resultado / investimento). Tocar numa barra mostra o dia.
9. Campanhas em cards, com barra de participação no investimento.
10. Criativos em carrossel horizontal (arrastar para o lado).
11. Quem respondeu: barras por idade, gênero, posicionamento.
12. Leitura: o que funcionou, o que não funcionou, próximos passos.
13. O que mudou nas campanhas.
14. "Sobre estes dados" (recolhido): atribuição, limitações, contas da Meta.
15. Rodapé com marca, contato e fonte.

Animações: entrada suave dos blocos, números que contam, barras que crescem. Tudo desliga
com a preferência de "reduzir movimento" do celular.

Segurança: todo texto vindo dos dados (nomes de campanha, textos de anúncio) é inserido
como texto puro, nunca como HTML.

## Conferência

```bash
python3 <skill>/scripts/gerar_pdf.py <pasta>/dashboard/index.html <pasta>/celular.png --png --pagina-inteira
```

Olhe o PNG (390px de largura): número estourando a largura, card vazio, logo invisível.
