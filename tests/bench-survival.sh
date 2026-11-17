#!/usr/bin/env bash
# Bateria final TAB — RAG generalista + SLM Gemma + gate. Nao apologiza; mede.
set -uo pipefail
R="$HOME/projects/termux-assistant/blackout/tab_rag.py"
LOG="${TA_BATTERY_LOG:-$HOME/.local/state/tab-battery-final-$(date +%Y%m%d-%H%M%S).txt}"
i=0; ok=0; duv=0
for q in \
 "como purificar agua em emergencia" \
 "o que fazer em queimadura" \
 "picada de cobra primeiro socorro" \
 "bebe engasgado o que fazer" \
 "parada cardiaca o que fazer" \
 "ferida sangrando muito"; do
  i=$((i+1)); T0=$(date +%s%3N)
  out=$(timeout 280 python3 "$R" "$q" 2>&1)
  T1=$(date +%s%3N)
  v=$(printf '%s' "$out" | grep -oE "VEREDITO: [A-Z]+" | tail -1 | cut -d' ' -f2)
  [ -z "$v" ] && v=SEM_VEREDITO
  case "$v" in CONFIAVEL|PARCIAL) ok=$((ok+1));; *) duv=$((duv+1));; esac
  printf 'CASO %d | %s | %sms | %s\n' "$i" "$q" "$((T1-T0))" "$v" | tee -a "$LOG"
  printf '%s\n' "$out" | head -5 | tee -a "$LOG"
  echo | tee -a "$LOG"
done
echo "RESUMO: $ok com veredito util / $duv duvidosos / total $i" | tee -a "$LOG"
echo "log=$LOG"
