---
name: opencode-termux
description: Config, servicos, MCPs, skills, identidade dinamica e ferramentas de diagnostico do OpenCode rodando no Android Termux (duas instalacoes: 2.2.5 e 2.0.0-termux)
---

Use para mexer na config do OpenCode no celular, descobrir qual instalação/sessão está ativa, ou diagnosticar serviços, MCPs, memória e plugins.

## Duas instalações (fato de ambiente)

| binário | versão | serviço | papel |
|---|---|---|---|
| `opencode` | **v2.2.5 (upstream)** | `127.0.0.1:52031` | **é onde a sessão do agente roda**; lê a config; aceita `providers.<id>.models` |
| `opencode2` | v2.0.0-android-termux.2 (build Termux) | `127.0.0.1:28570` | secundário: correções de TUI do Android (fix do crash Ctrl+B) |

Senhas dos serviços (para `--server`): `~/.config/opencode/service-stable.json` → 52031; `service-android-termux.json` → 28570. Use `OPENCODE_PASSWORD`.

## Identidade é DINÂMICA

O **modelo muda por sessão** (MiniMax via NVIDIA, DeepSeek via opencode, ...). Nunca fixe no AGENTS.md. Descoberta:

```bash
~/bin/oc-identidade        # alias: oc-quem     (--json para automação)
```

Ele pega o `OPENCODE_SESSION_ID`, pergunta a cada serviço qual sessão ele possui e devolve sessão + servidor + modelo + provider + variante.

## Ferramentas

```bash
~/bin/oc-doctor     # versoes, servicos, config, MCPs, skills, rede, pendencias
~/bin/oc-ram        # RSS por processo + RAM/swap; --stop-idle / --start-all
~/bin/oc-sessions   # lista sessoes do OpenCode
~/bin/oc-restart-opencode [seg]  # reinicia SO o 2.2.5, detach (nao mata a tool call)
~/bin/host-watch    # saude do PC NixOS pelo .onion (RAM/swap/zram/veredito)
```

## Config (`~/.config/opencode/opencode.json`)

- `model`: `nvidia/minimaxai/minimax-m3.1-flash` · `compaction`: auto, keep 50000, buffer 10%.
- `providers.nvidia`: `compatibility` (`requireFinishReason:false`, `maxTokensField`, `reasoningField`) + `settings` (timeouts 15/30/30 min) + catálogo de 23 modelos. Medido: minimax ctx **1.048.576** (o catálogo diz 262.144) e 7 variantes de reasoning.
- `mcp.servers`: `context7` (docs), `github` (46 tools, Bearer `GITHUB_TOKEN`), `jarvis` (coord, tailnet).
- `plugins: []` — **DCP e opencode-mem são v1 e quebram no v2** (`ctx.model.transform is not an object` / `NpmInstallFailedError` no Termux aarch64). Não instalar.

## Pegadinhas (medidas)

- O `opencode2` tem **file watcher desabilitado** (`OPENCODE_EXPERIMENTAL_DISABLE_FILEWATCHER=true`) e schema de provider diferente → ele **não recarrega a config** e **descarta** `providers.<id>.models`. O 2.2.5 recarrega.
- `~/.config/opencode/opencode.json` tem **precedência sobre** a config de projeto; a global só entra se não houver config de projeto no diretório.
- **O `AGENTS.md` da home tem ~45 KB e entra em toda sessão**: rodar `opencode run` de um diretório neutro baixa de ~17s para ~5s.
- RAM do celular é escassa (5,4 GB): cada serviço do OpenCode segura 200–400 MB. Pare o ocioso com `oc-ram --stop-idle`.
- Termux: **não existe `torsocks`** (use `proxychains4`), **não existe `node`/`bun`**, e os mirrors brasileiros de apt **não resolvem DNS** aqui.
