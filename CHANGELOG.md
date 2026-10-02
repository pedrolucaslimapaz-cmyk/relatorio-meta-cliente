# Changelog

Formato: versão · data · o que mudou para quem usa.

## 1.2.0 · 2026-10-02

Primeira versão pública.

- Segurança: a lista de ferramentas de escrita do Meta bloqueadas pela skill passou a cobrir
  todas (criativos, pixels, catálogos, imagens), e a sugestão de bloqueio permanente usa
  padrões que valem para qualquer nome de conector. A documentação agora explica que o
  bloqueio automático vale só no primeiro turno.
- Publicação: só o `index.html` do dashboard sobe para o Cloudflare (antes, arquivos ao lado
  dele podiam ir junto). Código do link com 16 caracteres. Novo `--despublicar` para tirar um
  relatório do ar.
- Imagens de criativo: só PNG, JPG, WebP ou GIF de dentro da pasta do relatório entram na página.
- Conversor de CSV: entende ponto de milhar ("34.567"), datas DD/MM/AAAA e traduz os códigos do
  Meta no tipo de resultado ("profile_visit_view" → "visitas ao perfil").
- `montar_relatorio.py` recusa datas fora do formato AAAA-MM-DD já na validação, com mensagem
  em português.
- Checagem do computador: exige Node.js 22+ (o wrangler atual não roda em versões antigas),
  indica o instalador do nodejs.org quando o Mac não tem Homebrew, confere o openpyxl e dá
  mensagens claras quando falta o Chromium.
- Windows: os scripts não quebram mais com acentos e emoji na saída e acham o `npx`.
- Conector do Meta adicionado com `--scope user` (vale em qualquer pasta).

## 1.1.0 · 2026-09-29

- Relatórios de período longo: campo `serie_granularidade` (dia, semana ou mês). O gráfico passa a
  se chamar "Evolução semana a semana" / "mês a mês" no PDF e no dashboard.
- Conversor de CSV acompanha o export atual do Gerenciador em pt-BR: lê "Encerramento dos
  relatórios" (data final), "Indicador de resultados" e "Valor de conversão da compra" (antes
  saía sem faturamento e sem ROAS).
- Foco "Leads e CPL" aceita nome próprio para o resultado (`totais.rotulo_leads`), para campanhas de
  mensagem: o relatório e a mensagem dizem "conversas no WhatsApp" e "custo por conversa", não "lead".
- Conversor não soma mais alcance entre campanhas (mostrava um número inflado) nem resultados de
  tipos diferentes; o aviso ao cliente sai em português simples, sem códigos do Meta.

## 1.0.1 · 2026-09-26

Correções do primeiro teste com conta real (MCP oficial do Meta Ads).

- Guia de coleta com os nomes de campo que o MCP aceita de verdade (`link_click`,
  `website_ctr`, `omni_purchase`, `omni_purchase_values`…); os antigos (`inline_link_clicks`,
  `actions`…) voltavam como desconhecidos.
- Guia de coleta: como lidar com ordenação e filtro de anúncios que o MCP ignora, contas que
  duplicam campanhas toda semana, miniatura de vídeo pequena e histórico de alterações ainda
  não liberado.
- Tabela de campanhas e cards de criativos não misturam mais resultados de outro tipo
  (visitas, alcance) na coluna de vendas ou leads: aparece "—".
- PDF mostra no máximo 3 criativos (uma linha), evitando uma página quase vazia no fim.
  O dashboard continua com até 6.
- `gerar_pdf.py --png` no HTML do PDF agora captura na largura A4 com mídia de impressão,
  igual ao PDF (antes parecia quebrado).

## 1.0.0 · 2026-09-25

Primeira versão.

- Três modos: conexão (MCP oficial do Meta Ads, Claude in Chrome ou CSV), identidade visual
  (logo, 3 paletas geradas a partir da logo ou cores informadas, várias marcas) e geração do
  relatório.
- Quatro focos: Vendas e ROAS, Leads e CPL, CAC (de mídia e real) e Alcance e engajamento.
  Aviso antes de gerar quando o foco escolhido não tem dados.
- PDF A4 formal e dashboard HTML para celular, com animações, gráfico dia a dia, campanhas,
  criativos, público, leitura do período e limitações.
- Publicação opcional no Cloudflare Pages da conta do gestor: um projeto por cliente, uma
  pasta por relatório, links antigos preservados, código aleatório no link e `noindex`.
- Mensagem para WhatsApp pronta para copiar, com tom ajustado quando o resultado fica abaixo
  do esperado.
- Conversor de CSV/XLSX do Gerenciador de Anúncios (cabeçalhos em português ou inglês).
- Configuração do usuário fora da pasta do plugin (`~/.relatorio-meta-cliente/`), preservada
  em atualizações. Credenciais nunca são gravadas.
- Principais ferramentas de escrita do MCP do Meta bloqueadas no turno em que a skill começa.
