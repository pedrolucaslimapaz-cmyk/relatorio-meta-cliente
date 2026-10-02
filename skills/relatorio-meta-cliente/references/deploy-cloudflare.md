# Publicação do HTML no Cloudflare Pages

Opcional. Sem isso, o HTML sai como arquivo local, pronto para publicar depois.

## Configuração (uma vez)

1. Conta gratuita no Cloudflare (cloudflare.com), no nome do próprio gestor.
2. Node.js 22+ instalado (`checar_ambiente.py` confere). O wrangler atual não roda em versões
   mais antigas.
3. Login, pelo terminal do gestor:
   ```bash
   npx wrangler login
   ```
   O navegador abre, a pessoa autoriza, pronto. Alternativa para quem prefere token:
   exportar `CLOUDFLARE_API_TOKEN` (permissão "Cloudflare Pages: Edit") e
   `CLOUDFLARE_ACCOUNT_ID` no perfil do terminal (`~/.zshrc`). **O token nunca é gravado pela
   skill, nem em config, nem em arquivo de log, nem colado na conversa.** Se a pessoa colar um
   token no chat, avise para gerar outro no painel do Cloudflare, porque aquele ficou exposto.
4. Conferir:
   ```bash
   python3 <skill>/scripts/deploy_cloudflare.py --checar
   ```
5. `config.py set publicacao.cloudflare true`.

## Como os links ficam

- Um projeto por cliente: `https://<projeto>.pages.dev` (o nome do projeto sai de
  `clientes.json → projeto_cloudflare`, que por padrão é o nome do cliente sem acento).
  Se o nome já estiver em uso no Cloudflare, ele acrescenta um sufixo; o script lê o
  domínio real da resposta do deploy.
- Uma pasta por relatório: `https://<projeto>.pages.dev/2026-09-3f9a1c0e7b2d4a65/`. O código
  no fim tem 16 caracteres aleatórios, para ninguém adivinhar o link de outro mês trocando a
  data. Os relatórios têm dados comerciais do cliente; não desligue o código (`--sem-codigo`)
  sem o gestor pedir.
- Só o `index.html` do dashboard sobe. O script recusa qualquer arquivo que não seja
  `<pasta>/dashboard/index.html`, para nada da pasta do relatório (JSON, mensagem, PDF) virar
  público por engano.
- Cada deploy substitui o site inteiro. Por isso o script mantém em
  `~/.relatorio-meta-cliente/publicar/<projeto>/` todos os relatórios já publicados daquele
  cliente e envia a pasta inteira: os links antigos continuam funcionando. Não apague essa
  pasta.
- A raiz do projeto mostra só "use o link completo do relatório" e o site vai com
  `noindex` (não aparece no Google).

## Publicar

```bash
python3 <skill>/scripts/deploy_cloudflare.py \
  --dashboard <pasta>/dashboard/index.html --projeto <projeto_cloudflare> --pasta 2026-09
```

Saída JSON com `"ok": true` e a `url`. O script só devolve `ok` depois de abrir o link e
receber resposta 200. Depois, gere a mensagem de novo com `--link <url>`.

## Tirar um relatório do ar

Só com o "sim" do gestor. A pasta é o nome completo, com o código (está no fim do link e em
`~/.relatorio-meta-cliente/publicar/<projeto>/`):

```bash
python3 <skill>/scripts/deploy_cloudflare.py --despublicar --projeto <projeto_cloudflare> --pasta 2026-09-3f9a1c0e7b2d4a65
```

O script apaga a cópia local e publica de novo sem ela: o link para de abrir em 1 ou 2
minutos. Os outros relatórios do cliente continuam no ar.

## Quando dá errado

| Código | O que aconteceu | O que fazer |
|---|---|---|
| 5 | Não está logado no Cloudflare, falta o Node ou o Node é antigo | Repassar a mensagem do script: `npx wrangler login`, ou instalar o Node.js 22+ (nodejs.org). Enquanto isso, entregar o HTML como arquivo. |
| 6 | O deploy falhou | Mostrar o motivo resumido (o script esconde qualquer coisa com cara de token). Entregar o HTML como arquivo. |
| 7 | Deploy feito, mas o link não respondeu | Pode ser a primeira publicação do projeto propagando. Esperar 1 a 2 minutos e testar o link antes de enviar. Não mandar o link ao cliente sem conferir. |

Em qualquer falha: a mensagem para o cliente sai na versão "em anexo", sem link. **Nunca
escreva um link que o script não devolveu**, nem "deve ficar em https://...".
