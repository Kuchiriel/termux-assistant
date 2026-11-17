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
  # Termux:Widget nao mostra symlinks cujo alvo esta fora de ~/.shortcuts
  # ou ~/.termux (README oficial). Copia arquivo REAL, nunca link.
  if [ -L "$HOME_DIR/.shortcuts/$b" ]; then
    Q="$HOME_DIR/.local/state/termux-assistant/shortcut-symlinks-$(date +%Y%m%d%H%M%S)"
    mkdir -p "$Q"; mv "$HOME_DIR/.shortcuts/$b" "$Q/$b" 2>/dev/null || true
  fi
  cp "$f" "$HOME_DIR/.shortcuts/$b" && chmod 755 "$HOME_DIR/.shortcuts/$b" && n=$((n+1))
done
am broadcast -n com.termux.widget/.TermuxWidgetProvider \
  -a com.termux.widget.ACTION_REFRESH_WIDGET --ei appWidgetId 0 >/dev/null 2>&1 || true
echo "atalhos: $n em ~/.shortcuts (refresh enviado)"
