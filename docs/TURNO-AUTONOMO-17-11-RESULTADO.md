# Turno autônomo — resultado (17/11, 21:45Z)

## O que foi entregue (com número)

| item | medido |
|---|---|
| Modo rápido do TAB (sem SLM) | **17/17 dominios CONFIAVEL em 118–311 ms** (antes: 100–200 s com SLM) |
| Bateria com SLM (Gemma 3 1B + gate) | 12/12 CONFIAVEL, 84–204 s por caso, temp 42–48 °C |
| Dominios novos | hipotermia, queimadura química, desidratação, AVC (FAST), torniquete (com contradição clínica da cobra) |
| Widget novo | `crouton-socorro` (emergência offline, um toque) |
| CLI | `ta tab "pergunta"` (rápido), `ta slm` (com modelo), `crouton-tab` (RAG+gate) |
| Jobs do celular | **14 jobs, 0 quebrados** (corrigido o falso positivo de shebang dos backups) |
| Instalador | normaliza shebang no runtime (regra 7) — não volta o bug |
| Delegação | job 117 `fleet-retry` despacha as 4 tarefas assim que o host voltar |
| Publicação | `termux-assistant` GitHub: `ff02cec`, `b03ebde`, `c1e26d1`; ai-mesh `98a3fd0` |

## Bugs encontrados e corrigidos nesta noite

1. **Instalador quebrava shebang** ao copiar do repo para `~/bin` (env não existe no
   Termux) — agora normaliza; era a causa de "jobs quebrados".
2. **`ta`/`house`/`tab-fast` com shebang de repo** — corrigidos no runtime e
   automaticamente pelo instalador.
3. **OR vs AND no retrieval**: com AND (termo PT + termo EN) o resultado era 0.
   Agora OR, exceto nos pares exatos (choking/burn/snake...).
4. **Regra de água vazando para queimadura/ferida** (medido na bateria de 6) —
   gerador por domínio + gate de domínio.
5. **Tradução trocando "costas" por "barriga"** — gate de termos essenciais.
6. **llama órfão** drenando bateria — `Popen + kill` em todo caminho.
7. **`jobs-audit` acusava backup como job quebrado** — ignorado.

## O que ficou bloqueado (e como retoma)

- Host inalcançável do celular (LAN/tailnet/onion sem resposta): os 4 wakes
  (Tatu, Lince, Cervo, Falcao) estão escritos em `~/bin/task-*.txt` e o job 117
  dispara sozinho quando a rota voltar.
- Bus GitHub: fecha novos comentários acima de 2500 (HTTP 403). Logs e entregas
  estão no ai-mesh e em `~/.local/state/`.
- Kaggle v10: era demora, não travamento (corrigido o diagnóstico). Em execução.

## Nota honesta sobre segurança

O TAB dá passos **extraídos de fontes citadas** (FM 4-25.11, FirstAidQA, NHS,
Kiwix, CDC/WHO) e recusa quando não há fonte. O SLM 1B alucina; o gate barra.
Ainda **não** é orientação médica validada — para emergência real, ligue para
emergência e use como apoio de primeiros socorros, não como diagnóstico.
