# Turno autônomo — 17/11/2026 (dono dormindo)

> Regra do turno: medir antes de afirmar; nada de hype; segredo fora do repo/bus;
> nada que apague estado; não reiniciar o opencode; registrar resultado em log.
> Cada entrega precisa de **número ou arquivo**, não de promessa.

## Estado de entrada (medido 17:55Z)

- TAB: 12/12 casos de emergência CONFIAVEL (lote afinado + lote frio).
  Logs: `~/.local/state/tab-battery-final-*.txt`, `tab-battery-cold-20261117-175410.txt`.
- Modelo: Gemma 3 1B Q4_K_M (769 MB) em `~/models/slm/`; Qwen 1.5B removido
  (prova em `~/models/slm/quarantine/DELETED-qwen2.5-1.5b.txt`).
- Casa: índice `ai-mesh/index/house.json` com 12 domínios; `house` CLI/TUI;
  `/hub/house`; `coord_house` no MCP.
- Frota: 6+ agentes no host; Lince em PR #96 (coord-mcp); Tatu recebeu
  PR #99 (nvidia/tokens) sem confirmação de aplicação.
- Bloqueios: rota do host caiu do celular (LAN/tailnet/onion sem resposta);
  bus GitHub fechou para novos comentários (>2500); Kaggle v10 em execução.

## Distribuição da frota (tarefas com aceite)

| agente | tarefa | aceite |
|---|---|---|
| Lince (Linux) | revisar PR #96 contra o host real; smoke do coord-mcp | linha no log + comentário no PR |
| Tatu (Windows) | aplicar pacote nvidia (PR #99) e responder `TOKEN-OK` | linha no log da lane windows |
| Cervo (Linux) |扩ir corpus offline: achar lacunas de emergência e sugerir EXP | diff no repo + número de docs |
| Falcao (Linux) | auditar `tab_rag`/gate: procurar alucinação que passe | caso de teste que falha antes do patch |
| Onça (Linux) | instrumentar `house` com last_measured automático | PR/commit + 1 medição real |

## Fila do TAB (eu)

1. Bateria consolidada de 12 (versão fria, 1 por vez) → log único.
2. Modo rápido **sem SLM**: o gerador determinístico tem que responder em <2 s,
   para uso real de emergência (o SLM leva 100–200 s).
3. Cobertura:体检 de no máximo 2 s por pergunta → se falhar, usa determinístico.
4. Ampliar EXP/gate a partir do que o corpus realmente tem (sem inventar).

## Registro de progresso

Cada passo grava em `~/.local/state/tab-night.log` e, quando é entrega de
código, commit no `termux-assistant` (publicado no GitHub) + doc no `ai-mesh`.

## Limites que eu não vou cruzar

- Não invento número de acerto sem medir.
- Não subo modelo semevaluate e gate.
- Não deixo llama órfão (Popen+kill em todo caminho).
- Não uso `pkill -f` (só PID).
- Não escrevo em repo/bus nada que seja segredo.
