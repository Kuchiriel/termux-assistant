---
name: termux-vpn
description: VPN/anonimato no Android Termux sem root (uma VPN por vez), cadeia Tor→onion→container, Mullvad/Proton/Tailscale e o guard de egress para nunca vazar o IP do dono
---

# VPN no Termux (projeto **vpnsec**)

Cobre: um slot de VPN por vez (Android), Tor local, proxychains, cadeia até container
privado por `.onion`, Mullvad/Proton/Tailscale e o **guard de egress**.

## 1. Regras do Android (quebram tudo se ignoradas)

- **Uma VPN Android por vez** (`VpnService`): Proton, Tailscale e SonicWall se derrubam.
- Termux é **app**, não root: `settings`/`dumpsys`/`sysfs` bloqueados; use Termux:API e `am start`.
- **Sem root = sem ADB**: não sugira Opções do desenvolvedor (quebra app de banco).
- Quando o Tailscale reinicia, o `tun0` é recriado → serviços amarrados no IP antigo
  ficam **vivos com socket morto**. Valide sempre a **porta**, não o PID.

## 2. Regra dura: o IP público do dono nunca sai do celular

- Qualquer teste/análise que dependa de anonymity passa por Tor/proxy.
- Use `~/bin/egress-guard` (novo): diagnostica a rota e **aborta** se o tráfego sairia
  pelo IP residencial.
  ```bash
  ~/bin/egress-guard              # diagnostico
  ~/bin/egress-guard --check      # sai != 0 se nao estiver protegido
  ~/bin/egress-guard --run "cmd"  # roda o cmd SO se estiver protegido
  ```
- VPN/UDP direto do celular **não passa por Tor** (Tor carrega TCP) → para esse tipo de
  teste, o caminho é pelo host Linux (SSH), nunca pelo link do celular.

## 3. Cadeia do projeto vpnsec (celular)

```
Celular → tor local (SOCKS 9050) → proxychains4 → .onion → sshd do container vpnsec-snx
                                                            └─ i386/userspace quando o cliente é 32-bit
```

Arquivos (projeto **vpnsec**):

```
~/vpnsec/termux/run.sh          # sobe a cadeia
~/vpnsec/termux/ssh_config      # Host .onion, UserKnownHostsFile=/dev/null, StrictHostKeyChecking=no
~/vpnsec/termux/proxychains.conf# socks5 127.0.0.1 9050
~/vpnsec/termux/teste-e2e.sh    # teste fim a fim da cadeia
~/vpnsec/widgets/README.md      # widgets do projeto
```

Pegadinhas já pagas:

- `StrictHostKeyChecking=no` + `UserKnownHostsFile=/dev/null` **no cliente** (o host .onion
  troca de chave a cada start) — mas **nunca** afrouxe o `sshd_config` do servidor.
- `proxychains4` é o que existe (não `torsocks`).
- Cliente 32-bit (i386) **não roda** em aarch64: o container no host resolve isso.
- O Tor local é `127.0.0.1:9050` (SOCKS); o proxychains aponta para ele.

## 4. Other VPNs (regras de uso)

| ferramenta | uso | cuidado |
|---|---|---|
| **Tailscale** | tailnet (Motorola Edge ↔ nitro-v15 ↔ Windows) | só 1 VPN Android ativa; se piscar, serviços perluem re-amarra |
| **Mullvad/Proton** | saída por VPN comercial | nunca combina com Tailscale ao mesmo tempo (mesmo slot) |
| **Tor** | anonymity real (TCP) | não carrega UDP; use proxychains4 |

## 5. Diagnóstico rápido

```bash
pgrep -af "tor -f"                     # tor rodando?
timeout 4 bash -c 'cat < /dev/null > /dev/tcp/127.0.0.1/9050' && echo "9050 OK"
ip -4 -o addr show scope global | awk '{print $2,$4}'   # tun0/wlan0/rmnet
~/bin/egress-guard
```

Relacionados: `mesh-trust` (chaves/SSH na tailnet) · `termux-ssh-vnc` (SSH/VNC) ·
`remote-automation` (sshd/webhook/ponte no celular).
