# F-Droid: trocar de fonte sem perder a casa

> Medido no aparelho (Motorola Edge, arm64, Android 11) em 19/11/2026.
> A fonte atual é **F-Droid** (`TERMUX_APP__APK_RELEASE=F_DROID`,
> v0.119.0-beta.3). Isto é **bom**: continuar no F-Droid é seguro.

## A regra que mata o medo

Termux e plugins usam `sharedUserId=com.termux`: **todos os APKs precisam ter a
mesma chave de assinatura**. Trocar de fonte (F-Droid ↔ GitHub ↔ Play) exige
**desinstalar os APKs** — e desinstalar **apaga `$HOME`**.

> O README oficial do termux-app diz exatamente isto e aponta
> "Backing up Termux" antes do uninstall.

Então a pergunta não é "posso trocar de fonte?", é **"meu estado sobrevive ao
uninstall?"**. Hoje: **sim**, e está provado por comando.

## Backup (1 comando, ~40 s)

```bash
ta backup
# -> ~/storage/shared/termux-assistant/backups/.ta-<stamp>.tar.gz (39 MB) + sha256
```

Cobre: `bin/`, `.termux/`, `.shortcuts/`, `.config/opencode/`,
`.config/termux-assistant/` (o `.env` com os **caminhos** das chaves),
`.local/share/termux-assistant/`, `offline-corpus/` (19k docs), `ai-mesh/docs`,
`ai-mesh/skills`, `projects/termux-assistant`.

O backup vai para **shared storage** (sobrevive ao uninstall) e é sha256-assinado.

## Restore (provado, não alegado)

```bash
ta restore <arquivo.tar.gz>          # restaura em $HOME
# ou para um diretório de teste, sem tocar em nada:
ta restore <arquivo.tar.gz> $PREFIX/tmp/restore-teste
```

Medido: 1531 entradas, 195 binários, e o `house` **funciona a partir do
restaurado** (`python3 <restore>/bin/house list` devolve o índice completo).

## Checklist de troca de fonte

1. `ta backup` e **copie o .tar.gz para fora do celular** (HD/PC).
2. Anote as versões: `termux-info | grep -E "VERSION|RELEASE"`.
3. Desinstale **todos** os APKs Termux (Termux, API, Widget, Window, Boot).
4. Instale **todos** da nova fonte, na mesma sessão.
5. Abra o Termux uma vez (bootstrap), dê a permissão de storage.
6. `pkg install -y python jq curl git openssh` (o mínimo do instalador).
7. `ta restore <arquivo.tar.gz>`.
8. `ta doctor` e `house status` — se ambos responderem, a casa voltou.

## O que **não** volta pelo backup (e por quê)

- **Valores de credencial** (nvidia key, token do GitHub, token do HF): ficam em
  arquivos 600 e em `~/.config/opencode/`. São **seus** — regenere ou copie
  manualmente para o aparelho novo (`$TA_HUB_TOKEN_FILE` etc. dizem onde).
- **Pacotes do sistema Termux** (`pkg`): voltam com `pkg install`.
- **O DB do opencode** (`~/.local/share/opencode/opencode.db`, 158 MB): é
  estado, não config. O backup leva a config; o histórico de sessões não.
  (Se quiser, adicione `~/.local/share/opencode` ao `TARGETS` — mas são 158 MB.)
- **O modelo do SLM** (`~/models/slm/*.gguf`, 769 MB): baixe de novo ou mantenha
  no HD (HF: `Kuchiriel/microturn-gate`, `Kuchiriel/microturn-duplex`).

## Blackout: o que já funciona sem rede

```bash
ta tab "como purificar agua"     # 17/17 dominios, ~150 ms, sem SLM
bash ~/projects/nixos-ai/scripts/house-offline.sh   # no host: unshare -n real
```

O corpus offline (19.046 docs, FTS5) está no backup. O LoRA e o modelo base
podem ser baixados do HF depois — ou o `ta backup` pode incluir `~/models` se
você quiser (769 MB).

## Se algo der errado no meio

- Nada é apagado pelo `restore`: usa `--keep-newer-files`.
- Os backups ficam em `~/storage/shared/termux-assistant/backups/` (múltiplos,
  com sha256 ao lado).
- O `install.sh` do pacote faz backup `.ta-backup-*` de cada arquivo que ele
  sobrescreve.
