#!/data/data/com.termux/files/usr/bin/bash
# setup_bot.sh - instala e configura o termux-assistant no Termux.
#
# Idempotente: pode rodar quantas vezes quiser. Nao roda nada destrutivo.
#
#   ./setup_bot.sh                       # detecta e instala o que falta
#   ./setup_bot.sh --backend opencode    # backend: opencode (padrao) | openai | ollama
#   ./setup_bot.sh --model <modelo>      # modelo do backend
#   ./setup_bot.sh --dry-run             # so mostra o que faria
#   ./setup_bot.sh --uninstall-ollama    # nao instala/remove o proot+ollama

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "$HERE/lib/common.sh"

BACKEND="opencode"
MODEL="nvidia/minimaxai/minimax-m3.1-flash"
LANG_TTS="pt-br"
DRY_RUN=0
WANT_OLLAMA=auto     # auto | yes | no

usage() {
  cat <<'EOF'
setup_bot.sh - instala/configura o termux-assistant (Termux:API + backends de LLM)

USO
  ./setup_bot.sh [opcoes]

OPCOES
  --backend <b>    opencode (padrao) | openai | ollama
  --model <m>      modelo do backend (ex.: nvidia/minimaxai/minimax-m3.1-flash)
  --lang <l>       idioma do TTS (padrao: pt-br)
  --dry-run        nao executa, so mostra o plano
  --no-ollama      nao instala proot-distro/Arch/Ollama
  --with-ollama    forca a instalacao do Ollama em proot-distro
  -h, --help       esta ajuda

EXEMPLOS
  ./setup_bot.sh
  ./setup_bot.sh --backend opencode --model nvidia/minimaxai/minimax-m3.1-flash
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --backend) BACKEND="${2:-}"; shift 2 ;;
    --model) MODEL="${2:-}"; shift 2 ;;
    --lang) LANG_TTS="${2:-}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --no-ollama) WANT_OLLAMA=no; shift ;;
    --with-ollama) WANT_OLLAMA=yes; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "opcao desconhecida: $1" >&2; usage; exit 2 ;;
  esac
done

run() {  # executa (ou mostra, em dry-run)
  if (( DRY_RUN )); then printf '\033[2m[dry-run]\033[0m %s\n' "$*"; else "$@"; fi
}

need_pkg() {  # need_pkg <pacote> [descricao]
  local pkg="$1" desc="${2:-}"
  if pkg list-installed 2>/dev/null | grep -q "^$pkg/"; then
    ta_log info "ok: $pkg ja instalado"
    return 0
  fi
  ta_log warn "instalando $pkg ${desc:+($desc)}"
  run pkg install -y "$pkg"
}

# ---------- 0. Termux:API (obrigatorio) ----------
need_pkg termux-api "Termux:API (toast, tts, dialog, bateria...)"
need_pkg jq
need_pkg curl
need_pkg translate-shell "translate-shell (detecao de idioma; comando 'trans')"
need_pkg termux-api 2>/dev/null || true

# ---------- 1. armazenamento compartilhado ----------
if [[ ! -d "$HOME/storage" ]]; then
  ta_log warn "sem acesso ao armazenamento compartilhado."
  ta_log warn "Rode: termux-setup-storage  (autorize na dialogo do Android) e depois repita este script."
else
  ta_log info "armazenamento compartilhado: ok"
fi

# ---------- 2. backend ----------
case "$BACKEND" in
  opencode)
    if ta_have opencode; then
      ta_log info "backend opencode: $(opencode --version 2>/dev/null | head -1)"
      if ! opencode models 2>/dev/null | grep -q .; then
        ta_log warn "opencode nao listou modelos. Se a lista vier vazia, configure a credencial do provider."
      fi
    else
      ta_log warn "backend opencode pedido, mas o binario 'opencode' nao esta no PATH."
      ta_log warn "Instalacao no Termux: pkg install opencode  (ou use o pacote custom v2.2.5-android-termux)."
    fi
    ;;
  openai)
    if [[ -z "${OPENAI_API_KEY:-}" ]]; then
      ta_log warn "backend openai sem OPENAI_API_KEY no ambiente."
      ta_log warn "exporte OPENAI_API_KEY=... (ou use ~/.config/termux-assistant/config.env)"
    fi
    ;;
  ollama)
    WANT_OLLAMA=yes
    ;;
  *) ta_die "backend invalido: $BACKEND" ;;
esac

# ---------- 3. Ollama opcional (proot-distro + Arch) ----------
setup_ollama() {
  need_pkg proot-distro
  if ! proot-distro list 2>/dev/null | grep -q '^archlinux'; then
    ta_log info "instalando distro archlinux no proot-distro"
    run proot-distro install archlinux
  fi
  if ! proot-distro login archlinux -- true >/dev/null 2>&1; then
    ta_die "proot-distro archlinux nao inicializou"
  fi
  if ! proot-distro login archlinux -- sh -lc 'command -v ollama' >/dev/null 2>&1; then
    ta_log info "instalando ollama dentro do archlinux"
    run proot-distro login archlinux -- bash -lc \
      'curl -fsSL https://ollama.com/install.sh | sh'
  fi
  ta_log info "ollama pronto (modelo padrao: tinydolphin:latest)"
  local m="tinydolphin:latest"
  if ! proot-distro login archlinux -- ollama list 2>/dev/null | grep -q "$m"; then
    ta_log info "baixando modelo $m (pode demorar)"
    run proot-distro login archlinux -- ollama pull "$m"
  fi
}

if [[ "$WANT_OLLAMA" == yes ]]; then
  setup_ollama
elif [[ "$WANT_OLLAMA" == auto && "$BACKEND" == ollama ]]; then
  setup_ollama
fi

# ---------- 4. config ----------
export TA_BACKEND="$BACKEND" TA_MODEL="$MODEL" TA_LANG="$LANG_TTS"
export TA_STREAM=false TA_TIMEOUT=120 TA_TTS=true TA_TTS_TRANSLATE=true
export TA_OPENAI_ENDPOINT="${TA_OPENAI_ENDPOINT:-http://127.0.0.1:8000/v1/chat/completions}"
export TA_OLLAMA_HOST="${TA_OLLAMA_HOST:-http://127.0.0.1:11434}"
if (( DRY_RUN )); then
  ta_log info "[dry-run] nao gravando config em $TA_CONFIG_FILE"
else
  ta_save_config
fi

# ---------- 5. atalhos ----------
if (( ! DRY_RUN )); then
  mkdir -p "$HOME/bin" "$HOME/.shortcuts"
  cat > "$HOME/bin/assistant" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec "$HERE/termux_bot.sh" "\$@"
EOF
  chmod +x "$HOME/bin/assistant"

  cat > "$HOME/.shortcuts/Assistente Termux.sh" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
# Atalho do Termux:API -> assistant
export PATH="\$PATH:\$HOME/bin"
exec "$HERE/termux_bot.sh" --interactive
EOF
  chmod +x "$HOME/.shortcuts/Assistente Termux.sh"
  ta_log info "atalhos: ~/bin/assistant e ~/.shortcuts/Assistente Termux.sh"
fi

# ---------- 6. health check ----------
ta_log info "verificando o backend $BACKEND ..."
case "$BACKEND" in
  opencode)
    if ta_have opencode; then
      n=$(opencode models 2>/dev/null | wc -l)
      ta_log info "opencode: $n modelos disponiveis"
    else
      ta_log warn "opencode ausente"
    fi
    ;;
  ollama)
    if curl -fsS --max-time 3 "$TA_OLLAMA_HOST/api/tags" >/dev/null 2>&1; then
      ta_log info "ollama: respondendo em $TA_OLLAMA_HOST"
    else
      ta_log warn "ollama nao responde em $TA_OLLAMA_HOST"
    fi
    ;;
  openai)
    ta_log info "openai: usando $TA_OPENAI_ENDPOINT"
    ;;
esac

# checagem da voz pt-BR (o TTS e sempre em portugues do Brasil)
if ta_have termux-tts-speak; then
  if timeout 12 termux-tts-speak -l "$LANG_TTS" "ok" >/dev/null 2>&1; then
    ta_log info "voz TTS '$LANG_TTS' disponivel"
  else
    ta_log warn "a voz TTS '$LANG_TTS' nao respondeu. No Android: Ajustes > Sistema > Idiomas e entrada > Saida de texto para voz, e baixe a voz em portugues (Brasil)."
  fi
fi

ta_log info "pronto. Use: assistant --help"
