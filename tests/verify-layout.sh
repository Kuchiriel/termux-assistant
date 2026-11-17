#!/usr/bin/env bash
# Prova de layout para update/uninstall/install — nao destrui nada.
set -uo pipefail
HOME_DIR="${HOME:-/data/data/com.termux/files/home}"
FALHAS=0
check() { [ -e "$2" ] && printf 'OK   %s\n' "$1" || { printf 'FALTA %s (%s)\n' "$1" "$2"; FALHAS=$((FALHAS+1)); }; }
check home "$HOME_DIR"
check bin "$HOME_DIR/bin"
check shortcuts "$HOME_DIR/.shortcuts"
check termux-widget "$HOME_DIR/.termux/widget"
check opencode-config "$HOME_DIR/.config/opencode"
check offline-corpus "$HOME_DIR/offline-corpus"
check env-example "$HOME_DIR/.config/termux-assistant/.env.example"
check ta-cli "$HOME_DIR/bin/ta"
atalhos=$(find "$HOME_DIR/.shortcuts" -maxdepth 1 -type l 2>/dev/null | wc -l | tr -d ' ')
printf 'atalhos em ~/.shortcuts: %s\n' "$atalhos"
[ "$atalhos" -ge 5 ] || FALHAS=$((FALHAS+1))
# segredo: so caminhos no .env
if [ -f "$HOME_DIR/.config/termux-assistant/.env" ]; then
  if grep -qE '(nvapi-|hf_[A-Za-z0-9]{20}|sk-[A-Za-z0-9]{20})' "$HOME_DIR/.config/termux-assistant/.env"; then
    echo 'ERRO: .env com valor de segredo'; FALHAS=$((FALHAS+1))
  else echo 'OK   .env sem valores de segredo'; fi
fi
backups=$(find "${TA_BACKUP_DIR:-$HOME_DIR/storage/shared/termux-assistant/backups}" -name '*.tar.gz' 2>/dev/null | wc -l | tr -d ' ')
printf 'backups locais: %s\n' "$backups"
echo "falhas=$FALHAS"
[ "$FALHAS" -eq 0 ]
