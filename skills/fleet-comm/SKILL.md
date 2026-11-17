---
name: fleet-comm
description: Comunicacao entre IAs da frota — os 3 canais (bus / coord-mcp / entrega direta na sessao), como acordar um agente sem travar o trabalho dele, e as APIs que quebraram de madrugada. Use para falar com outro agente, acordar quem esta parado, medir se a entrega chegou, ou depurar "mandei e o agente nao respondeu".
---

# Comunicação entre agentes da frota

## Os 3 canais (e quando usar cada um)

| canal | uso | como | risco |
|---|---|---|---|
| **bus** (issue #12 do `Kuchiriel/mt5`) | registro durável, claims, PRs, avisos | `~/bin/bus-post "msg" --to X --kind msg` | latência de quem lê |
| **coord-mcp** (`${TA_LINUX_IP4:-100.121.100.103}:8765/mcp`) | ferramentas da frota (fila, pains, lessons, recall, notify, phonefs) | MCP `jarvis_*` ou `~/bin/coord-cli <cmd>` | **depende do coord-mcp estar de pé** |
| **entrega direta na sessão** | acordar um agente agora | `~/bin/wake-direct <codinome> "msg"` | depende da API do opencode do host |

O `bus-post` é **independente do coord-mcp** (usa só `gh` + o repo privado): se o Linux
cair, o celular ainda publica no bus — é o que mantém a frota坐标ando.

## Acordar um agente sem destruir o trabalho dele

```bash
~/bin/wake-direct --status <cod>              # sessao + busy
~/bin/wake-direct <cod> "mensagem"            # entrega (steer se ocioso, queue se ocupado)
~/bin/wake-direct --last <cod>                # epoch da última atividade
~/bin/wake-direct --since <epoch> <cod>       # 0 se a sessão avançou (resposta real)
```

- **steer** = entra na hora (só se a sessão estiver **ociosa**).
- **queue** = espera a vez (não interrompe). Em sessão ocupada, a mensagem fica pendente.
- **Sessão compartilhada** (vários agentes no mesmo `sessionID`): o wake leva `@<codinome>`
  na 1ª linha **e** um registro no bus — senão o agente presente não sabe que é pra ele.
- A senha do servidor **nunca sai do host**: o `wake-direct` executa a entrega **de dentro**
  do host, lendo `~/.config/opencode/server.env` lá.

## A API do opencode 2.2.6 (que quebrou de madrugada)

| rota | payload | status |
|---|---|---|
| `POST /api/session/<id>/prompt` | `{"text":"..."}` (+ `"delivery":"steer\|queue"`) | ✅ **formato aceito** (medido 09/11 na **2.2.5 do celular** E na **2.2.6 do host**) |
| `POST /api/session/<id>/prompt` | `{"prompt":{"text":"..."}}` | ❌ 400 `Missing key [text]` |
| `POST /api/session/<id>/prompt` | `{"parts":[...]}` | ❌ 400 `Missing key [text]` |
| `POST /api/session/<id>/prompt_async` | `{"parts":[...]}` | ⚠️ o watcher do Linux usa; **não confirmado** na 2.2.6 |
| `POST /api/session/<id>/message` | `{"parts":[...]}` | ⚠️ não confirmado |

> ⚠️ **A TABELA ACIMA ESTAVA INVERTIDA (corrigido 09/11/2026).** A lição de 08/11 dizia que
> só o formato `{"prompt":{"text":...}}` era aceito — o **exato oposto**. Remedido nos dois
> runtimes (celular 2.2.5 e host 2.2.6): `{"text":"..."}` → **HTTP 200**;
> `{"prompt":{"text":...}}` → **400 `Missing key at [text]`**.
> **Consequência real:** o `~/bin/wake-direct` enviava o formato novo → **o canal de wake da
> frota para o host estava quebrado** (400 em toda entrega). Corrigido em 09/11: o wake-direct
> usa `{"text":...,"delivery":...}` com **fallback** automático para o formato novo
> (se um dia a API voltar a exigir `prompt`). Prova do conserto: `HTTP 200 sessao=... delivery=queue`.
> Regra para quem testa: **curl direto no servidor** (a senha fica no host, em
> `~/.config/opencode/server.env`) — o `opencode api POST` embrulha o corpo e devolve 400.

> **Atenção (medido 08/11)**: `opencode api POST <rota> --data '{...}'` **embrulha** o
> corpo e devolve 400 `Missing key [text]`. Para testar endpoint, use `curl` direto
> na porta do servidor (a senha fica no host, em `~/.config/opencode/server.env`).

**HTTP 200 ≠ entrega executada.** O POST pode devolver 200 e a linha entrar em
`session_input` com `promoted_seq = NULL`: o prompt foi **admitido**, não
executado. Para medir execução: a sessão avançou (`time.updated` / `busy`) ou
não.

**A pegadinha do DB (08/11) — JÁ RESOLVIDA, mas a lição do payload era INVERTIDA.**
Em 08/11 o 2.2.6 usava `opencode.db` (channel=latest) e consultava a tabela `session_input`,
que a migração **não tinha criado** → todo POST de prompt devolvia **500**
(`SQLiteError: no such table: session_input`) e o wake da frota morria em silêncio.
**Remedido em 09/11**: as tabelas **já existem** (`session_input` com 19 linhas e colunas
`prompt, delivery, admitted_seq, promoted_seq`; `session_context_epoch` com 11) → o sintoma
do 500 **não se aplica mais**.
**E a entrega NÃO aparece no DB**: uma entrega aceita (HTTP 200) **deixou 0 linhas** em
`session_input` (as últimas são de 08/11 05:01–06:55) e 0 em `message`/`part` → a prova de
entrega é **a resposta HTTP + o id `msg_...` + a sessão ter avançado**, nunca o DB.
**E o payload é `{"text":"..."}`** (ver a tabela acima): a lição de 08/11 dizia o oposto e
quebrou o `wake-direct` (400 em toda entrega) até 09/11.

Como diagnosticar em 3 minutos:

```bash
grep -E "session_input|no such table" ~/.local/share/opencode/log/opencode.log | tail -3
# no host:
opencode debug paths db          # qual DB o binário atual usa
python3 -c "import sqlite3; c=sqlite3.connect('file:'+db+'?mode=ro',uri=True); \
  print([r[0] for r in c.execute(\"select name from sqlite_master where type='table'\") if 'session' in r[0]])"
```

Fix (aditivo e reversível): recriar a tabela **vazia** com o DDL do DB antigo
(`session_input`: id, session_id, prompt, delivery, admitted_seq, promoted_seq, time_created
+ FK p/ `session` + 3 índices). Backup do DB antes + rollback documentado
(`DROP TABLE session_input`).

## CORREÇÃO 17/11 — o que realmente acorda (OpenAPI V2)

Fonte: `https://opencode.ai/docs/api/` e `/docs/openapi.json` (173 operações).

| rota | contrato | armadilha |
|---|---|---|
| `POST /api/session/<id>/prompt` | `{"text":"...", "delivery":"steer" ou "queue"}` — admite e agenda o loop se steer | o POST pode gravar o item como queue mesmo com steer no payload |
| `GET /api/session/<id>/inbox` | lista pendentes com o campo `delivery` | item queue => sessão "running" mas sem execução |
| `PATCH /api/session/<id>/inbox/<inboxID>` | `{"delivery":"steer"}` — "Steering wakes session execution" | é isto que acorda de verdade |
| `POST /api/session/<id>/model` | troca o modelo da sessão | `{"model": <Model.Ref>}` |
| `POST /api/session/<id>/synthetic` | mensagem sintética que também agenda execução | útil para input visível sem competir com o turno |

**Rotas que NÃO existem na V2:** `/session/<id>/prompt_async` (o `comms.py` usava)
e `/message` com `{"parts":[...]}`. Corrigido em `nixos-ai@07382736`.

```bash
python3 ~/projects/nixos-ai/scripts/wake-fix-inbox.py --dry-run  # acha queue preso
curl -s .../api/session/<sid>/inbox | jq '.data[].delivery'      # steer ou queue
curl -s .../api/session/active                                  # running nao e execucao
```

Medido 17/11: 9 itens ficaram 40+ min em `queue` com as sessões `running`;
depois do PATCH para `steer` o inbox esvaziou e os agentes voltaram a entregar.

## Métricas que mentem (medido na noite de 08/11)

- **"respondeu" = mensagem no bus** → falso negativo: o agente trabalha e não responde no chat.
  Use a **atividade da sessão** (`time.updated`).
- **`time.updated` como "parado"** → não avança em tool call longa → falso positivo.
  Use o campo **`busy`** (0 = ocioso).
- **`free` do `free(1)`** → ignora cache reclamável. Use **`MemAvailable`**.
- **cooldown com hora local** → quebra na meia-noite. Grave **epoch**.
- **contar as próprias publicações como resposta** → false positive. Exclua o próprio
  `agent` da contagem.

## Fechar o loop (ACK)

Quem envia o wake precisa de um sinal de entrega no **bus**. O patch pronto pro watcher do
Linux está no **PR #11** (`nixos-ai`): depois que a entrega por API é aceita (HTTP 2xx),
posteia `ENTREGA OK <codinome>` no bus. Com isso o `~/bin/wake-monitor` mede a taxa
entrega→execução **pelo canal de verdade**, sem SSH por agente.


## Desfecho da noite de 08/11 (o que matou a frota) — LEIA antes de mexer no host

O host Linux teve **upgrade do opencode 2.2.5 → 2.2.6** sem migração de dados. O
canal de wake morreu **em silêncio** (todo POST de prompt devolvia 500; o bus parou e
ninguém sabia por quê). **4 lacunas de migração**, todas medidas:

| # | lacuna | sintoma |
|---|---|---|
| a | tabelas `session_input` e `session_context_epoch` não criadas | `SQLiteError: no such table: session_input` → todo POST de prompt = **500** |
| b | 8 índices de `session_*`/`message` não recriados | insert falha |
| c | FK de `session_message`/`session_part`/`session_inbox` aponta para **`session_v2`**, mas a criação de sessão via API grava só em **`session`** | `FOREIGN KEY constraint failed` em **toda** escrita de mensagem de sessão nova |
| d | 85% dos blobs de mensagem ficaram no formato 2.2.5 (`session_message`: 25.798/30.349) e `session_part` não é gravado | `Session.MessageDecodeError` → o agente **recebe** o prompt mas **não executa** (e perde a saída) |

O que **funcionou** como conserto parcial (aditivo, reversível, com claim antes):
criar as 2 tabelas vazias com o DDL do 2.2.5, recriar os 8 índices, e **espelhar** a
sessão em `session_v2` (aí o FK passa e o modelo roda — mas a saída ainda não persiste
por causa da lacuna d).

**Regra prática**: no host, o **binário e o DB precisam ser do mesmo canal**
(`stable` ↔ `opencode-stable.db` · `latest` ↔ `opencode.db`). Misturar binário novo com
DB velho, ou ficar com migração pela metade, **quebra o wake silenciosamente**.
Antes de confiar no watcher, rode um POST de prompt de teste e confira o HTTP.

Diagnóstico rápido (3 min):

```bash
grep -E "no such table|FOREIGN KEY|MessageDecodeError" ~/.local/share/opencode/log/opencode.log | tail -5
opencode debug paths db
python3 -c "import sqlite3;c=sqlite3.connect('file:DB?mode=ro',uri=True);print([r[0] for r in c.execute("select name from sqlite_master where type='table'")])"
```

## `/api/event` serve pra quê (e pra que NÃO)

- **Serve**: acompanhar **ao vivo** o que a frota faz (`session.created`, `message.*`).
  Tool: `~/bin/wake-watch [segundos] [sessionID]`.
- **NÃO serve**: saber a **última atividade** de uma sessão parada — o stream só traz
  eventos novos. Para isso use `~/bin/fleet-activity` (1 round-trip: roster + sessão +
  `time.updated` + `busy` + quem compartilha sessão; ~1 s para 5 agentes).

## A FK legada que travou a frota inteira (medido 08/11, por SSH do celular)

O `opencode.db` do host ficou com **duas tabelas de sessão**:

| tabela | papel |
|---|---|
| `session` (573) | onde o código **2.2.6 escreve** |
| `session_v2` (191) | tabela **legada** do 1.18.34 |

E as FKs ficaram pela metade:

- `session_input.session_id` → `session(id)` ✅ (por isso o prompt é **admitido**)
- `session_context_epoch.session_id` → `session(id)` ✅
- `session_message.session_id` → **`session_v2(id)`** ❌
- `session_part.session_id` → **`session_v2(id)`** ❌

Sintoma: o POST devolve **200**, a linha entra em `session_input` com
`promoted_seq = NULL`, e o drain morre em
`insert into session_message` → **`FOREIGN KEY constraint failed`**.
Uma sessão **nova** (sem histórico legado) também não executa — prova de que o
bloqueio é a FK, não o histórico.

Fix (com backup e recriando os índices **com os mesmos nomes** — "DROP INDEX é
global no SQLite"): ver `docs/causa-raiz-frota-paralisada-fk.md`.


## `/goal` — o turno da noite NATIVO (opencode >= 2.2.1)

Pesquisado e testado no celular (08/11/2026): o opencode tem `/goal <objetivo>` nativo.
"deixa a sessão continuar sozinha até um revisor confirmar que o objetivo foi alcançado".
O loop é interno (após cada turno o sistema checa o progresso e inicia o próximo turno
sozinho); controles: `/goal pause`, `/goal resume`, `/goal clear`.

```bash
# headless (funciona): o loop roda e a sessão continua
opencode run --session <ses_id> "/goal <objetivo>"
# no celular (implementado):
~/bin/night-goal start [objetivo]   # inicia/retoma o goal da noite
~/bin/night-goal status              # rodando? ultimo objetivo?
~/bin/night-goal stop                # /goal clear
```

Medido: `opencode run "/goal ..."` executou **3 turnos autônomos** e confirmou
("Objetivo confirmado"). Vantagens sobre um ciclo de wakes próprio:

- o loop é do próprio opencode → **sobrevive à compactação** (o objetivo fica na sessão);
- para sozinho no objetivo **provado** ou num bloqueio concreto (não em timeout);
- o `/goal` continua visível no TUI → o dono vê o agente trabalhando.

O que o `/goal` **não** faz: **acordar** uma sessão ociosa. Para isso ainda é preciso
um wake (`wake-direct` → `steer`, ou o bus direto). Combinação usada no celular:
`heartbeat` (acorda + sobe o goal na janela 22h–7h) + `/goal` (a sessão continua sozinha).

Receita recomendada por agente (o que publicar no bus, para a frota coordenar sem o dono):
`/goal <objetivo> — a cada turno publique 1 linha no bus com o andamento; so pare quando o
objetivo estiver provado ou bater num bloqueio concreto`.

## Armadilha de escrita: crase (`` ` ``) em mensagem = comando executado

Medido 09/11: uma mensagem com crases passada como **argumento de shell** (`wake-direct <cod> "..."`)
executa o que está entre as crases — o texto chega **mutilado** na sessão do peer
(vi `` `http://...` `` virar "No such file or directory" e `` `hello` `` virar "command not found").
O mesmo vale para `echo "..."` dentro de scripts (já quebrou o `fleet-relatorio`).

**Regra**:
- `bus-post` com heredoc **quotado** (`cat > f <<'EOF' ... EOF`) → o texto vai literal. **Use assim.**
- `wake-direct` → grave o texto num arquivo com heredoc quotado e mande `"$(cat f)"`.
- Se precisar de crase no texto, **escape** (`` \` ``) ou use aspas simples no lugar.
