# REGRA P0 — Erro enfrentado = correção registrada na sequência

> **Prioridade 0 da casa (18/11/2026, dono).** Milhares/milhões de tokens são
> gastos todo dia em comandos que falham, erros repetidos e agentes
> redescobrindo o que outro agente já descobriu. Isso acaba aqui.

## A regra (vale para TODO agente, TODO host, TODO turno)

Quando **qualquer** comando/ferramenta falhar, na ordem:

1. **PARE de tentar de novo.** Não repita o comando "a ver se funciona".
2. **Meça o erro exato.** Capture stderr/stdout, código de saída, schema,
   rota, porta, timestamp. Um erro sem mensagem exata não é diagnose.
3. **Ache a causa.** Leia `--help`, schema, doc oficial, fonte, ou arquivo
   de config — nessa ordem. Se o erro disser "missing argument", descubra
   o nome real do argumento; se disser "connection timed out", descubra
   qual rota/porta está morta; se disser 403, descubra qual limite bateu.
4. **Corrija na sequência.** Aplique a correção no lugar onde o erro
   aconteceu (script, config, rota, prompt) e **rode o mesmo comando de novo**
   para provar que passou.
5. **Registre a lição ANTES de continuar**, em um destes lugares (o que
   fizer sentido):
   - `ai-mesh/memory/episodic/<host>.jsonl` (append-only) —
     `{"kind":"fix","text":"ERRO X -> causa Y -> correcao Z"}`,
   - skill correspondente (ex.: `fleet-comm`, `opencode-termux`),
   - `docs/agentes/ARMADILHAS.md` quando for armadilha recorrente,
   - `docs/lab/README.md` quando for do laboratório,
   - CLI: `~/bin/lesson "comando" "erro" "causa" "correcao"`.
6. **Só então** volte à tarefa original. O custo do registro é alguns
   tokens; o custo de outro agente redescobrir é milhares.

## Exemplos reais desta casa (não repetir)

| erro | causa | correção |
|---|---|---|
| `coord_msg '{"to","text"}'` → 2 validation errors | schema é `message`, não `text` | usar `{"to":..., "message":...}` |
| `HTTP 400 request exceeds context` | provider nvidia sem `compatibility`, ctx small | PR #99 (Tatu mediu 136×400 → 0) |
| `wake` HTTP 200 mas agente não executa | item ficou `queue` no inbox | `PATCH /inbox/<id> {"delivery":"steer"}` |
| `pgrep -f "scripts/ab_loop.sh"` casa o próprio shell | padrão bate no `bash -c` | padrão em arquivo ou PID |
| `opencode --version` modelo fixo | modelo é dinâmico | `~/bin/oc-identidade --json` |
| shebang `#!/usr/bin/env bash` em `~/bin` | Termux não tem `/usr/bin/env` | `#!/data/data/com.termux/files/usr/bin/bash`; instalador normaliza |
| `kaggle kernels status X` "Permission denied" | slug divergia do título | consultar slug real em `kernels list` |
| tempo `time.updated` como prova de execução | POST atualiza updated | prova = transcript/artefato |
| CJK/seta em commit message via zsh remoto | crase executada | `git commit -F arquivo` |
| `rm -rf` em lane temporária antes de medir | destruiu evidência | quarentena + manifesto |

## Verificação (obrigatória em todo turno longo)

```bash
~/bin/lesson --check      # erros conhecidos que ainda podem se repetir?
~/bin/lesson --stats      # quantas lições, quantas host/origem
```

Se `lesson --check` mostrar pendência, resolva antes de continuar o
backlog. Se um erro já registrado acontecer de novo, a correção anterior
está errada — corrigir a correção é parte da regra.

## Onde esta regra mora (bidirecional)

- `~/.config/opencode/AGENTS.md` (raiz do agente; carregado em cada turno)
- `~/AGENTS.md` (raiz do usuário)
- `~/ai-mesh/AGENTS.md` (contrato comum da frota — todos os hosts)
- `~/projects/termux-assistant/docs/REGRAS-P0.md` (este arquivo)
- `~/projects/termux-assistant/README.md` (ponto de entrada do pacote)
- `~/projects/termux-assistant/HANDOFF.md` (retomada)
- mt5: `AGENTS.md` e `ARMADILHAS.md` (via coord / bus #100)
