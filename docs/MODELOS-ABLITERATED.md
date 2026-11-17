# Modelos abliterated / Dolphin / MTP — pesquisa 17/11

## O que foi pedido
"ache uma versao dolphin ou abliterated MTP" para o TAB (1B/1.5B, arm64, Termux, sem GPU).

## O que a busca achou (web)
- `Dolphin`/`abliterated` e' uma linhagem real (remocao de recusa), mas no tamanho
  que cabe no aparelho (<=1.5B Q4) **nao ha um MTP abliterated confiavel e verificado**
  com model card claro. O que aparece sao modelos 27B+ (ex.: Qwen3.5-9B MTP uncensored,
  Qwen3.8-27B Heretic-Abliterated) — nao cabem em 5.5 GB de RAM.
- O MTP real do ecossistema e' um **draft layer** (speculative decoding), nao um
  modelo standalone de chat. No `llama-cli` local aparece `--spec-type draft-mtp`,
  `--spec-draft-threads-batch`, `--spec-draft-sampling {greedy,probabilistic}`.
  Isso e' para server com modelo grande + rascunho, nao para one-shot de 1B em CPU.
- O Qwen 4B MTP do host (duplex) e' justamente `Qwen3.5-4B-MTP` (ctx 12.288,
  perfil slim) — roda no PC, nao no celular.

## Decisao
**Nao trocar o Gemma 3 1B IT agora.** Motivos medidos:
1. Gemma 3 1B Q4_K_M = 769 MB, 140 idiomas, PT melhor que Qwen 2.5 1.5B.
2. O erro do TAB nao e' recusa (o modelo responde) — e' alucinao em RAG, que
   o gate segura. Abliterate nao melhora fidelidade a fonte.
3. Modelos abliterated pequenos encontrados nao tem avaliacao de fidelidade PT;
   trocar sem medir e' exatamente o que a casa proibe ("medir antes de acreditar").

## Quando reavaliar
Se aparecer `dolphin-*-1.5b-Q4_K_M.gguf` com:
- licenca clara (Apache/MIT),
- suporte PT documentado,
- benchmark de fidelidade (nao so "0 refusals"),
entao baixar para `~/models/slm/candidates/`, rodar `tests/bench-survival-12.sh`
com `TA_SLM_MODEL` apontando para ele e comparar: se nao superar o Gemma no
gate, nao entra.

Comando de teste (quando houver candidato):
```bash
TA_SLM_MODEL=~/models/slm/candidates/xxx.gguf bash tests/bench-survival-12.sh
```
