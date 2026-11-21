---
name: auto-wake
description: Manter o agente trabalhando sozinho e VISIVEL NO TUI (hook experimental.idle admite prompt sintetico na propria sessao), com fila de auto-tarefas, orcamento de wakes e metricas honestas. Use quando o dono dormir, quando precisar continuar sozinho, ou para enfileirar a proxima tarefa.
---

# auto-wake — o agente continua sozinho, **visível no TUI**

Não é background: quando a sessão termina o turno e fica ociosa, o plugin
(`memory-termux.js`) registra o hook **`experimental.idle`** e **admite um prompt sintético
na própria sessão** → o trabalho continua **na conversa do OpenCode**, na frente do dono.

## API (OpenCode 2.2.5)

```js
export default {
  id: "meu-plugin",
  async setup(ctx) {
    await ctx.session.hook("experimental.idle", async (event) => {
      await ctx.session.synthetic({ sessionID: event.sessionID, text: "..." });
    });
  },
};
```

- O loader do 2.2.5 exige **`export default` com `id` + `setup(ctx)`**. O named export V1
  (`export const X = async () => ({...})`) **não carrega**:
  `PluginModule.LoadError: ... Missing key at ["default"]`.
- Erro de sintaxe no plugin = **o plugin inteiro fora** (`AggregateError: N errors building`).
  Cuidado com **backtick sem escape dentro de template literal** — foi o que quebrou uma versão.

## Fila de auto-tarefas

```bash
~/bin/auto-wake enqueue "tarefa"   # enfileira (FIFO, respeita o teto)
~/bin/auto-wake status             # fila + teto + orçamento de wakes
~/bin/auto-wake queue-limit        # mostra o teto da fila
~/bin/auto-wake next               # interno (o plugin usa)
```

Regras implementadas:

- só acorda se houver **tarefa na fila** (fila vazia = sessão fica ociosa de verdade);
- fila: **teto central de 12** (`AUTO_WAKE_MAX_QUEUE`); tarefa nova no teto falha com rc=1,
  duplicata exata é idempotente;
- orçamento: **máx. 12 wakes/hora** + gap mínimo de 3 min;
- **não** mexe na sessão da noite (`Turno da noite - TAB`, que tem ciclo próprio);
- o prompt admite as regras: medir antes de agir, não apagar nada, não reiniciar o opencode,
  segredos fora do bus/repo, e **enfileirar a próxima tarefa** ao terminar.

## Métricas honestas (o que mentiu na noite)

| métrica | problema | use |
|---|---|---|
| "respondeu" = mensagem no bus | o agente **trabalha e não responde no chat** → falso negativo | **atividade da sessão** (`time.updated`) |
| `time.updated` como "parado" | **não avança** durante tool call longa (rebuild, pesquisa) | campo **`busy`** + atividade real |
| cooldown com hora local | `date -d "23:56:37"` = hoje 23:56 = **futuro** após a meia-noite → wake nunca dispara | **epoch** |

## Canal de entrega para outros agentes

`~/bin/wake-direct <codinome> "msg"` — entrega **direta** na sessão do agente (roda no host,
a senha do servidor **fica lá**), com modo adaptativo: `steer` se ocioso, `queue` se ocupado.
Detalhes e as APIs que quebraram: skill `fleet-comm`.
