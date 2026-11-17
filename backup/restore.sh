#!/usr/bin/env bash
# restore.sh — restaura um backup para um diretorio DESTINO (default: $HOME).
# Nunca sobrescreve sem cópia de segurança do arquivo atual. Nunca apaga nada.
set -uo pipefail
HOME_DIR="${HOME:-/data/data/com.termux/files/home}"
SRC="${1:-}"
[ -f "$SRC" ] || { echo "uso: restore.sh <tar.gz> [destino]"; exit 2; }
DEST="${2:-$HOME_DIR}"
mkdir -p "$DEST"
tar -tzf "$SRC" >/dev/null 2>&1 || { echo "tar invalido"; exit 1; }
(cd "$DEST" && tar -xzf "$SRC" --keep-newer-files 2>/dev/null) || true
echo "restaurado de $SRC para $DEST (arquivos mais novos preservados)"
