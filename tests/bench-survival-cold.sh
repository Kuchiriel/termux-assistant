#!/usr/bin/env bash
# Bateria FRIA: 6 casos pendentes, 1 por vez, pausa longa entre eles.
set -uo pipefail
R="$HOME/projects/termux-assistant/blackout/tab_rag.py"
LOG="${TA_BATTERY_LOG:-$HOME/.local/state/tab-battery-cold-$(date +%Y%m%d-%H%M%S).txt}"
i=0; conf=0; duv=0
for q in \
 "afogamento primeiros socorros" \
 "choque eletrico o que fazer" \
 "insolacao calor extremo o que fazer" \
 "fratura perna o que fazer" \
 "envenenamento por comida o que fazer" \
 "convulsao o que fazer"; do
  i=$((i+1))
  # espera ate a temperatura baixar de 44C (no max 5 min) — sem llama paralelo
  for w in $(seq 1 15); do
    T=$(termux-battery-status 2>/dev/null | python3 -c 'import json,sys
try: print(float(json.load(sys.stdin).get("temperature",0)))
except Exception: print(0)')
    awk -v t="$T" 'BEGIN{exit !(t<44)}' && break
    sleep 20
  done
  T0=$(date +%s%3N)
  out=$(TA_SLM_N=140 timeout 240 python3 "$R" "$q" 2>&1)
  T1=$(date +%s%3N)
  TE=$(termux-battery-status 2>/dev/null | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("temperature"))
except Exception: print("?")')
  v=$(printf '%s' "$out" | grep -oE 'VEREDITO: [A-Z]+' | tail -1 | awk '{print $2}')
  [ -z "$v" ] && v=SEM_VEREDITO
  case "$v" in CONFIAVEL|PARCIAL) conf=$((conf+1));; *) duv=$((duv+1));; esac
  printf 'CASO %d | %s | %sms | %s | %sC\n' "$i" "$q" "$((T1-T0))" "$v" "$TE" >> "$LOG"
  printf '%s\n' "$out" | grep -E '^[0-9]\.|F[0-9] |SEM FONTE' | head -4 >> "$LOG"
  echo >> "$LOG"
  sleep 30
done
echo "RESUMO uteis=$conf duvidosos=$duv total=$i" >> "$LOG"
