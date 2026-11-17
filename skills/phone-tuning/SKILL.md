---
name: Bateria, tela e performance do celular
description: O que da (e o que NAO da) para ajustar sem root no Android via Termux — diagnostico de bateria, sensor de proximidade cortando a tela, e como deixar o aparelho mais leve
---

Use quando o usuário reclamar de bateria que não segura carga, tela que apaga sozinha, sensor de proximidade ruim, ou aparelho lento.

## Limite medido (sem root, o app é um app)

**Não funciona** a partir do Termux: `settings get/put` (vazio), `settings list`, `dumpsys sensorservice`, `dumpsys battery`, `/sys/class/power_supply/battery/*` (sem acesso), `pm disable-user`.
**Funciona**: Termux:API (`termux-battery-status`, `termux-fingerprint`, `termux-dialog`...) e `am start -a android.settings.<X>` para **abrir** telas do sistema (mas não tocar nelas).

## Bateria — o que dá para medir

```bash
~/bin/battery-monitor status   # nivel, saude, temperatura, tensao, corrente, charge_counter
~/bin/battery-monitor log      # grava amostra no CSV (~/.local/state/battery.csv)
~/bin/battery-monitor trend 7  # desgaste: delta de charge_counter, Ah/dia, ciclos/ano, temp max
~/bin/battery-monitor watch    # loga a cada 15 min + avisa no ntfy se passar de 42C
```

`termux-battery-status` expõe: `percentage`, `health`, `temperature` (C), `voltage` (mV),
`current` (µA, +carregando / −descarregando), `charge_counter` (µAh acumulados).
**Não expõe** `cycle_count` nem capacidade de projeto (exigem `dumpsys`/root) → o desgaste
é medido pelo **delta do charge_counter** ao longo do tempo (1 Ah ≈ 1 ciclo).

Sinais de bateria degradada: temperatura alta durante o uso (≥42C), `health` diferente de
`GOOD`, e nível caindo rápido. Bateria quente = swelta → cai a carga → o celular "desliga"
sozinho. Ações sem root: carregamento otimizado/adaptativo (se o ROM tiver), brilho
automático sem always-on, menos apps em primeiro plano, e Termux sem serviço ocioso
(`oc-ram --stop-idle`, `sshd-remote stop`).

## Tela apagando sozinha / proximidade

`~/bin/tune` abre a tela certa e imprime o passo a passo.

⚠️ **Opções do desenvolvedor podem QUEBRAR app de banco**: vários bancos brasileiros
checam `ADB_ENABLED`/estado de developer options e bloqueiam o app no aparelho.
Por isso a ordem é **sem developer options**:
1. `Tela > Tempo de tela inactivity` → 30 min (resolve quase tudo);
2. tela não apaga durante vídeo/PDF de qualquer app;
3. app utilitário "keep screen on" (F-Droid) — sem ADB, sem dev options;
4. teste no Termux: `termux-dialog` aberto costuma segurar a tela (panel "Tela acesa");
5. **só se for mesmo preciso** "Stay awake while charging": ative as Opções do desenvolvedor,
   **desligue a Depuração USB** e teste o app de banco depois.

Causa nº 1 da tela apagar sozinha: **capinha/película** que mantém o sensor de proximidade
coberto → modo bolso constante. Teste tirar a capinha; se parar, achou.
O Termux **não** expõe o sensor de proximidade (`dumpsys sensorservice` negado) → ajuste fino
não é possível por aqui. O aparelho tem **sensor de digital** (`termux-fingerprint` responde),
não face-unlock nativo.

## Acelerar sem root

- Termux não muda o Android, mas: Termux mais novo (F-Droid/GitHub — a Play Store congela),
  menos jobs/serviços em background, armazenamento folgado (feito: ~4 GB), jobs pesados com
  `nice`/`ionice`, e debloat de apps do fabricante via **ADB do PC** (`pm disable-user` do
  Termux é negado).
- Jobs do agendador: `termux-job-scheduler --pending` / `--cancel <id>` (mínimo do Android: 15 min).

## Script `tune`

```bash
~/bin/tune listar      # testa quais telas abrem
~/bin/tune stayawake   # Opcoes do desenvolvedor (so se necessario; ver alerta do app de banco)
~/bin/tune display|security|battery|apps|face
```
