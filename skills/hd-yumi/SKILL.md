---
name: hd-yumi
description: HD externo YUMI (SanDisk Extreme 1 TB, exFAT) — "Thunar abre vazio" é o disco caindo do USB, regra do LIXO/quarentena com manifesto, dedup já aplicada (Empresas=PROJETOS/CONSULTORIA) e números reais de espaço
---

# HD YUMI — usar antes de mexer no disco do PC

Detalhe completo: `~/docs/agentes/hd-yumi.md`. Aqui só o que muda decisão.

## 1. "Abre vazio" é o disco, não o gerenciador
O SanDisk Extreme cai do barramento por mal contato. Listagem vazia + `failed to
access to FAT` no dmesg = queda, não pasta vazia. **Verificar o kernel antes de
concluir qualquer coisa:**

```bash
ssh ${TA_LINUX_USER:-nixos}@${TA_LINUX_LAN:-192.168.15.10} 'sudo dmesg | grep -E "sda|exFAT|USB disconnect" | tail -10; findmnt /run/media/nixos/YUMI'
```

Caminho certo é `/run/media/nixos/YUMI` (atalho para `/media/nixos/YUMI` é fóssil
e abre vazio). O disco também é Ventoy (`sda2` = VTOYEFI, 32 MB) — não
reparticionar.

## 2. Nada é apagado direto: LIXO + manifesto
Regra do próprio disco (`LIXO/README.md`): nunca deletar automaticamente.
Dedup vai para `LIXO/quarentena-<data>/` com `MANIFESTO.md` + lista sha256 da
árvore. Reverter = `mv` de volta. Só libera espaço quando o dono esvaziar.

## 3. Já deduplicado (não refazer)
- `Empresas/` era cópia inteira de `PROJETOS/CONSULTORIA/` (9.270 de 9.271
  arquivos, mesmo caminho e tamanho). `Empresas/Sonda` + `Arquivos Compactados/Tecnico.7z`
  estão em `LIXO/quarentena-dedup-20261114/` (5,7 G), com prova sha256.
- Canônico: **`PROJETOS/CONSULTORIA/`**. Único exclusivo de `Empresas/`:
  `Zion/Contratos/Contrato ZionDashboard.docx`.

## 4. Números (não usar o catálogo como verdade)
`BACKUPS` 116 G · `Pessoal` 56 G (47 G = DATABASES) · `PROJETOS` 50 G ·
`DOCUMENTOS` 11 G · `Imagens`/`Empresas` 8,2 G cada · `MÍDIA` 6,4 G.
`catalogo/yumi.json` cobre só 30 GiB de 470 GiB (6%) — número de dedup dele não
vale para o disco.

## 5. Sensível
`PROJETOS/CONSULTORIA/Sonda/Técnico.7z` tem `Certificados Embraer` e pasta
`Crendenciais`. Existe em 2 lugares. Se não tiver senha, é credencial em claro.
