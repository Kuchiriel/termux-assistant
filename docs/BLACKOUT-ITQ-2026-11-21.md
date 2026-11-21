# Blackout RAG com Joint-ITQ (21/11)

Origem: LittleBit-2 (Samsung, ICML 2026). O que foi aproveitado **não** foi o
QAT — foi o primitivo de geometria: rotação ortogonal + Joint-ITQ para alinhar
vetores ao hipercubo binário antes de binarizar.

## O que mudou

- `blackout/offline-itq-index.json`: 18.046 códigos binários de 256 bits
  (609 KB) + matriz de rotação, gerados do `corpus.db` do próprio aparelho.
  Nenhum segredo, nenhum embedding de rede, nenhuma API.
- `blackout/itq_index.py`: lookup em Python puro (`bit_count`), sem numpy —
  funciona no Termux.
- `blackout/offline_answer.py`: fusão RRF entre FTS5/BM25 e o índice binário,
  com dedupe por fonte antes de fundir (evita inflar um documento com vários
  chunks). Se o índice faltar, mantém o comportamento anterior.

## Medição no celular

60 perguntas, mesmo `corpus.db`:

| modo | recall@8 |
|---|---:|
| FTS5/BM25 | 0,917 |
| binário ITQ sozinho | 0,700 |
| **fusão RRF** | **0,933** |

Latência: ~105 ms por consulta no índice binário; resposta completa do
`offline_answer.py` em ~0,23 s. Sem internet, sem LLM, sem servidor.

## Limitação

O ganho é pequeno (+1 pergunta em 60) e o binário sozinho é pior que o BM25 —
ele serve como **recuperador complementar**, não substituto. A matriz de
rotação precisa ser regenerada se o `corpus.db` mudar de conteúdo/ordem.
