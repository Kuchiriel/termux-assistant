---
name: github-cli
description: Fazer tudo no GitHub pelo `gh` CLI (autenticado) em vez do MCP de 46 tools — repos, PRs, issues, busca, releases, arquivos. Use quando precisar ler/escrever no GitHub, abrir PR, comentar issue, buscar código ou commit, ou quando o MCP github não estiver disponível.
---

# GitHub pelo `gh` CLI (substitui o MCP de 46 tools)

O MCP `github` foi **desligado de propósito** (economia de tokens: 46 schemas em todo
request). O `gh` CLI está autenticado como **Kuchiriel** (scopes `repo`, `read:org`, `gist`)
e cobre o mesmo terreno. Use **timeout** nas chamadas de rede.

## Comandos que resolvem 95% do caso

```bash
gh repo view Kuchiriel/ai-mesh --json name,description,isPrivate,pushedAt
gh repo create Kuchiriel/x --private --description "..." && cd x && git push -u origin main
gh pr list --repo Kuchiriel/ai-mesh --state open
gh pr view 12 --repo Kuchiriel/mt5 --json title,body,state,comments
gh pr create --fill --head branch --title "..." --body "..."
gh pr merge 11 --squash --delete-branch
gh issue list --repo Kuchiriel/mt5 --state open
gh issue comment 12 --repo Kuchiriel/mt5 --body "..."
gh release list --repo Kuchiriel/x
```

## Busca e API (o resto)

```bash
gh search code "kanban" --repo Kuchiriel/ai-mesh --json path,repository
gh search issues "MESH-MANIFEST" --repo Kuchiriel/mt5 --state open
gh api repos/Kuchiriel/mt5/issues/12/comments -F body=@arquivo.md
gh api repos/Kuchiriel/mt5/issues/12/comments --jq '.[-5:][] | .body'
gh api repos/Kuchiriel/nixos-ai/contents/path/file.ts -q .content | base64 -d
gh api repos/Kuchiriel/nixos-ai/git/trees/HEAD?recursive=1 -q '.tree[].path'
gh api graphql -f query='...'
```

## Pegadinhas (já pagas)

- **Bus com >100 comentários**: `page=1` traz os **antigos**. Calcule a última página:
  `N=$(gh api repos/OWNER/REPO/issues/12 -q .comments); P=$(( (N-1)/100 + 1 ))`
  e use `?per_page=100&page=$P`.
- `gh api -F body=@arquivo.md` **tenta parsear o arquivo como JSON** → para texto puro use
  `-f body="$(cat arquivo.md)"`.
- Duplicar `-F body=` no mesmo comando → `unexpected override existing field under "body"`.
- Saída JSON grande: filtre com `--jq` no servidor (evita despejar 60 KB no contexto).
- **PR que carrega histórico demais**: se a branch foi criada de um `main` local desatualizado,
  o PR aparece com centenas de arquivos. Refaça a branch a partir de `origin/main`
  (`git checkout -B branch origin/main && git reset --hard origin/main`).
- Trabalho de outra pessoa no mesmo repo: **worktree isolado** (`git worktree add -B branch /tmp/x origin/main`)
  → nunca toque no `main` com mudanças não commitadas dos outros.

## Por que o MCP está desligado

O Code Mode injeta o catálogo de tools MCP no prompt de **todo** request. As 46 tools do
github custavam ~2k tokens/request sem uso. O Linux mediu o mesmo efeito: 48 → 19 tools =
**−3.397 tok/request** (`docs/META-TOOLS-E-ECONOMIA-DE-TOKENS.md`, nixos-ai). O CLI não
custa contexto: é uma linha de shell + esta skill.

Religar (se precisar da API estruturada): `MEMORY_TERMUX_MCP_TRIM=0` no serviço, ou
`"disabled": false` em `providers.mcp.servers.github` do `opencode.json`.
