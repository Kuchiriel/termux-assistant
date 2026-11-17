# Arquitetura — termux-assistant

## Camadas

```
voce (Termux / widget / voz)
        |
        v
   ta (CLI unica) ---- ta api (OpenAI-compatible, loopback:8787)
        |                         |
        +--> bin/ (44 utilitarios)|
        +--> blackout/harness.sh  |
        +--> offline (FTS5 19k)   |
        +--> ssh/tailnet -> Linux (hub, MCPs, LLM local, A/B)
```

## Principios

1. **Agnostico**: tudo fala por contrato (CLI / HTTP OpenAI-compatible / SSH).
   Nenhum script sabe onde o host esta — vem de `.env`.
2. **Sem segredo no repo**: `.env.example` so tem caminhos; tokens ficam em
   arquivos 600. `ta secrets` bloqueia push.
3. **Blackout-first**: `blackout/harness.sh` nunca exige internet para responder
   comandos locais e corpus offline. Modelo GGUF e opcional (`TA_LOCAL_MODEL_URL`).
4. **Idempotente**: `install.sh` nao apaga nada; usa `.ta-backup-*` e symlinks.
5. **Visivel**: atalhos em `~/.shortcuts` (diretorio canonico do Termux:Widget),
   nao apenas em `~/.termux/widget`.

## Mapeamento de dores -> solucao

| dor desta sessao | solucao |
|---|---|
| 10 comandos diferentes para achar coisa | `ta status`, `ta doctor`, `house` |
| widget so mostrava um atalho | `~/.shortcuts` + broadcast de refresh |
| toolbar sumiu | configuracao documentada + `termux-reload-settings` (depende da tela) |
| latencia da voz | roteador: local/offline/house/API com numeros |
| medo de uninstall F-Droid | `ta backup`/`ta restore` + runbook |
| segredo em log/bus | `ta secrets`, `.env` com caminhos |
| blackout | harness local + corpus FTS5 + modelo opcional |
| comunicação entre agents | hub API + `coord_house` + wake steer (contratos V2) |
| spawn headless | `spawn-visible.sh` no host (aba no TUI) |

## O que NAO esta no pacote

- pesos de modelos (GGUF) — usuario fornece via `TA_LOCAL_MODEL_URL`;
- tokens/keys — usuario fornece via arquivos 600;
- catalogos de 150 MB e logs — ficam no host/celular, nao no repo.
