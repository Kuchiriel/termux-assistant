---
name: ai-mesh (hub da frota)
description: Repo privado ai-mesh como fonte unica da malha de IAs — manifesto de capacidades por host, skills compartilhadas, memoria episodica e o protocolo do heartbeat
---

Use quando o usuário falar em "malha", "fleet", "todos os agentes", "compartilhar skills",
"memória", "RAG", "heartbeat", "repo da malha", ou para descobrir o que outro host tem/precisa.

## O hub

`https://github.com/Kuchiriel/ai-mesh` (privado). Clone no Termux: `~/ai-mesh`.

```
manifests/<host>.json  capacidade declarada (skills, MCPs, plugins, scripts, widgets, servicos, precisa_dos_outros, oferece)
skills/                skills compartilhadas, instaláveis em qualquer host
memory/episodic/*.jsonl memória episódica append-only (um arquivo por host)
docs/                  memoria-rag.md (desenho em camadas + fontes), heartbeat.md (protocolo)
scripts/               install-skills.sh · publish-manifest.sh · heartbeat.sh
AGENTS.md              contrato comum da frota
```

## Comandos (Termux)

```bash
~/bin/mesh-repo pull      # git pull + instala as skills compartilhadas
~/bin/mesh-repo publish   # gera meu manifesto e abre PR
~/bin/mesh-repo status    # estado do clone
~/bin/mesh-manifest       # imprime meu manifesto (JSON)
```

Jobs: 111 (pull 30 min) · 110 (heartbeat 15 min) · 106 (mesh-apply 15 min).

## Os 3 canais (não confundir)

| canal | papel | latência |
|---|---|---|
| **bus** (issue #12 do `Kuchiriel/mt5`) | mensagens `coord-json`; `coord_msg` acorda a sessão do peer | tempo real |
| **repo ai-mesh** | estado durável: capacidades, skills, memória | horas |
| **coord-mcp** (`${TA_LINUX_IP4:-100.121.100.103}:8765/mcp`) | hub com 9 tools, de qualquer host do tailnet | tempo real |

## Manifesto de capacidade (JSON)

```json
{"host":"termux","so":"android","tailnet_ip":"${TA_PHONE_IP:-100.104.175.123}",
 "mcp":{"jarvis":{"type":"remote","url":"http://${TA_LINUX_IP4:-100.121.100.103}:8765/mcp","auth":"none (tailnet only)"}},
 "skills":[...],"plugins":[],"scripts":[...],"widgets":[...],
 "servicos":[{"nome":"sshd","porta":8022,"auth":"key-only"}],
 "precisa_dos_outros":[...],"oferece":[...]}
```

Antes de pedir "alguém sabe fazer X?" ou instalar qualquer coisa: **consulte o manifesto**.

## Memória episódica

`memory/episodic/<host>.jsonl`, append-only:
`{"ts":"...","host":"termux","kind":"fact|decision|failure|path|gotcha","tags":["vpn"],"text":"...","refs":[...]}`

Guarde **failure/gotcha/decision/path** — o que mais economiza tempo é o que **não** funcionou.
Não: dump de sessão, segredo, ou o que já está no AGENTS.md.

Consulta sem banco:
```bash
grep -h '"kind":"failure"' ~/ai-mesh/memory/episodic/*.jsonl | jq -r '.host+": "+.text'
```

## Heartbeat

Job de 15 min (`~/bin/heartbeat`): confere o coord-mcp, acorda quem está **online e silencioso há >20 min**
(`coord_msg` curto), com anti-spam de 1 wake por agente a cada 30 min, e reergue serviços locais caídos.

**Contrato de resposta: 1 linha** — o que está em andamento / o que está bloqueado / se precisa de ação do dono.

Intervenção humana só quando: coord-mcp do Linux cair, o agente pedir algo manual, disco <400 MB,
ou a conta do gateway estiver bloqueada.

## Plugin de memória (instalado no celular)

`~/.config/opencode/plugins/memory-termux.js` injeta no system prompt: identidade real
(model/provider/variante/sessionID/host), o estado da frota (`~/bin/ta-state`, cache 10 min) e
as regras fixas; re-injeta após compactação; bloqueia `rm -rf /` sem caminho ancorado.
A/B: `OPENCODE_NO_IDENTITY_INJECT=1` · `OPENCODE_NO_STATE_INJECT=1` · `OPENCODE_NO_REHYDRATE_INJECT=1`.
Doc: `docs/plugin-memoria-termux.md`. O `shared/` do repo traz o lado Linux
(`memory.js`, `redteam.js`, `rtk.ts`, skill `opencode-coordination`).

## Design de memória (docs/memoria-rag.md)

Camadas no espírito do MemGPT/Letta: **hot** (AGENTS.md ≤10 KB, sempre no prompt) · **warm**
(skills, sob demanda) · **cold** (episódica, buscada) · **semântica** (manifests + docs, por host).
Fontes: survey *"Memory in the Age of AI Agents"* (dez/2025), A-MEM (NeurIPS 2025), MemGPT/Letta, Zep/Graphiti.
RAG de verdade (vetores + grafo temporal) fica no host Linux; o celular guarda só cache e ids.
