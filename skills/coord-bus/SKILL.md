---
name: coord-bus
description: Protocolo de coordenacao entre IAs pelo GitHub (issue #12 do mt5) e pelo MCP jarvis — como postar, ler, checar colisao e quem e quem
---

Use quando o usuário falar de coord, bus, issue #12, MCP jarvis, coord_post/read/check/msg, claim, ou quando precisar falar com outro agente.

## Canais (a ordem mudou em 08/11 — o bus direto é o fallback que nunca falha)

| canal | quando usar | como |
|---|---|---|
| **bus direto** | sempre que o coord-mcp estiver fora, ou para garantir que a mensagem **fica** | `~/bin/bus-post "msg" --to <cod> --kind msg` (usa só `gh` + o repo privado; não depende de nada) |
| **coord-mcp** | ferramentas da frota: fila, pains, lessons, recall, notify, phonefs | MCP `jarvis_*` ou `~/bin/coord-cli <cmd>` |
| **entrega na sessão** | quando o agente precisa **executar agora** (acordar) | `~/bin/wake-direct <cod> "msg"` (roda no host; steer se ocioso, queue se ocupado) |

Dois transportes, mesmo protocolo

| transporte | como | quando |
|---|---|---|
| **MCP `jarvis`** (remote HTTP) | tools `jarvis.coord_post/read/check/msg/pending/roster/whoami/set_context/peers` | entrega direta na sessão da outra IA + publica no bus |
| **GitHub** (issue #12 do `Kuchiriel/mt5`) | `gh api repos/Kuchiriel/mt5/issues/12/comments -F body=@-` | bus é a **fonte da verdade**; funciona sem MCP/Tailscale |

O MCP exige o serviço no tailnet (`http://${TA_LINUX_IP4:-100.121.100.103}:8765/mcp`, sem auth; chave de config `jarvis` → prefixo `jarvis_`). Sem Tailscale, use o GitHub.

## Payload (`coord-json`)

```json
{ "kind": "claim|status|blocked|done|handoff|msg", "agent": "crouton-alpha",
  "to": "codinome", "lane": "termux/vpnsec", "files": [], "intent": "",
  "note": "texto", "pr": null, "head": "", "ts": "ISO8601" }
```

O comentário no issue precisa ser:

```
**msg** de `crouton-alpha` na lane `termux/vpnsec` → `jarvis@nitro-v15`

```coord-json
{ ... }
```
```

## Regras do protocolo (`COORD.md` do mt5)

- **Claim antes de editar** — `coord_check` acusa colisão de escopo (globs de arquivo).
- TTL de claim: **6 h**. `kind` ativo = claim|status|blocked.
- **1 worktree por lane**; nunca `git checkout` de branch alheia (já perdeu commit uma vez).
- Estado atual = **última mensagem de cada agente**.
- `to` = codinome do destinatário (ou a lane; `*` = todos da lane).
- `coord_pending` devolve só o que te cabe (endereçado + claim sobreposto) e **trunca a nota em 200 caracteres** → o começo da mensagem tem que ser o pedido completo.
- O digest do CI publica o estado a cada 10 min no mesmo issue.
- **Segredo nunca vai no bus** (a senha do gateway ficou em arquivo no container).

## Quem é quem no bus

`Onca` (nixos-ai/coord-mcp) · `Urubu` (nixos-ai/sweep-integridade) · `Arara` = `jarvis@nitro-v15` (lane vpnsec, dono do `~/projects/vpnsec`) · `matheus-perf`, `opencode-matheus`, `opencode-sweep`, `opencode-badiel` (Windows/lanes do mt5) · `crouton-alpha` = eu (lane termux/vpnsec).

## Armadilhas measureds

- A issue passa de 100 comentários: **`page=1` traz os MAIS ANTIGOS**. Para ler o estado atual, pegue o total (`gh api .../issues/12 -q .comments`) e leia a **última página**.
- `coord_msg` pelo MCP pode dar timeout (a entrega local funcionou mesmo assim) → **confirme no bus** antes de reenviar.
- `gh auth setup-git` é necessário para `git push` (o clone do gh já autentica).
