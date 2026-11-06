# termux-assistant

Assistente de voz e comandos para o **Termux** (Android), com três backends de LLM:
o próprio **OpenCode** do aparelho, qualquer endpoint **OpenAI-compatible**, ou **Ollama** local.

> Reescrito em 06/11/2026: setup idempotente, sem `set -x` no output, timeouts em toda
> chamada de rede, TTS por frase (o antigo fazia um toast por palavra), sem `source ~/.bashrc`,
> e **OpenCode como backend padrão** (elimina o proot-distro/Arch/Ollama de 4 GB).

---

## 1. Instalação

```bash
git clone https://github.com/Kuchiriel/termux-assistant
cd termux-assistant
./setup_bot.sh --help
./setup_bot.sh                    # instala o que falta e grava a config
```

O `setup_bot.sh`:

- instala `termux-api`, `jq`, `curl` e `translate-shell` (só se faltarem);
- avisa (não trava) se faltar a permissão de armazenamento (`termux-setup-storage`);
- verifica o backend escolhido e a saúde dele no final;
- grava `~/.config/termux-assistant/config.env` (600);
- cria o atalho `~/bin/assistant` e o atalho Termux:API `~/.shortcuts/Assistente Termux.sh`.

Opções: `--backend opencode|openai|ollama`, `--model <m>`, `--lang <l>`, `--dry-run`,
`--no-ollama`, `--with-ollama`.

## 2. Uso

```bash
assistant "acende a lanterna"                 # comando local, responde na hora
assistant "qual o nivel da bateria?"
assistant --backend opencode "explique o tunel SSL em 2 frases"
assistant --interactive                       # dialogo por voz, ate "sair"
assistant --stream "conte uma historia"       # fala por sentenca enquanto gera
assistant --no-tts "..."                     # so texto no stdout
```

Saída: a resposta vai para o **stdout** (dá para pipe); toast e TTS são extras.

**TTS sempre em português do Brasil** (`TA_LANG=pt-br`, voz fixa). Se a resposta do
LLM vier em outro idioma, ela é **traduzida** antes de ser falada
(`TA_TTS_TRANSLATE=true`, usa `translate-shell`); a voz nunca muda sozinha.

## 3. Comandos locais (não vão para o LLM)

| comando | ação |
|---|---|
| lanterna / torch | liga/desliga (`termux-torch`) |
| volume | sobe/baixa o volume de mídia |
| bateria | nível, saúde, temperatura, carregando |
| notificação | lista resumida (não despeja o JSON) |
| localização | lat/lon + endereço (OpenStreetMap), com timeout |
| IP | local (`ip -4`) e público (`api.ipify.org`) |
| toast / copiar / vibrar | utilitarios |
| sair | encerra o modo interativo |

Todo o resto vai para o LLM com um prompt de sistema curto ("português do Brasil, no máximo 3 frases").

## 4. Backends

| backend | como funciona | observações |
|---|---|---|
| `opencode` (padrão) | `opencode run --format json --model <m>` (saída é **JSONL**: o texto vem em `.part.text` das linhas `.type=="text"`) | usa a config do próprio OpenCode do aparelho (mesmo modelo do agente, janela de 1M, variantes de reasoning). Não precisa de proot/Ollama. Roda num diretório neutro (`$TA_RUN_DIR`) para não carregar o `AGENTS.md` da home — ~5s em vez de ~17s por resposta. |
| `openai` | POST em `$TA_OPENAI_ENDPOINT` com `OPENAI_API_KEY` | qualquer OpenAI-compatible (OpenRouter, NIM, llama.cpp…). |
| `ollama` | `POST /api/generate` | local; opcionalmente em `proot-distro`/Arch (instalado por `--with-ollama`). |

Trocar de backend é `~/.config/termux-assistant/config.env` ou `--backend` na chamada.

## 5. Config

`~/.config/termux-assistant/config.env` (gerado pelo setup):

```bash
TA_BACKEND=opencode
TA_MODEL=nvidia/minimaxai/minimax-m3.1-flash
TA_LANG=pt-br
TA_STREAM=false
TA_TIMEOUT=120
TA_TTS=true
TA_TTS_TRANSLATE=true
TA_RUN_DIR=/data/data/com.termux/files/usr/tmp/opencode/assistant-run
TA_OPENAI_ENDPOINT=http://127.0.0.1:8000/v1/chat/completions
TA_OLLAMA_HOST=http://127.0.0.1:11434
```

Variáveis de ambiente sobrescrevem o arquivo (`TA_*`). Segredos (chaves) **nunca**
vão para o config: use `OPENAI_API_KEY` no ambiente.

## 6. Requisitos no Termux

- `pkg install termux-api jq curl translate-shell`
- app **Termux:API** instalado (o `pkg` instala o binário; o app precisa estar instalado).
- Permissão de armazenamento (só para câmera/galeria): `termux-setup-storage`.

## 7. Problemas comuns

| sintoma | causa provável | solução |
|---|---|---|
| `Termux:API app not installed` | app ausente | instale o app Termux:API (F-Droid/GitHub) e rode `termux-api-start` |
| `trans: command not found` | translate-shell ausente | `pkg install translate-shell` |
| a voz pt-BR não fala | falta a voz no Android | Ajustes → Sistema → Idiomas e entrada → Saída de texto para voz → baixe **português (Brasil)**. O `setup_bot.sh` avisa se a voz não responder |
| resposta lenta | o OpenCode carregou o `AGENTS.md` | o backend `opencode` roda em `$TA_RUN_DIR` (dir neutro); ~5s em vez de ~17s |
| Ollama não responde | não está rodando | `proot-distro login archlinux -- ollama serve` ou `--backend opencode` |
| `opencode models` vazio | provider sem credencial | configure a chave do provider no OpenCode do aparelho |

## 8. Estrutura

```
termux-assistant/
├── setup_bot.sh        # instalador/configurador idempotente
├── termux_bot.sh       # o assistente (comandos locais + LLM)
├── lib/common.sh       # helpers: log, config, TTS por frase, backends
└── config.example.env  # referência da config
```

## Licença

Ver [LICENSE](LICENSE).
