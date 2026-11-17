#!/usr/bin/env bash
# backup.sh — prova contra uninstall do Termux: copia o estado para shared storage.
# NAO apaga nada. NAO coloca segredo em repo; o tarball fica local (600).
set -uo pipefail
HOME_DIR="${HOME:-/data/data/com.termux/files/home}"
DEST="${TA_BACKUP_DIR:-$HOME_DIR/storage/shared/termux-assistant/backups}"
STAMP=$(date +%Y%m%d-%H%M%S)
mkdir -p "$DEST"
TMP="$DEST/.ta-$STAMP.tar"
TARGETS=(bin .termux .shortcuts .config/opencode .local/share/termux-assistant offline-corpus ai-mesh/docs ai-mesh/skills projects/termux-assistant)
(cd "$HOME_DIR" && tar cf "$TMP" "${TARGETS[@]}" 2>/dev/null) || true
gzip -f "$TMP" 2>/dev/null || true
F="$TMP.gz"
[ -f "$F" ] || { echo "backup falhou"; exit 1; }
chmod 600 "$F"
sha256sum "$F" | tee "$F.sha256"
printf 'backup: %s (%s)\n' "$F" "$(du -h "$F" | cut -f1)"
