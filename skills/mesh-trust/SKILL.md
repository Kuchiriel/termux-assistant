---
name: Malha de confianca (tailnet)
description: Confianca mutua entre Termux, Linux (nitrov15) e Windows via SSH no tailnet — manifesto no bus, mesh-sync para instalar chaves, mesh para o estado, widget crouton-mesh
---

Use quando o usuário falar em confiança entre hosts, malha, peer, tailnet, SSH entre máquinas,
ou quiser que uma IA de um host entre em outro.

## Topologia (tailnet)

| host | IP tailnet | SSH | outros serviços |
|---|---|---|---|
| **termux** (celular) | ${TA_PHONE_IP:-100.104.175.123} | **8022** (só tailnet, key-only) | webhook 8789 · ponte OpenAI-compatible 8788 |
| **nitrov15** (Linux/NixOS) | ${TA_LINUX_IP4:-100.121.100.103} | 22 | coord-mcp 8765 (9 tools) |
| **windows** | 100.123.236.2 | (sem OpenSSH Server medido) | opencode server 4096 (via proxy coord) |

Caminho alternativo sem tailnet: celular → Tor → `.onion` → container `vpnsec-snx` no Linux.

## Como a confiança funciona

1. Cada host publica um **manifesto** no barramento (issue #12 do `Kuchiriel/mt5`), dentro do
   campo `note` de um payload `coord-json`, com o marcador `MESH-MANIFEST` e um JSON:
   `{"mesh":"v1","host":"...","ip":"...","user":"...","ssh_port":N,"pubkey":"ssh-ed25519 AAAA...","services":[...]}`
2. Cada host roda `mesh-sync apply` → lê o manifesto mais recente e **instala a chave pública dos
   peers no próprio `~/.ssh/authorized_keys`** (idempotente).
3. Chave **pública** pode circular pelo bus; **privada e senha nunca**.

> **MEDIDO 12/11:** o bus é uma **janela móvel** (já tem 1.542 comentários / 16
> páginas) e o leitor olhava só as **2 últimas páginas** — os manifestos de
> 07/11 saíram da janela e o `mesh-sync apply` falhou **181 vezes** com
> "nenhum manifesto encontrado no bus", sem que ninguém notasse. Agora o
> manifesto **de cada host vive no repo**, em `manifests/mesh/<host>.json`
> (chave pública — seguro versionar), e o bus continua sendo o canal de
> anúncio. O leitor usa o repo primeiro e o bus como fallback.

## Comandos (no Termux)

```bash
~/bin/mesh-sync publish    # publica meu manifesto no bus
~/bin/mesh-sync show       # mostra os manifestos encontrados
~/bin/mesh-sync apply      # instala as chaves dos peers no meu authorized_keys
~/bin/mesh-sync status     # manifesto + o que eu confio
~/bin/mesh status          # estado da malha (IPs/portas alcançáveis)
~/bin/mesh pubkey          # minha chave pública (pra publicar)
~/bin/mesh add <pubkey>    # instala a chave de um peer à mão
~/bin/mesh check <ip> [p] # testa SSH
```

Widget: `crouton-mesh` (mostra o estado e aplica o manifesto ao tocar).
Automação: jobs 105/106 (aplicar manifesto a cada 15 min) + `sshd-remote start` (o sshd não
sobe sozinho; log com teto de 5 MB e pre-flight de disco).

## Regras

- Nada de porta na internet: tudo no tailnet; o sshd do celular escuta **só** no IP de tailnet.
- O Windows precisa de **OpenSSH Server** (ou declarar outra porta) para entrar na malha por SSH.
- Chave privada nunca sai do host; o bus é para chave pública e instruções.
- Ao trocar de host/porta, publique o manifesto de novo (o último vale).
