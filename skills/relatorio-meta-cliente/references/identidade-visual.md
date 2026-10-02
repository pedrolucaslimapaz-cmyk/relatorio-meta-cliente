# Modo B — Identidade visual

Tudo fica em `~/.relatorio-meta-cliente/identidades/<slug>/`: `identidade.json`, a logo e
`paletas.json` (as opções geradas). Atualizar a skill não mexe nessa pasta.

## Passo a passo

1. **Logo.** Peça o caminho (ou para arrastar o arquivo para a conversa). PNG com fundo
   transparente funciona melhor; JPG, SVG e WEBP também. Peça também o nome da marca como
   deve aparecer no relatório.
   ```bash
   python3 <skill>/scripts/config.py identidade-nova --nome "Marca do Gestor" --logo "<caminho>"
   ```
   Saída com o `slug`. Logo com fundo branco chapado (JPG): funciona, mas avise que no
   dashboard escuro ela vai aparecer num quadro claro.
2. **Cores.**
   ```bash
   python3 <skill>/scripts/paleta_logo.py --identidade <slug>
   ```
   Mostra as cores encontradas na logo e 3 paletas:
   - **Marca em destaque**: cor mais forte da logo no bloco principal e nos gráficos.
   - **Sóbrio**: base quase preta, a cor da logo só nos números e gráficos.
   - **Duas cores da logo** (ou **Claro nos dois formatos**, se a logo tiver uma cor só).
   Logo monocromática (preto, branco, cinza): o script sugere cores de destaque neutras e
   diz isso na descrição. Deixe claro para o gestor que é sugestão.
   Mostre uma tabela com nome, descrição e os códigos, e pergunte
   [Paleta 1] [Paleta 2] [Paleta 3] [Quero informar os códigos]. Depois:
   ```bash
   python3 <skill>/scripts/paleta_logo.py --identidade <slug> --aplicar 2
   python3 <skill>/scripts/paleta_logo.py --identidade <slug> --hex "#0A2540,#FF7A00" --aplicar hex
   ```
   Com `--hex`, a primeira cor é a da marca (bloco principal) e a segunda o destaque.
   O script ajusta o tom quando falta contraste (texto sempre legível, destaque visível nos
   dois fundos), então a cor final pode sair um pouco mais clara ou escura que a informada:
   se isso acontecer, avise.
3. **Nome, contato, rodapé.** Puxe o que já souber (nome no git, e-mail, CLAUDE.md) e mostre
   um checklist: marca, responsável, WhatsApp, e-mail, Instagram, site, rodapé. Pergunte
   [Está certo] [Quero mudar algo]. Grave cada campo:
   ```bash
   python3 <skill>/scripts/config.py identidade-set <slug> responsavel "Nome Sobrenome"
   python3 <skill>/scripts/config.py identidade-set <slug> contato.whatsapp "(11) 90000-0000"
   python3 <skill>/scripts/config.py identidade-set <slug> rodape "Gestão de tráfego pago"
   ```
   Campo vazio não aparece no relatório.
4. **Prévia nos dois formatos** (PDF A4 e dashboard no celular) com os dados de exemplo (a
   faixa "Prévia com dados de exemplo" aparece sozinha):
   ```bash
   P=~/.relatorio-meta-cliente/previa/<slug>
   python3 <skill>/scripts/montar_relatorio.py <skill>/assets/exemplo-relatorio.json --identidade <slug> --saida $P
   python3 <skill>/scripts/gerar_pdf.py $P/relatorio-pdf.html $P/previa.pdf
   python3 <skill>/scripts/gerar_pdf.py $P/dashboard/index.html $P/previa-celular.png --png --pagina-inteira
   ```
   Veja você mesmo o PNG e o PDF antes de mostrar (logo apagada, cor sem contraste, texto
   cortado). Depois abra os dois para o gestor e pergunte [Aprovar] [Ajustar cores]
   [Ajustar layout].
5. **Ajustes.**
   - Cores: volte ao passo 2 com outra paleta ou `--hex`.
   - Layout: pergunte o que incomodou, com opções concretas, por exemplo
     [Dashboard claro em vez de escuro] [Logo maior] [Outra fonte] [Outro ajuste].
     Tema do dashboard: `identidade-set <slug> html.tema claro|escuro`.
     Fonte do Google Fonts: `identidade-set <slug> fonte_google "Montserrat"` (no PDF só
     funciona com internet; sem internet, cai na fonte do sistema).
     Logo precisando de fundo: `identidade-set <slug> logo_fundo claro|escuro|auto`.
   - Ajuste estrutural (tirar uma seção, mudar a ordem): não edite os templates. Eles ficam
     na pasta da skill e seriam sobrescritos na próxima atualização. Diga que a estrutura é
     fixa nesta versão e sugira abrir uma issue em
     https://github.com/pedrolucaslimapaz-cmyk/relatorio-meta-cliente/issues.
6. Ao aprovar: `config.py identidade-set <slug> aprovada true`.

## Várias identidades

Gestor que atende com duas marcas: repita o Modo B com outro nome. Cada cliente pode ter a
sua (`config.py cliente --conta <id> --nome "..." --identidade <slug>`). Se houver mais de
uma e o cliente não tiver identidade ligada, o Modo C pergunta qual usar.

## Princípios dos templates

- Resultado em primeiro plano: o número que importa para o dono do negócio é o maior da
  página.
- Neutros com uma cor de destaque. Funciona com qualquer logo.
- Nada de ícones decorativos, gradientes chamativos ou "cara de IA".
- Verde e vermelho só para variação (melhorou / piorou), nunca como decoração.
