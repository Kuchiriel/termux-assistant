# AGENTS.md — ponteiro minimo do termux-assistant

> Este arquivo e' instalado somente se nao existir. Se o AGENTS.md do host ja
> existir, o instalador apenas acrescenta 2 linhas apontando para o repo.

## Entrada unica

- `ta doctor` — saude local (binarios, paths, jobs).
- `ta status` — laboratorio A/B e indice da casa.
- `ta chat "pergunta"` — roteia local/offline/host/API.
- `ta offline "pergunta"` — funciona sem internet.
- `ta linux status` — saude do host Linux pelo tailnet.
- `ta widgets` — reinstala atalhos em `~/.shortcuts` e refresca o widget.

## Regras que nao mudam

1. Medir antes de acreditar; `lab doctor` antes de concluir sobre modelo.
2. Segredo nunca em repo, bus, clipboard ou doc — so arquivo 600 local.
3. Uma VPN Android por vez; IP do dono nunca chega a terceiro (use `egress-guard`).
4. Nao reiniciar o opencode no meio do turno.
5. Antes de apagar: backup/quarentena. Use `ta backup`.
6. F-Droid e' a fonte atual dos APKs; nao misturar com GitHub sem uninstall + restore.

Mapa completo: `~/projects/termux-assistant/docs/INDEX.md`.
