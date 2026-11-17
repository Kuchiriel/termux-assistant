#!/usr/bin/env bash
# Bateria ampliada TAB — 12 emergencias, veredito + latencia, log incremental.
set -uo pipefail
R="$HOME/projects/termux-assistant/blackout/tab_rag.py"
LOG="${TA_BATTERY_LOG:-$HOME/.local/state/tab-battery-12cool-$(date +%Y%m%d-%H%M%S).txt}"
i=0; conf=0; parcial=0; duv=0
while IFS='|' read -r q; do
  [ -z "$q" ] && continue
  i=$((i+1)); T0=$(date +%s%3N)
  out=$(TA_SLM_N=140 timeout 200 python3 "$R" "$q" 2>&1)
  sleep 20  # pausa termica
  T1=$(date +%s%3N)
  v=$(printf '%s' "$out" | grep -oE 'VEREDITO: [A-Z]+' | tail -1 | awk '{print $2}')
  [ -z "$v" ] && v=SEM_VEREDITO
  case "$v" in CONFIAVEL) conf=$((conf+1));; PARCIAL) parcial=$((parcial+1));; *) duv=$((duv+1));; esac
  printf 'CASO %02d | %s | %sms | %s\n' "$i" "$q" "$((T1-T0))" "$v" | tee -a "$LOG"
  printf '%s\n' "$out" | grep -E '^[0-9]\.|F[0-9] |SEM FONTE' | head -4 | tee -a "$LOG"
  echo >> "$LOG"
done <<'CASES'
como purificar agua em emergencia
o que fazer em queimadura
picada de cobra primeiro socorro
bebe engasgado o que fazer
parada cardiaca o que fazer
ferida sangrando muito
afogamento primeiros socorros
choque eletrico o que fazer
insolacao calor extremo o que fazer
fratura perna o que fazer
envenenamento por comida o que fazer
convulsao o que fazer
CASES
echo "RESUMO conf=$conf parcial=$parcial duvidoso=$duv total=$i" | tee -a "$LOG"
echo "log=$LOG"
