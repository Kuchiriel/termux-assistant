# termux-assistant — a casa inteira num comando

Transforma um Termux novo (ou um que você quer preservar) num assistente com:
CLI unica (`ta`), API local OpenAI-compatible, modo blackout sem rede, skills,
plugins, scripts, atalhos de widget, ponteiros AGENTS e backup contra uninstall.

> **Fonte de verdade**: este repo. **Nada de segredo aqui**: tokens ficam em
> arquivos 600 no aparelho e são apontados por `.env.example`.

## Regra P0 (antes de tudo)

Todo erro encontrado vira **correção registrada na sequência**: pare, meça o
erro exato, ache a causa, corrija na origem, prove rodando de novo e registre
em `~/ai-mesh/docs/ARMADILHAS.md` via `~/bin/lesson` — **antes** de continuar.
Nunca repita um comando falho "a ver se funciona" e nunca deixe outro agente
redescobrir. Regra completa: `docs/REGRAS-P0.md`.

## Instalação em um comando

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/Kuchiriel/termux-assistant/main/install.sh)"
```

Mais seguro (recomendado): baixe, inspecione, rode:

```bash
curl -fsSL https://raw.githubusercontent.com/Kuchiriel/termux-assistant/main/install.sh -o /tmp/ta-install.sh
bash /tmp/ta-install.sh --dry-run
bash /tmp/ta-install.sh
ta doctor
```

O instalador é idempotente: nunca apaga seu `AGENTS.md` nem sobrescreve `.env`;
faz backup com sufixo `.ta-backup-*` se um arquivo mudou.

## Uso em 30 segundos

```bash
ta doctor                 # binarios, paths, jobs
ta status                 # laboratorio A/B + indice da casa
ta chat "como purificar agua?"
ta offline "primeiros socorros"     # sem internet
ta linux status                     # saude do host Linux
ta api                              # API em http://127.0.0.1:8787/v1
ta widgets                          # reinstala ~/.shortcuts e refresca
ta backup                           # tarball em ~/storage/shared/...
ta secrets                          # varredura antes de publicar
```

## O que esta incluido

| camada | conteudo |
|---|---|
| `bin/` | 44 utilitarios: lab, house, lab-sync, fleet-dispatch, mcp, offline, wake-direct, phone-fs, ... |
| `skills/` | 21 skills do OpenCode |
| `plugins/` | `memory-termux.js` |
| `widgets/` | 20 atalhos `crouton-*` (instalados em `~/.shortcuts`) |
| `api/` | servidor OpenAI-compatible em loopback (`/v1/chat/completions`) |
| `blackout/` | harness .sh: comandos locais → GGUF opcional → corpus FTS5 → "nao sei" |
| `backup/` | backup/restore para shared storage (sha256) |
| `config/` | AGENTS minimo e `.env.example` (sem valores reais) |
| `docs/` | arquitetura, F-Droid, segredos, comandos, migracao |

## F-Droid e medo de perder tudo

O aparelho hoje usa **F-Droid** (`TERMUX_APP__APK_RELEASE=F_DROID`,
v0.119.0-beta.3). Isso é bom:继续 atualizando **todos** os APKs Termux pelo
mesmo F-Droid. Nunca misture com GitHub sem antes fazer `ta backup` e
desinstalar todos os APKs (o uninstall apaga `$HOME`).

Detalhes: `docs/FDROID-E-UNINSTALL.md`.

## Segurança

- `.env` com caminhos de tokens, nunca valores.
- API escuta em `127.0.0.1` por padrão; se virar `0.0.0.0`, exige token 600.
- `ta secrets` barra publicação se achar `nvapi-`, `hf_`, `sk-`, `ghp_` ou
  atribuição de senha.
- Nenhum catálogo de 150 MB, log, memória episódica ou credencial entra no repo.

## Licença

Apache-2.0 (vide `LICENSE`).
