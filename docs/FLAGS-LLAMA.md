# TAB — flags llama.cpp ótimas para one-shot + anti-alucinação (medido 17/11)

Hardware: **Motorola Edge (racer/qcom), arm64-v8a, Android 11, 8 cores, 5.5 GB RAM**.
Runtime: `llama-cpp` 1.0.0 do repo Termux (`pkg install llama-cpp`),
`llama-cli` / `llama-bench` em `$PREFIX/bin`.

## Problema

O default do `llama-cli` é `--temp 0.80 --top-k 40 --top-p 0.95 --min-p 0.05`.
Isso é ótimo para conversa, mas em RAG de sobrevivência **aumenta alucinação**:
o modelo inventa "boca a boca" em engasgo e troca "back slaps" por "batidas na barriga".

## Flags aplicadas em `tab_rag.generate()` e `tab_translate.translate()`

```
--temp 0.1          # quase determinístico (0 é greedy rígido; 0.1 mantém um pouco de fluência)
--top-k 20          # corta cauda longa de tokens improváveis
--top-p 0.9         # nucleus mais estreito
--min-p 0.05        # remove tokens com probabilidade relativa baixa
--typical-p 0.9     # locally typical sampling (typ_p) — penaliza extremos
--seed 42           # REPRODUCIBILIDADE: mesmo prompt => mesma saída
-st, --single-turn  # uma resposta e sai (sem modo chat interativo)
--no-warmup         # evita custo extra de warmup em one-shot
-t 4 -tb 8          # 4 threads de geração, 8 de prompt (medido: prefills melhor)
--ctx-size 2048     # contexto enxuto: prompt + fontes, sem gastar RAM
--no-display-prompt # stdout limpo para o parser
```

## O que NÃO usar (medido/recomendado)

- `--repeat-penalty` alto (1.1+) — artigo de 07/2026 mostra que mecanismos novos
  (DRY, typ_p, min_p) são melhores; repeat penalty可以 deformar tradução.
- `--temp 0` puro — greeting "recém-nascido" em vez de "bebê" mesmo assim;
  `temp 0.1 + typ_p` deu a mesma saída com 8 s em vez de 14 s.
- `-fa` (flash attention) em CPU não ajuda e pode custar compatibilidade.
-------

## Benchmark (llama-bench, Gemma 3 1B Q4_K_M, CPU)

| configuração | pp512 | tg128 |
|---|---:|---:|
| `-t 4` | 11,5 t/s | 7,4 t/s |
| `-t 4 -tb 8` (pp256) | 15,9 t/s | 6,1 t/s (tg64) |

Conclusão: **prefill com 8 threads, geração com 4**. O gargalo é geração (~7 t/s),
não a leitura das fontes.

## Metacognição > sampling

Mesmo com flags ótimas, o 1B ainda errou. O que realmente segurou foi o **gate**:

1. `tab_rag` checa suporte lexical/numérico de cada passo contra as fontes.
2. Verifica domínio (água ≠ queimadura ≠ engasgo).
3. Verifica idioma (descarta linhas em inglês).
4. `tab_translate` checa números **e termos essenciais**
   (`back slaps` → palmad/golp, `shoulder blades` → escápul, etc).

Se o SLM falha, entra o fallback determinístico em PT com passos extraídos das fontes.
**Modelo propõe, checker decide** — o mesmo princípio do duplex do Linux.

## Processo one-shot (bateria/RAM)

`Popen + communicate(timeout) + proc.kill()` em `tab_rag.py` e `tab_translate.py`.
Isso corrige o bug medido: `timeout` com `subprocess.run` matava o Python mas
deixava o `llama-cli` órfão drenando bateria. Agora nenhum processo fica residente.
