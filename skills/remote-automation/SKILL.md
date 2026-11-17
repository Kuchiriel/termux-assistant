---
name: Automacao remota do celular
description: Comandar o celular Termux de fora (SSH no tailnet, webhook HTTP com token, agendador de jobs, ponte OpenAI-compatible) — os 4 primitivos e como usar
---

Use quando o usuário pedir para "automatizar o celular", mandar comando de fora, disparar coisa no aparelho por HTTP, agendar tarefas, ou ligar um app de chat ao OpenCode local.

## Primitivo 1 — SSH no tailnet (o mais útil)

O Termux tem `sshd`. O celular está no tailnet (`${TA_PHONE_IP:-100.104.175.123}`), então o host NixOS entra direto:

```bash
~/bin/sshd-remote start      # sobe na porta 8022, SÓ no IP de tailnet
~/bin/sshd-remote status
~/bin/sshd-remote pubkey     # chave publica para o host autorizar
```

Travas do `~/.ssh/sshd_config` (gerado pelo script): `PasswordAuthentication no`,
`PermitRootLogin no`, `AllowUsers <user>`, `AllowTcpForwarding no`, `AllowAgentForwarding no`,
`PermitTunnel no`, `MaxAuthTries 3`, bind **só** no IP de tailnet (nunca 0.0.0.0).
A chave do celular (`~/.ssh/celular_remoto_ed25519`) fica **sem passphrase** e só serve para
acesso remoto do próprio aparelho; a pubkey precisa entrar no `authorized_keys` do host.

## Primitivo 2 — Webhook HTTP (gatilho externo)

```bash
~/bin/webhook init      # gera o token em ~/.config/webhook/token (600)
~/bin/webhook start     # 127.0.0.1:8789 (ou OC_WEBHOOK_HOST=100.x para a tailnet)
~/bin/webhook list
curl -X POST http://127.0.0.1:8789/status -H "X-Webhook-Token: $TOKEN"
```

Só executa scripts que já estão em `~/hooks/` (allowlist), exige token, tem rate limit por IP,
timeout por execução e log em `~/.local/state/webhook.log`. **Falha fechada:** sem token, 401.
O app **ntfy** está instalado → a ação do ntfy pode mandar POST aqui e acionar um hook
(ex.: `host-check` publica alerta no ntfy quando o PC NixOS entra em risco de swap).

## Primitivo 3 — Agendador de jobs (Termux:API)

```bash
termux-job-scheduler --period-ms 900000 --script ~/hooks/host-check --job-id 101 --persisted true
termux-job-scheduler --pending
termux-job-scheduler --cancel 101
```

**Mínimo do Android: 900.000 ms (15 min)** — não existe "a cada 5 min".
`--job-id` é **inteiro** e sobrescreve o job anterior; `--persisted true` sobrevive a reboot.

## Primitivo 4 — Ponte OpenAI-compatible (app de chat ↔ OpenCode local)

O `opencode serve` expõe a API nativa (138 rotas) mas **não** tem `/v1/chat/completions`.
A ponte traduz:

```bash
# MEDIDO 12/11: o token precisa PERSISTIR em arquivo, nao ser efemero.
# Antes o start manual usava 'openssl rand -hex 16' a cada vez — com isso a
# ponte morria a cada reboot e o heartbeat so reclamava (92x em ~23 h) sem
# nunca reerguer. O token agora vive em ~/.config/oc-bridge.env (0600, local,
# fora do repo/bus) e o heartbeat reergue a ponte sozinho.
set -a; . ~/.config/oc-bridge.env; set +a
~/bin/oc-bridge &
```

Para gerar o token (uma vez só):

```bash
# sem 'openssl' no Termux: usa o python
umask 077; python3 -c "import secrets;print('OC_BRIDGE_TOKEN='+secrets.token_hex(16))" \
  >> ~/.config/oc-bridge.env
```

`POST /v1/chat/completions` (com `Authorization: Bearer`) → chama `opencode run` e devolve a resposta.
Escuta em 127.0.0.1 por padrão, **não sobe sem token**, e a resposta sai do mesmo agente
(com ferramentas e skills do aparelho). Serve para Chatbox/LobeChat/Enchanted e para o
`termux-assistant` (que usa o mesmo `opencode run`).

> O token é **local e nunca sai do aparelho**: não vai para o repo, nem para o bus,
> nem para o clipboard. Cliente na mesma máquina lê `~/.config/oc-bridge.env`.

## Hardening do Termux (medido)

- `allow-external-apps` **desligado** é o padrão e deve continuar assim: habilita o intent
  `RUN_COMMAND`, que deixa **qualquer app do celular executar comandos no Termux**.
- Os widgets passam pelo Termux:API (`RUN_WIDGET`) e **não** precisam dela.
- O keystore do Android via Termux (`termux-keystore`) só faz **chaves assimétricas**
  (`generate`/`sign`/`verify`) — não serve para guardar senha/segredo.
- Segredos ficam no diretório privado do app (sandbox + FBE), **não** em `~/storage/shared`.
  O backup em `~/storage/shared/backups/` é feito **sem** segredos (por design).
- `termux-clipboard-set` deixa o conteúdo visível ao app em primeiro plano → não copie senha
  para a área de transferência.
