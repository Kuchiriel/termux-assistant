#!/usr/bin/env bash
# Bateria do modo RAPIDO (sem SLM): latencia e cobertura dos 12 dominios.
set -uo pipefail
R="$HOME/projects/termux-assistant/blackout/tab_rag.py"
LOG="${TA_BATTERY_LOG:-$HOME/.local/state/tab-fast-$(date +%Y%m%d-%H%M%S).txt}"
i=0; ok=0; sem=0
for q in \
 "como purificar agua em emergencia" "o que fazer em queimadura" "picada de cobra primeiro socorro" \
 "bebe engasgado o que fazer" "parada cardiaca o que fazer" "ferida sangrando muito" \
 "afogamento primeiros socorros" "choque eletrico o que fazer" "insolacao calor extremo o que fazer" \
 "fratura perna o que fazer" "envenenamento por comida o que fazer" "convulsao o que fazer"; do
  i=$((i+1)); T0=$(date +%s%3N)
  out=$(TA_SLM_OFF=1 timeout 20 python3 "$R" "$q" 2>&1)
  T1=$(date +%s%3N)
  v=$(printf '%s' "$out" | grep -oE 'VEREDITO: [A-Z]+' | tail -1 | awk '{print $2}')
  [ -z "$v" ] && v=SEM_VEREDITO
  case "$v" in CONFIAVEL) ok=$((ok+1));; *) sem=$((sem+1));; esac
  printf 'CASO %02d | %-38s | %5sms | %s\n' "$i" "$q" "$((T1-T0))" "$v" >> "$LOG"
done
echo "RESUMO ok=$ok sem_regra=$sem total=$i" >> "$LOG"
cat "$LOG"
