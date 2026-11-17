#!/usr/bin/env bash
# blackout-harness — conversa local SEM internet, SEM servidor, SEM LLM obrigatorio.
#
# Modos (em ordem):
#   1) comando local do termux_bot.sh (bateria, IP, notificacoes) — zero rede
#   2) modelo GGUF local se TA_LOCAL_MODEL_CMD/URL estiver configurado
#   3) corpus offline FTS5 (19k docs) — zero rede
#   4) fallback honesto: dizer que nao sabe, nunca inventar
#
# Uso: blackout-harness "pergunta"
set -uo pipefail
export PATH="$HOME/bin:$PATH"
Q="${*:-}"
[ -z "$Q" ] && { echo "uso: blackout-harness 'pergunta'"; exit 2; }

for f in "$HOME/.config/termux-assistant/.env" "$HOME/.env"; do
  [ -r "$f" ] && { set -a; . "$f"; set +a; }
done

# 1) comandos locais conhecidos
case "$Q" in
  *bateria*|*battery*) exec "$HOME/projects/termux-assistant/termux_bot.sh" --quiet --no-tts "$Q" ;;
esac

# 2) modelo local opcional (o pacote NAO inclui pesos)
if [ -n "${TA_LOCAL_MODEL_URL:-}" ]; then
  R=$(timeout "${TA_LOCAL_TIMEOUT:-60}" curl -fsS --max-time "${TA_LOCAL_TIMEOUT:-60}" \
      -X POST "$TA_LOCAL_MODEL_URL/chat/completions" \
      -H 'Content-Type: application/json' \
      -d "$(printf '{"model":"local","messages":[{"role":"user","content":"%s"}]}' "$Q" | jq -c .)" 2>/dev/null \
      | jq -r '.choices[0].message.content // empty' 2>/dev/null)
  [ -n "$R" ] && { printf '%s\n' "$R"; exit 0; }
fi

# 3) corpus offline com resposta direta (extracao + fonte)
ANSWER="$HOME/projects/termux-assistant/blackout/tab_rag.py"
[ -f "$ANSWER" ] || ANSWER="$HOME/.local/share/termux-assistant/blackout/tab_rag.py"
if [ -f "$ANSWER" ]; then
  R=$(timeout 280 python3 "$ANSWER" "$Q" 2>/dev/null)
  [ -n "$R" ] && { printf '%s\n' "$R"; exit 0; }
fi

# 4) honestidade
printf 'Sem rede e sem modelo local configurado. Sei responder comandos do Termux e consultar o corpus offline. Configure TA_LOCAL_MODEL_URL para um GGUF local.\n'
