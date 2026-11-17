#!/usr/bin/env bash
# Instala/refresca atalhos do Termux:Widget no diretorio canonico ~/.shortcuts.
set -uo pipefail
HOME_DIR="${HOME:-/data/data/com.termux/files/home}"
SRC="${TA_SOURCE_WIDGETS:-$HOME_DIR/.local/share/termux-assistant/widgets}"
[ -d "$SRC" ] || SRC="$HOME_DIR/projects/termux-assistant/widgets"
mkdir -p "$HOME_DIR/.shortcuts/tasks"
chmod 700 "$HOME_DIR/.shortcuts" "$HOME_DIR/.shortcuts/tasks"
n=0
for f in "$SRC"/*; do
  [ -f "$f" ] || continue
  b=$(basename "$f")
  chmod 755 "$f" 2>/dev/null || true
  ln -sfn "$f" "$HOME_DIR/.shortcuts/$b" && n=$((n+1))
done
am broadcast -n com.termux.widget/.TermuxWidgetProvider \
  -a com.termux.widget.ACTION_REFRESH_WIDGET --ei appWidgetId 0 >/dev/null 2>&1 || true
echo "atalhos: $n em ~/.shortcuts (refresh enviado)"
