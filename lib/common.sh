#!/data/data/com.termux/files/usr/bin/bash
# lib/common.sh - helpers compartilhados do termux-assistant
# Shell: bash. Uso: source "$(dirname "$0")/lib/common.sh"

# Não falha se o script for source'd fora de um contexto interativo.
[[ -n "${BASH_VERSION:-}" ]] || return 0

TA_CONFIG_DIR="${TA_CONFIG_DIR:-$HOME/.config/termux-assistant}"
TA_CONFIG_FILE="${TA_CONFIG_FILE:-$TA_CONFIG_DIR/config.env}"
TA_LOG_LEVEL="${TA_LOG_LEVEL:-info}"

# ---------- log ----------
_ta_level_num() {
  case "$1" in
    debug) echo 10 ;; info) echo 20 ;; warn) echo 30 ;; error) echo 40 ;;
    *) echo 20 ;;
  esac
}

ta_log() {
  local level="$1"; shift
  local want cur
  want=$(_ta_level_num "$level")
  cur=$(_ta_level_num "$TA_LOG_LEVEL")
  (( want < cur )) && return 0
  local ts; ts=$(date '+%H:%M:%S')
  case "$level" in
    debug) printf '\033[2m[%s] %s\033[0m\n' "$ts" "$*" >&2 ;;
    info)  printf '\033[36m[%s] %s\033[0m\n' "$ts" "$*" >&2 ;;
    warn)  printf '\033[33m[%s] AVISO: %s\033[0m\n' "$ts" "$*" >&2 ;;
    error) printf '\033[31m[%s] ERRO: %s\033[0m\n' "$ts" "$*" >&2 ;;
  esac
}

ta_die() { ta_log error "$*"; exit 1; }

ta_have() { command -v "$1" >/dev/null 2>&1; }

# ta_need <cmd> [mensagem]
ta_need() {
  ta_have "$1" && return 0
  ta_die "${2:-falta o comando '$1'}"
}

# ---------- config ----------
ta_load_config() {
  if [[ -f "$TA_CONFIG_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$TA_CONFIG_FILE"
    ta_log debug "config carregado de $TA_CONFIG_FILE"
  else
    ta_log warn "sem config em $TA_CONFIG_FILE (use o setup_bot.sh)"
  fi
  : "${TA_BACKEND:=opencode}"
  : "${TA_MODEL:=nvidia/minimaxai/minimax-m3.1-flash}"
  : "${TA_LANG:=pt-br}"
  : "${TA_STREAM:=false}"
  : "${TA_OPENAI_ENDPOINT:=http://127.0.0.1:8000/v1/chat/completions}"
  : "${TA_OLLAMA_HOST:=http://127.0.0.1:11434}"
  : "${TA_TIMEOUT:=120}"
  : "${TA_TTS:=true}"
  : "${TA_TTS_TRANSLATE:=true}"
}

ta_save_config() {
  mkdir -p "$TA_CONFIG_DIR"; chmod 700 "$TA_CONFIG_DIR"
  {
    echo "# termux-assistant - config gerado por setup_bot.sh"
    echo "TA_BACKEND=$TA_BACKEND"
    echo "TA_MODEL=$TA_MODEL"
    echo "TA_LANG=$TA_LANG"
    echo "TA_STREAM=$TA_STREAM"
    echo "TA_OPENAI_ENDPOINT=$TA_OPENAI_ENDPOINT"
    echo "TA_OLLAMA_HOST=$TA_OLLAMA_HOST"
    echo "TA_TIMEOUT=$TA_TIMEOUT"
    echo "TA_TTS=$TA_TTS"
    echo "TA_TTS_TRANSLATE=$TA_TTS_TRANSLATE"
  } > "$TA_CONFIG_FILE"
  chmod 600 "$TA_CONFIG_FILE"
  ta_log info "config salvo em $TA_CONFIG_FILE"
}

# ---------- Termux:API ----------
ta_toast() {
  ta_have termux-toast && termux-toast "${1:-}" >/dev/null 2>&1 || true
}

# ta_speak <texto> [lang]
# Regra do dono: o TTS e SEMPRE em portugues do Brasil. Se a resposta vier em
# outro idioma e o translate-shell estiver disponivel, ela e traduzida antes
# (TA_TTS_TRANSLATE=true). A voz nunca muda sozinha.
ta_speak() {
  local text="${1:-}" lang="${2:-$TA_LANG}"
  [[ -z "$text" || "$TA_TTS" != "true" ]] && return 0
  ta_have termux-tts-speak || return 0

  # traduz para pt-BR quando preciso (sem mudar a voz escolhida)
  if [[ "${TA_TTS_TRANSLATE:-true}" == "true" ]] && ta_have trans; then
    local detected; detected=$(ta_detect_lang "$text")
    if [[ "$detected" != "pt" && "$detected" != "pt-br" ]]; then
      local translated
      translated=$(trans -b -s "$detected" -t "$lang" "$text" 2>/dev/null || true)
      [[ -n "$translated" ]] && text="$translated"
    fi
  fi

  # remove pontuacao que faz o TTS engasgar e emojis
  text="${text//$'\n'/ }"
  text=$(printf '%s' "$text" | sed 's/[.,!?;:]/ /g; s/  */ /g; s/^ *//; s/ *$//')
  [[ -z "$text" ]] && return 0
  termux-tts-speak -l "$lang" "$text" >/dev/null 2>&1 || true
}

# Detecta o idioma e devolve o codigo curto (pt, en, es...) sem ':' nem sufixo.
ta_detect_lang() {
  local text="${1:-}" out=""
  ta_have trans || { echo "$TA_LANG"; return 0; }
  out=$(trans -b -identify "$text" 2>/dev/null | head -1 | cut -d: -f1 | cut -d' ' -f1)
  out="${out%%:*}"
  [[ -n "$out" ]] && echo "$out" || echo "$TA_LANG"
}

# Divide texto em frases (para falar por frase, e nao por palavra).
ta_sentences() {
  printf '%s' "${1:-}" | sed 's/[.!?]\+/\n/g' | sed 's/^[[:space:]]*//; s/[[:space:]]*$//' | grep -v '^$'
}

# ---------- backends ----------
# opencode: usa o proprio OpenCode do aparelho (mesmo modelo/sessao do agente).
# A saida de `opencode run --format json` e JSONL: um objeto por linha, e o texto
# vem em .part.text das linhas com .type == "text".
ta_opencode_generate() {
  local prompt="$1" model="${2:-$TA_MODEL}"
  ta_need opencode "OpenCode nao encontrado (instale ou use --backend openai)"
  # Roda num diretorio NEUTRO: se o cwd estiver sob a home, o OpenCode carrega o
  # AGENTS.md (36 KB aqui) em cada sessao -> ~17s em vez de ~5s por resposta.
  local rundir="${TA_RUN_DIR:-${TMPDIR:-$PREFIX/tmp/opencode}/assistant-run}"
  mkdir -p "$rundir" 2>/dev/null || true
  local out
  out=$(cd "$rundir" 2>/dev/null && opencode run --format json --model "$model" "$prompt" 2>/dev/null)
  [[ -z "$out" ]] && return 0
  if ta_have jq; then
    printf '%s\n' "$out" | jq -r 'select(.type == "text") | .part.text // empty' 2>/dev/null
    return 0
  fi
  printf '%s\n' "$out" | sed -n 's/.*"text"[[:space:]]*:[[:space:]]*"\(.*\)".*/\1/p'
}

# openai: qualquer endpoint OpenAI-compatible (OpenRouter, NIM, llama.cpp...).
ta_openai_generate() {
  local prompt="$1" model="${2:-gpt-4o-mini}"
  local key="${OPENAI_API_KEY:-}"
  [[ -n "$key" ]] || ta_die "OPENAI_API_KEY nao definido (use --backend opencode ou exporte a chave)"
  local payload
  payload=$(jq -nc --arg m "$model" --arg p "$prompt" \
    '{model:$m, messages:[{role:"user",content:$p}], stream:false}')
  curl -fsS --max-time "$TA_TIMEOUT" "$TA_OPENAI_ENDPOINT" \
    -H "Content-Type: application/json" -H "Authorization: Bearer $key" \
    -d "$payload" | jq -r '.choices[0].message.content // .choices[0].text // empty'
}

# ollama: local (proot-distro/Arch ou host).
ta_ollama_generate() {
  local prompt="$1" model="${2:-tinydolphin:latest}"
  local payload
  payload=$(jq -nc --arg m "$model" --arg p "$prompt" '{model:$m,prompt:$p,stream:false}')
  curl -fsS --max-time "$TA_TIMEOUT" "$TA_OLLAMA_HOST/api/generate" -d "$payload" \
    | jq -r '.response // empty'
}

# ta_generate <prompt> [model] -> texto
ta_generate() {
  local prompt="$1" model="${2:-$TA_MODEL}"
  case "$TA_BACKEND" in
    opencode) ta_opencode_generate "$prompt" "$model" ;;
    openai)   ta_openai_generate  "$prompt" "$model" ;;
    ollama)   ta_ollama_generate  "$prompt" "$model" ;;
    *)        ta_die "backend desconhecido: $TA_BACKEND (opencode|openai|ollama)" ;;
  esac
}
