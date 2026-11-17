---
name: Termux Widgets
description: Atalhos de um toque na tela inicial do Android via Termux:Widget (os scripts em ~/.termux/widget/) — como usar, o que cada um faz e como criar novos
---

Use quando o usuário falar de widget, tela inicial, atalho de um toque, Termux:Widget, ou quiser transformar um script em botão.

## Como instalar um widget

1. Tela inicial → segure espaço vazio → **Widgets**.
2. Arraste **Termux:Widget** para a tela.
3. Toque no widget → escolha o script (o app lista `~/.termux/widget/`).
4. O widget mostra o **stdout** do script. Toque de novo para atualizar.
5. Se não disparar: **não** habilite `allow-external-apps` (libera o intent RUN_COMMAND = qualquer app executa comandos no Termux). Os widgets usam o Termux:API (`RUN_WIDGET`) e funcionam sem ela; se precisar, habilite só temporariamente e reverta.

## Os widgets deste aparelho (`~/.termux/widget/`)

| widget | o que faz |
|---|---|
| `crouton-menu` | **menu principal** (dialog interativo): status VPN, leak check, status/pedido do túnel, barramento, Tor on/off, assistente, sessões, retomar, doctor, IP |
| `crouton-vpn` | estado da cadeia: Tor + exit, tailnet, container via `.onion` |
| `crouton-leak` | **guard de vazamento de IP**: mede o egress e aborta se for o IP residencial do dono |
| `crouton-onion` | status do túnel SNX no container (lido pelo `.onion`) |
| `crouton-onion-up` | guard + pedido ao host para subir o túnel (a senha não vai no barramento) |
| `crouton-bus` | estado do barramento de coordenação: último estado de cada agente + o que é endereçado a mim |
| `crouton-host` | **saúde do PC NixOS** pelo `.onion`: RAM, swap/zram, sessões opencode, veredito (CRÍTICO/ATENÇÃO/OK) |
| `crouton-assistant` | abre o assistente por voz; resposta falada em **pt-BR** |
| `crouton-sessions` | sessões recentes do OpenCode (título + hora) |
| `crouton-resume` | retoma a sessão mais recente (`opencode --session <id>`) |
| `crouton-doctor` | diagnóstico rápido: Termux, OpenCode, MCPs, Tor, coord-mcp, disco, **identidade (modelo+variante)** |

## Criar um widget novo

```bash
cat > ~/.termux/widget/meu-widget <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
# saída do script = o que aparece no widget
export PATH="$HOME/bin:$PATH"
printf 'linha1\nlinha2\n'
EOF
chmod +x ~/.termux/widget/meu-widget
```

Regras que evitam bug:
- sempre `set -uo pipefail` e `timeout` em chamadas de rede;
- o script roda em background → não pode pedir input (use `termux-dialog` para isso);
- falhe com mensagem curta (o widget tem pouco espaço);
- `termux-toast` para feedback de ação.

## Testar sem o app

```bash
bash ~/.termux/widget/crouton-doctor
bash ~/.termux/widget/crouton-host
```

Doc completa: `~/vpnsec/widgets/README.md`.
