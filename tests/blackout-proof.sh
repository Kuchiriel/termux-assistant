#!/usr/bin/env bash
# Prova de BLACKOUT: rede morta (proxy sem destino) e TAB ainda responde.
set -uo pipefail
R="$HOME/projects/termux-assistant/blackout/tab_rag.py"
DEAD="http://127.0.0.1:9"
echo "=== 1) a rede esta mesmo morta no processo?"
env https_proxy=$DEAD http_proxy=$DEAD all_proxy=$DEAD \
  timeout 8 curl -s -o /dev/null -w "curl_externo=%{http_code} (000 = sem saida)\n" https://api.ipify.org 2>/dev/null
echo "=== 2) TAB (modo rapido, sem SLM) ainda responde?"
T0=$(date +%s%3N)
env https_proxy=$DEAD http_proxy=$DEAD all_proxy=$DEAD TA_SLM_OFF=1 \
  timeout 20 python3 "$R" "como purificar agua em emergencia" 2>&1 | head -5
T1=$(date +%s%3N)
echo "latencia=$((T1-T0))ms"
echo "=== 3) TAB com SLM (Gemma local) tambem funciona offline?"
T0=$(date +%s%3N)
env https_proxy=$DEAD http_proxy=$DEAD all_proxy=$DEAD \
  timeout 240 python3 "$R" "convulsao o que fazer" 2>&1 | grep -E "^[0-9]+\.|VEREDITO" | head -3
T1=$(date +%s%3N)
echo "latencia=$((T1-T0))ms"
echo "=== 4) o que NAO funciona sem rede (honesto)"
env https_proxy=$DEAD http_proxy=$DEAD all_proxy=$DEAD \
  timeout 20 python3 "$HOME/projects/termux-assistant/blackout/tab_translate.py" \
  "For a choking infant, perform 3-4 back slaps between the shoulder blades." 2>&1 | head -2
