#!/data/data/com.termux/files/usr/bin/bash
# termux_bot.sh - assistente de voz/comandos do Termux.
#
# Como usar:
#   ./termux_bot.sh "acende a lanterna"          # um comando, responde e sai
#   ./termux_bot.sh --interactive                 # dialogo por voz (Termux:API)
#   ./termux_bot.sh --backend opencode --model X "..."
#   ./termux_bot.sh --stream "..."               # fala por sentenca enquanto gera
#
# Saida: texto da resposta no stdout (util para pipe); toasts/TTS sao opcionais.

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "$HERE/lib/common.sh"

ONCE=0
INTERACTIVE=0
STREAM=0
QUIET=0
TEXT=""

usage() {
  cat <<'EOF'
termux_bot.sh - assistente Termux (comandos locais + LLM)

USO
  ./termux_bot.sh [opcoes] ["texto do comando"]

OPCOES
  --interactive        abre o dialogo de voz (termux-dialog) e repete ate "sair"
  --once               processa o texto informado e sai (padrao se ha texto)
  --backend <b>       opencode (padrao) | openai | ollama
  --model <m>         modelo do backend
  --lang <l>          idioma do TTS (padrao: pt-br)
  --stream            fala por sentenca enquanto a resposta e gerada
  --no-tts            desliga a fala (mantem o toast)
  --quiet             nao imprime logs (so a resposta no stdout)
  -h, --help          esta ajuda

EXEMPLOS
  ./termux_bot.sh "qual a temperatura da bateria?"
  ./termux_bot.sh --backend opencode --model nvidia/minimaxai/minimax-m3.1-flash "explique o tunel SSL"
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --interactive) INTERACTIVE=1; shift ;;
    --once) ONCE=1; shift ;;
    --backend) TA_BACKEND="${2:-}"; shift 2 ;;
    --model) TA_MODEL="${2:-}"; shift 2 ;;
    --lang) TA_LANG="${2:-}"; shift 2 ;;
    --stream) STREAM=1; TA_STREAM=true; shift ;;
    --no-tts) TA_TTS=false; shift ;;
    --quiet) QUIET=1; TA_LOG_LEVEL=error; shift ;;
    -h|--help) usage; exit 0 ;;
    --) shift; TEXT="$*"; break ;;
    -*) ta_log warn "opcao desconhecida: $1"; shift ;;
    *) TEXT="${TEXT:+$TEXT }$1"; shift ;;
  esac
done

ta_load_config
(( QUIET )) && TA_LOG_LEVEL=error
[[ -n "${TA_OPENAI_API_KEY:-}" ]] && export OPENAI_API_KEY="$TA_OPENAI_API_KEY"

# ---------- comandos locais ----------
local_ip() {
  ip -4 -o addr show scope global 2>/dev/null | awk '{split($4,a,"/"); print a[1]}' | head -1
}

public_ip() {
  # usa ipify (nao ifconfig.co) e nao vaza nada se o Tor estiver ativo
  curl -fsS --max-time 12 https://api.ipify.org 2>/dev/null || echo "desconhecido"
}

cmd_battery() {
  local st; st=$(termux-battery-status 2>/dev/null)
  if [[ -z "$st" ]]; then echo "nao consegui ler a bateria"; return; fi
  if ta_have jq; then
    jq -r '"nivel \(.percentage)% | saude \(.health) | \(.plugged) | \(.temperature)C"' <<<"$st"
  else
    echo "$st"
  fi
}

cmd_notifications() {
  local n; n=$(termux-notification-list 2>/dev/null)
  [[ -z "$n" ]] && { echo "nenhuma notificacao"; return; }
  if ta_have jq; then
    local count; count=$(jq 'length' <<<"$n" 2>/dev/null || echo 0)
    echo "$count notificacao(oes):"
    jq -r '.[0:5][] | "  - \(.title // "sem titulo"): \((.content // "")[0:60])"' <<<"$n" 2>/dev/null
  else
    echo "$n"
  fi
}

cmd_location() {
  local loc
  loc=$(timeout 25 termux-location -a 2>/dev/null || true)
  [[ -z "$loc" ]] && { echo "nao consegui obter a localizacao (sem permissao ou sem GPS)"; return; }
  if ta_have jq; then
    local lat lon acc addr
    lat=$(jq -r '.latitude' <<<"$loc" 2>/dev/null)
    lon=$(jq -r '.longitude' <<<"$loc" 2>/dev/null)
    acc=$(jq -r '.accuracy' <<<"$loc" 2>/dev/null)
    addr=$(curl -fsS --max-time 12 -A "termux-assistant" \
      "https://nominatim.openstreetmap.org/reverse?lat=$lat&lon=$lon&format=json" 2>/dev/null \
      | jq -r '[.address.road, .address.suburb, .address.city, .address.state] | map(select(. != null)) | join(", ")' 2>/dev/null)
    echo "você está em ${addr:-lat $lat, lon $lon} (precisão ${acc:-?})"
  else
    echo "$loc"
  fi
}

# run_local <texto> -> imprime a resposta local e retorna 0 se tratou
run_local() {
  local speech="$1"
  case "${speech,,}" in
    *lanterna*|*torch*|*flashlight*)
      if [[ "${speech,,}" =~ (off|desliga|apaga|desligar) ]]; then termux-torch off 2>/dev/null; echo "lanterna desligada";
      else termux-torch on 2>/dev/null; echo "lanterna ligada"; fi
      return 0 ;;
    *volume*)
      # a API do Termux exige NUMERO: le o atual, soma/subtrai e grava.
      local cur new
      cur=$(termux-volume 2>/dev/null | jq -r '[.[] | select(.stream == "music") | .volume][0] // 0' 2>/dev/null || echo 0)
      [[ "$cur" =~ ^[0-9]+$ ]] || cur=0
      if [[ "${speech,,}" =~ (aumenta|sobe|mais|up|raise|cima) ]]; then
        new=$((cur + 1)); [[ $new -gt 15 ]] && new=15
      elif [[ "${speech,,}" =~ (diminui|baixa|menos|down|lower|abaixo) ]]; then
        new=$((cur - 1)); [[ $new -lt 0 ]] && new=0
      else
        echo "quer aumentar ou diminuir o volume?"; return 0
      fi
      termux-volume music "$new" >/dev/null 2>&1
      echo "volume da mídia: $new"
      return 0 ;;
    *bateria*|*battery*)
      cmd_battery; return 0 ;;
    *notifica*)
      cmd_notifications; return 0 ;;
    *localiza*|*"onde eu"*|*location*)
      cmd_location; return 0 ;;
    *"meu ip"*|*"ip local"*|*"ip publico"*|*"endereco ip"*)
      if [[ "${speech,,}" =~ (local|priv) ]]; then echo "seu IP local e $(local_ip)";
      elif [[ "${speech,,}" =~ (public|global|externo) ]]; then echo "seu IP publico e $(public_ip)";
      else echo "IP local: $(local_ip) | IP publico: $(public_ip)"; fi
      return 0 ;;
    *toast*)
      local msg="${speech#*toast }"
      ta_toast "$msg"; echo "toast: $msg"; return 0 ;;
    *copi*|*clipboard*)
      local msg="${speech#*copi }"
      termux-clipboard-set "$msg" 2>/dev/null && echo "copiei para a area de transferencia: $msg"; return 0 ;;
    *vibr*)
      termux-vibrate -d 1000 2>/dev/null; echo "vibrando"; return 0 ;;
    *sair*|*tchau*|*bye*|*exit*)
      echo "ate mais"; return 0 ;;
  esac
  return 1
}

# ---------- geracao ----------
ask_llm() {
  local prompt="$1" out=""
  if (( STREAM )); then
    # fala por sentenca: divide em pedacos e fala cada um (nada de toast por palavra)
    out=$(ta_generate "$prompt")
    local acc=""
    while IFS= read -r s; do
      acc="$acc $s"
      local full; full=$(printf '%s' "$acc" | tr '\n' ' ')
      if [[ ${#full} -ge 120 || "$s" =~ [.!?]$ ]]; then
        ta_toast "$full"; ta_speak "$full"; acc=""
      fi
    done < <(ta_sentences "$out")
    [[ -n "$acc" ]] && { ta_toast "$acc"; ta_speak "$acc"; }
  else
    out=$(ta_generate "$prompt")
  fi
  [[ -z "$out" ]] && out="(sem resposta do backend $TA_BACKEND)"
  printf '%s\n' "$out"
}

handle() {
  local speech="$1"
  [[ -z "${speech// }" ]] && { echo "nao entendi"; return; }
  local resp
  if resp=$(run_local "$speech"); then
    printf '%s\n' "$resp"
    ta_toast "$(printf '%s' "$resp" | head -c 200)"
    ta_speak "$resp"
    return
  fi
  local system="Voce e um assistente no Termux, em um celular Android. Responda em portugues do Brasil, de forma curta e direta (maximo 3 frases), sem markdown."
  resp=$(ask_llm "$system

Usuario: $speech")
  printf '%s\n' "$resp"
  ta_toast "$(printf '%s' "$resp" | head -c 200)"
  ta_speak "$resp"
}

# ---------- modos ----------
if (( INTERACTIVE )); then
  ta_need termux-dialog "Termux:API nao instalado (pkg install termux-api)"
  title="Assistente Termux"
  hint="Como posso ajudar?"
  ta_speak "$hint"
  while true; do
    raw=$(termux-dialog speech -i "$hint" -t "$title" 2>/dev/null)
    speech=$(ta_have jq && jq -r '.text // empty' <<<"$raw" 2>/dev/null || echo "$raw")
    [[ -z "$speech" ]] && break
    handle "$speech"
    case "${speech,,}" in
      *sair*|*tchau*|*bye*|*exit*) break ;;
    esac
  done
  exit 0
fi

if [[ -z "$TEXT" ]]; then
  usage
  exit 2
fi

handle "$TEXT"
