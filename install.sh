#!/usr/bin/env bash
# termux-assistant — instalador idempotente (um comando).
#
#   curl -fsSL https://raw.githubusercontent.com/Kuchiriel/termux-assistant/main/install.sh -o /tmp/ta-install.sh
#   bash /tmp/ta-install.sh --dry-run
#   bash /tmp/ta-install.sh
#
# Nunca sobrescreve arquivo do usuario sem backup; nunca grava segredo.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="${HOME:-/data/data/com.termux/files/home}"
TA_DIR="$HOME_DIR/.local/share/termux-assistant"
CFG_DIR="$HOME_DIR/.config/termux-assistant"
BIN_DIR="$HOME_DIR/bin"
SHORTCUTS="$HOME_DIR/.shortcuts"
SKILLS="$HOME_DIR/.config/opencode/skills"
PLUGINS="$HOME_DIR/.config/opencode/plugins"
LOG="$HOME_DIR/.local/state/termux-assistant-install.log"
DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1

say() { printf '%s %s\n' "$(date '+%H:%M:%S')" "$*" | tee -a "$LOG" 2>/dev/null || printf '%s\n' "$*"; }
inst() {
  local src="$1" dst="$2" mode="${3:-644}"
  [ -f "$src" ] || { say "FALTA $src"; return 1; }
  if [ "$DRY" = "1" ]; then printf 'dry-run: %s -> %s\n' "$src" "$dst"; return 0; fi
  mkdir -p "$(dirname "$dst")"
  if [ -e "$dst" ] && ! cmp -s "$src" "$dst"; then
    cp -p "$dst" "$dst.ta-backup-$(date +%Y%m%d%H%M%S)" 2>/dev/null || true
  fi
  cp "$src" "$dst" && chmod "$mode" "$dst"
}
link_shortcut() {
  local wname="${1:-}"
  [ -z "$wname" ] && return 0
  local src="$TA_DIR/widgets/$wname" dst="$SHORTCUTS/$wname"
  if [ "$DRY" = "1" ]; then printf 'dry-run atalho: %s\n' "$dst"; return 0; fi
  mkdir -p "$SHORTCUTS/tasks"; chmod 700 "$SHORTCUTS" "$SHORTCUTS/tasks"
  # Termux:Widget ignora symlinks para fora de ~/.shortcuts — copia arquivo real.
  [ -L "$dst" ] && mv "$dst" "$dst.ta-symlink" 2>/dev/null || true
  cp "$src" "$dst" 2>/dev/null && chmod 755 "$dst"
}

say "instalando termux-assistant de $REPO (dry=$DRY)"

# 1) biblioteca e binarios
inst "$REPO/ta.py" "$TA_DIR/ta.py" 755
for f in "$REPO"/lib/*; do [ -f "$f" ] && inst "$f" "$TA_DIR/lib/$(basename "$f")" 644; done
for f in "$REPO"/bin/*; do [ -f "$f" ] && inst "$f" "$BIN_DIR/$(basename "$f")" 755; done
inst "$REPO/ta.py" "$BIN_DIR/ta" 755

# 2) config: so exemplo; .env real nunca e' sobrescrito
inst "$REPO/.env.example" "$CFG_DIR/.env.example" 600
if [ "$DRY" = "0" ] && [ ! -e "$CFG_DIR/.env" ]; then
  cp "$CFG_DIR/.env.example" "$CFG_DIR/.env"; chmod 600 "$CFG_DIR/.env"
  say "criei $CFG_DIR/.env (sem segredos)"
fi

# 3) skills e plugins
for d in "$REPO"/skills/*/; do
  [ -f "$d/SKILL.md" ] || continue
  n=$(basename "$d"); mkdir -p "$SKILLS/$n" 2>/dev/null
  inst "$d/SKILL.md" "$SKILLS/$n/SKILL.md" 644
done
for f in "$REPO"/plugins/*; do [ -f "$f" ] && inst "$f" "$PLUGINS/$(basename "$f")" 644; done

# 4) ponteiros AGENTS (sem apagar o AGENTS existente)
if [ "$DRY" = "0" ]; then
  for target in "$HOME_DIR/AGENTS.md" "$HOME_DIR/.config/opencode/AGENTS.md"; do
    mkdir -p "$(dirname "$target")"
    if [ ! -e "$target" ]; then
      cp "$REPO/config/opencode/AGENTS.termux.md" "$target"
    elif ! grep -q "termux-assistant" "$target"; then
      printf '\n## termux-assistant\n\nLeia `%s` e use `ta status` / `ta doctor`.\n' "$REPO/README.md" >> "$target"
    fi
  done
fi

# 5) widgets no diretorio canonico do Termux:Widget
for f in "$REPO"/widgets/*; do
  [ -f "$f" ] || continue
  n=$(basename "$f")
  inst "$f" "$TA_DIR/widgets/$n" 755
  link_shortcut "$n"
done

# 6) refresh (versao >= 0.13; id 0 = todos)
if [ "$DRY" = "0" ] && [ "${TA_AUTO_REFRESH_WIDGETS:-1}" = "1" ]; then
  am broadcast -n com.termux.widget/.TermuxWidgetProvider \
    -a com.termux.widget.ACTION_REFRESH_WIDGET --ei appWidgetId 0 >/dev/null 2>&1 || true
fi

say "concluido. Use: ta doctor && ta status"
