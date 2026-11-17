# Indice de comandos (ta)

| comando | o que faz | exige rede? |
|---|---|---|
| `ta doctor` | saude local e jobs | nao |
| `ta status` | lab + casa | host para status completo |
| `ta chat "q"` | roteia: local -> offline -> host | opcional |
| `ta offline "q"` | corpus FTS5 19k docs | **nao** |
| `ta linux status` | hostname/uptime/servicos do host | sim (tailnet) |
| `ta linux <cmd>` | executa comando remoto | sim |
| `ta api` | API OpenAI-compatible em 127.0.0.1:8787 | nao (backend opcional) |
| `ta widgets` | instala `~/.shortcuts` e refresca | nao |
| `ta backup` | tarball + sha256 em shared storage | nao |
| `ta restore <tar>` | restaura preservando arquivos novos | nao |
| `ta secrets` | varredura de segredos | nao |

## Atalhos (widgets)

Depois de `ta widgets`, na tela inicial: segure espaço vazio → Widgets →
Termux:Widget → arraste. Toque no widget e escolha `crouton-ask` (texto),
`crouton-voice` (voz), `crouton-offline` (blackout), `crouton-logs`, etc.

Se aparecer só `Assistente Termux.sh`: remova e readicione o widget na tela —
o refresh por broadcast ja foi enviado, mas o seletor do launcher e' estatal
e so pode ser mudado pelo usuario (medido: `SecurityException` no shell).

## API

```bash
# foreground, ctrl+c para parar
ta api
curl -s http://127.0.0.1:8787/health
curl -s -X POST http://127.0.0.1:8787/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"offline","messages":[{"role":"user","content":"purificar agua"}]}'
```
