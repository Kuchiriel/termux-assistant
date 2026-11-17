---
name: Termux SSH e VNC
description: SSH (Tor/onion/chave com passphrase) e VNC a partir do Termux, com as pegadinhas do OpenSSH 10.5 no Android
---

Use quando o usuário pedir SSH, VNC, túnel de porta, TigerVNC, forwarding ou acesso remoto a partir do Termux.

## 1. O que está instalado (medido)

`openssh 10.5p1`, `proxychains4 4.17` (proxychains-ng), `tor`, `vncviewer` (TigerVNC
1.16.2 via pacman), `jq`, `curl`, `translate-shell`.
**Não existe** `torsocks` e **não existe** binário `tailscale` no Termux.

## 2. Chave com passphrase — use SSH_ASKPASS, não ssh-agent

O `ssh-agent` do Termux usa socket em `~/.ssh/agent/`; socket velho (ou processo
morto) causa `Permission denied (publickey)` **intermitente**.

```bash
export SSH_ASKPASS="$HOME/.config/vpnsec/askpass.sh"   # imprime a passphrase
export SSH_ASKPASS_REQUIRE=force
export DISPLAY=:0
ssh -i ~/.ssh/vpnsec_termux_ed25519 ...
```

## 3. Cliente pronto (cadeia Tor → onion → container)

`~/vpnsec/termux/run.sh` já faz tudo (pede `VPN_ONION`, checa o Tor, usa
proxychains4 + askpass e o `ssh_config` com `IdentitiesOnly`/`ExitOnForwardFailure`):

```bash
export VPN_ONION=hvcx....onion
~/vpnsec/termux/run.sh                                  # shell no container
~/vpnsec/termux/run.sh -N -T -L 5901:10.x.x.x:5900      # túnel VNC
~/vpnsec/termux/run.sh -N -T -L 2222:10.x.x.x:22         # túnel SSH
```

Depois: VNC Viewer (ou `vncviewer 127.0.0.1:5901`) no celular.

## 4. Pegadinhas do OpenSSH 10.5 no Android (medidas)

- **`X11Forwarding` é opção de servidor** → no cliente use `ForwardX11 no`, senão o
  ssh aborta com *Bad configuration option*.
- O **destino posicional** precisa ser um hostname válido: use um alias
  (`Host vpnsec-onion`) e passe o endereço real por `-o HostName=<onion>`.
  Sem isso o cliente aborta com *hostname contains invalid characters*.
- `ssh -L`/`-D` **não** resolvem o destino no celular — quem resolve é o servidor
  (no caso do container, o `resolv.conf` dele). Isso é o que faz o `-L` alcançar a
  intranet a partir de um host que não tem rota.
- `StrictHostKeyChecking accept-new` **falha** se a chave do host mudou (container
  recriado) → apague a entrada em `~/.ssh/known_hosts.vpnsec` e reconecte
  (o ideal é o host persistir a host key num volume).
- `ProxyCommand`/`ProxyJump` resolvem o host de salto **no cliente** → evite-os
  quando o nome for interno.

## 5. DNS e Tor

- `proxychains` com `strict_chain` + `proxy_dns`: sem Tor **não há** fallback em
  claro (falha em vez de vazar). `.onion` e nome interno resolvem pelo Tor/servidor.
- Confira antes: `proxychains4 -f ~/.proxychains.conf curl -s https://check.torproject.org/api/ip`
  → precisa vir `{"IsTor":true,...}`.

## 6. Widgets relacionados

`~/.termux/widget/crouton-{vpn,leak,snx,snx-up,menu,sessions,resume,doctor,assistant,bus}` —
atalhos de um toque (Termux:Widget). `crouton-leak` é o guard de vazamento de IP.

## 7. Diagnóstico rápido

```bash
~/bin/oc-doctor                 # versões, serviços, config, MCPs, rede
ssh -G -F ~/.ssh/config host    # resolve a config efetiva
```
