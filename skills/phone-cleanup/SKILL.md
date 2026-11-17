---
name: phone-cleanup
description: Organizar e limpar o armazenamento do Android via Termux (~/bin/phone-clean), o mapa do que ocupa espaco e o que NUNCA deve ser apagado
---

Use quando o usuário pedir para liberar espaco, organizar arquivos, limpar lixo, ou perguntar onde está o espaço do celular.

## Ferramenta

```bash
~/bin/phone-clean --report              # tamanho por categoria (nao apaga)
~/bin/phone-clean --safe --yes          # apaga SO lixo inequivoco
~/bin/phone-clean --duplicates          # duplicatas exatas (por hash)
~/bin/phone-clean --big 200            # arquivos >= 200 MB
~/bin/phone-clean --old 365             # arquivos do Download com >365 dias
~/bin/phone-clean --organize            # Download por tipo (com manifesto reversivel)
~/bin/phone-clean --prune-whatsapp 180 --yes   # midia orfa >180d (politica do app)
```

## Mapa (medido 06/11/2026)

| lugar | tamanho | situação |
|---|---|---|
| WhatsApp Business → `Media` | 5,0 GB | mídia **ativa** (app instalado): só o app reduz (Configurações → Gerenciar armazenamento) |
| WhatsApp Business → `Databases` | 3,0 GB | **NUNCA** apagar (é o histórico de chat) |
| WhatsApp Business → pastas "WhatsApp *" | 1,79 GB | **órfãs**: o app `com.whatsapp` não está instalado (só o `w4b`) → prune por idade já aplicado |
| `Download` | 892 MB | organizado em `documentos/ compactados/ modelos-3d/ midia/ programas/ outros/` (manifesto em `~/docs/`) |
| DCIM / Pictures / Movies / Documents | ~700 MB | conteúdo do usuário, **não mexer** |
| Termux (home) | ~600 MB | projetos + `.cargo` (253 MB, mantém rebuild offline) |

## Regras (hard)

1. **Nunca** apagar `Databases/`, `Backups/`, DCIM, Documents, Pictures, Music, Movies.
2. Apagar mídia do WhatsApp **não** apaga mensagens (fica botão de re-download) — mas só o app é dono do `Databases`.
3. Antes de apagar qualquer coisa que não seja lixo óbvio: **mover para quarentena** e anotar (manifesto), nunca apagar direto.
4. `Pictures/.thumbnails`, caches e `.tmp` podem ser apagados (reconstroem).
5. Libere o `~/.cargo/registry/cache` (os `.crate`); o `src/` extraído fica (rebuild offline).

## Liberações já feitas

`~/vpn-port/snx-rs/target` (1,7 GB) · caches npm (530 MB) · `.thumbnails` (71,8 MB) · `~/.cache` · `.cargo/registry/cache` (27 MB) · mídia órfã do WhatsApp >180d (1,6 GB) · temp de trabalho. Resultado: **~4 GB liberados**.
