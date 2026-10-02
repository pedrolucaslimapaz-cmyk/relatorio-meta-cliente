# Relatório Meta Ads para Clientes

Plugin do Claude Code para gestores de tráfego. Você conecta suas contas de anúncio uma vez,
configura sua marca uma vez, e depois gera o relatório de qualquer cliente em poucos cliques:

- **PDF** formal, para anexar;
- **página no celular** (dashboard) com link, para mandar no WhatsApp;
- **mensagem pronta** para copiar e colar no WhatsApp.

Tudo com a sua logo e as suas cores. O plugin foi feito para **só ler** os dados do Meta:
ele nunca cria, edita, pausa ou ativa campanhas (veja "Segurança recomendada").

Versão atual: 1.2.0 (veja o que mudou em `CHANGELOG.md`). Código aberto, licença MIT.
Testado no macOS. No Windows deve funcionar (use `python` no lugar de `python3`), mas ainda
não foi testado.

---

## O que você precisa

| Item | Obrigatório? | Para quê |
|---|---|---|
| Claude Code (plano Pro, Max, Team ou Enterprise) | Sim | Rodar o plugin |
| Python 3.9 ou mais novo | Sim | Montar os relatórios |
| Playwright + Chromium | Para o PDF | Transformar o relatório em PDF |
| Acesso às contas de anúncio dos clientes (na BM) | Sim | Ler os dados |
| Node.js 22+ e conta gratuita no Cloudflare | Só para o link | Publicar a página do relatório |

Não sabe se tem? Não tem problema: na primeira execução o plugin confere tudo e mostra o
comando para instalar o que faltar.

## Instalação

No Claude Code, rode os dois comandos abaixo:

```
/plugin marketplace add pedrolucaslimapaz-cmyk/relatorio-meta-cliente
/plugin install relatorio-meta-cliente@relatorio-meta-cliente
```

Depois, feche e abra o Claude Code de novo.

Prefere baixar a pasta (botão **Code → Download ZIP** no GitHub)? Descompacte e rode, no
terminal (dica: arraste a pasta para o terminal para preencher o caminho):

```
claude plugin marketplace add /caminho/da/pasta/relatorio-meta-cliente-main
claude plugin install relatorio-meta-cliente@relatorio-meta-cliente
```

### Atualizar

No terminal, rode os dois comandos e depois feche e abra o Claude Code:

```
claude plugin marketplace update relatorio-meta-cliente
claude plugin update relatorio-meta-cliente@relatorio-meta-cliente
```

Quem instalou pelo ZIP: baixe o ZIP novo, descompacte por cima da mesma pasta e rode os dois
comandos.

## Primeira execução

Abra o Claude Code em qualquer pasta e escreva:

> quero configurar o relatório de Meta Ads

O plugin vai te levar, uma etapa por vez, com perguntas de clicar:

1. **Checagem do computador**: instala (com sua autorização) o que faltar.
2. **Conexão com o Meta**: o jeito recomendado é o conector oficial do Meta Ads. Você roda um
   comando, entra com seu Facebook no navegador e pronto. Sem ele, dá para usar o Chrome ou
   um arquivo CSV exportado do Gerenciador.
3. **Conferência das contas**: ele lista todas as contas encontradas para você confirmar.
4. **Link do relatório (opcional)**: conecta o seu Cloudflare para publicar os relatórios.
5. **Sua marca**: você manda a logo, escolhe uma de três paletas de cores (ou informa seus
   códigos), confere nome e contato e aprova uma prévia do PDF e da página no celular.

Leva uns 15 minutos. Só se faz uma vez.

## Uso no dia a dia

> faz o relatório mensal do [cliente]

Ele pergunta, sempre com opções para clicar: conta, período, métrica de destaque (vendas e
ROAS, leads e CPL, CAC ou alcance), mostra os números para você conferir, pergunta o formato
e entrega o PDF, o link e a mensagem.

Outros exemplos:
- "relatório da campanha de Dia dos Pais da Loja X, foco em ROAS, só PDF"
- "relatório semanal do Studio Y"
- "tenho esse CSV exportado do Gerenciador, faz o relatório" (e arraste o arquivo)
- "quero trocar as cores do relatório" / "cadastra uma segunda marca"

## Onde ficam seus dados

Os arquivos ficam **no seu computador**, em `~/.relatorio-meta-cliente/`:

- `config.json`, `clientes.json` e `controle.json`: sua configuração, seus clientes e o
  histórico de relatórios emitidos;
- `identidades/`: suas logos e cores;
- `relatorios/`: os arquivos gerados;
- `publicar/`: os relatórios já publicados (não apague, senão links antigos param).

Atualizar o plugin não apaga nada disso.

O que sai do computador:
- os dados lidos do Meta passam pela sua conversa com o Claude, como em qualquer uso do
  Claude Code;
- quando você escolhe o formato com link, o relatório vai para o **seu** Cloudflare;
- se você escolher uma fonte do Google Fonts para a sua marca, a página do cliente carrega
  essa fonte do Google.

Senhas e tokens nunca são gravados pelo plugin.

## Segurança recomendada

O conector oficial do Meta também tem ferramentas que criam, editam, apagam e ativam
campanhas, públicos e criativos. O plugin nunca usa essas ferramentas, mas o bloqueio
automático do Claude Code vale só na primeira mensagem do relatório. Para um bloqueio
permanente, aceite a sugestão da configuração (uma lista `permissions.deny` no seu
`~/.claude/settings.json`). Ela bloqueia só as ferramentas que alteram algo; as de leitura
continuam funcionando. Vale para o Claude Code inteiro: com ela ativa, nenhuma conversa cria
ou altera nada no Meta.

Os links publicados levam um código aleatório de 16 caracteres no final e não aparecem no
Google, mas quem tiver o link consegue abrir. Mande só para o cliente. Para tirar um
relatório do ar, peça: "tira do ar o relatório de setembro do cliente X".

## Problemas comuns

| O que aparece | O que fazer |
|---|---|
| "Não consegui abrir o Chromium" | Rode `python3 -m playwright install chromium` no terminal. |
| Conta com `is_ads_mcp_enabled: false` | A Meta ainda não liberou o conector para essa conta. Use CSV para ela por enquanto. |
| "Você ainda não está conectado ao Cloudflare" | Rode `npx wrangler login` no terminal e autorize no navegador. |
| "Seu Node.js é antigo" | Instale a versão LTS (22 ou mais nova) em https://nodejs.org. |
| "O foco precisa de vendas, que não veio nos dados" | A campanha não mede compras (sem pixel ou evento de compra). Escolha o foco sugerido. |
| O link não abre logo depois de publicar | Na primeira vez pode levar 1 ou 2 minutos. O plugin só entrega o link depois de testar. |

## Suporte e contribuições

Achou um problema ou tem uma ideia? Abra uma *issue* em
https://github.com/pedrolucaslimapaz-cmyk/relatorio-meta-cliente/issues.

Para rodar os testes automáticos (não mexem na sua configuração; usam uma pasta temporária;
precisam do Playwright e do Chromium instalados):

```
python3 tests/testar.py
```

## Licença

MIT. Pode usar, adaptar e redistribuir, mantendo o aviso de licença (veja `LICENSE`).
