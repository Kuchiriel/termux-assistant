---
name: house-index
description: Como navegar a casa inteira sem queimar contexto — HOME.md, index/house.json, CLI house (list/describe/search/tui/web) e MCP coord_house; ponteiros bidirecionais para o monorepo
---

Use quando a pergunta for "onde mora X", "qual o entrypoint de Y", "o que já
foi medido sobre Z", ou antes de abrir vários arquivos para descobrir o mapa
da casa.

## Regra de ouro (token)

1. Leia **só** `HOME.md` (ou rode `house list`).
2. Abra **no máximo um** doc de domínio (`docs/house/<id>.md`).
3. Se precisar de detalhe, `house describe <id>` — não carregue o repo
   inteiro, não leia `AGENTS.md` de todos os hosts.

## Comandos (celular e Linux)

```bash
house list                 # uma tela: id, status, hosts, título, CLI
house list --json          # para máquina
house search "gpu"         # acha por id/título/tag
house describe lab         # entrypoints, docs, código canônico e última medição
house status               # status + última medição de todos
house tui                  # menu (dialog quando existe; --plain força números)
house web lab              # imprime/abre http://.../house#lab
house docs --check         # acusa HOME.md/docs/house desatualizados
```

No MCP, a mesma pergunta:

```text
coord_house action=list
coord_house action=describe id=lab
coord_house action=search query=gpu
coord_house action=status
```

O meta-tool `tools_search`/`tools_call` continua sendo a porta das ~46 tools
do JARVIS; `coord_house` é só o índice.

## O que é canônico

- **Fonte da verdade:** `index/house.json` no repo `Kuchiriel/ai-mesh`.
- **Porta humana:** `HOME.md` (a tabela é gerada por `house docs`).
- **Ponte para o código:** cada entrada tem `code.canonical` (monorepo
  `nitro-v15:~/projects/nixos-ai`) e `code.mirror` (celular).
- **Ponte de volta:** todo doc satélite começa com
  `> Volta para [HOME](../../HOME.md)`.

## Adicionar uma capacidade à casa

1. Edite `index/house.json` (id, summary, status, hosts, entrypoints, docs,
   code, health, last_measured).
2. Rode `house docs` (gera a tabela e `docs/house/<id>.md`).
3. Prove o `health` de verdade e registre a medição (`ck=v3` se for modelo).
4. `house docs --check` tem de passar; commit no ai-mesh e `mesh-repo publish`.
5. No Linux: `git -C ~/projects/ai-mesh pull --ff-only`; no celular:
   `mesh-repo pull`.

## Não faça

- Não duplique a lista de comandos aqui ou no AGENTS.md: aponte para o índice.
- Não invente entrypoint que não rodou; `planned` é status honesto.
- Não coloque segredo (token, chave privada) no índice nem nos docs.
- Não use `last_measured` de checker inválido: só `ck=v3` conta.
