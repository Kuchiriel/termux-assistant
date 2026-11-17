---
name: phone-files
description: Acesso seguro de outros agentes (Linux/Windows) aos arquivos do celular e do HD externo — inventário, busca, leitura, movemento por quarentena e manifesto. Use quando pedirem "organizar os arquivos do celular", "ver o que tem no storage", "mover/quarentenar arquivo", "inventário do Android/HD", ou para achar documento do dono.
---

# Arquivos do celular (e do HD externo) — acesso controlado

O celular expõe SSH **só na tailnet** (`${TA_PHONE_IP:-100.104.175.123}:8022`, key-only) e o tool
`~/bin/phone-fs`, que aplica a política do dono.

## Do Linux (SSH) — testado nos dois sentidos

```bash
ssh -p 8022 u0_a438@${TA_PHONE_IP:-100.104.175.123} '~/bin/phone-fs inventory --json'
ssh -p 8022 u0_a438@${TA_PHONE_IP:-100.104.175.123} '~/bin/phone-fs find INSS --root shared --json'
```

O relay **Linux → celular** funciona (o Linux entra via chave e chama o phone-fs direto);
o audit log registra **quem chamou** (`caller=local | ssh:<ip>:<porta>`).

## Comandos

```bash
~/bin/phone-fs inventory --json          # o que tem, onde, tipo, tamanho, data
~/bin/phone-fs find <termo> [--root R] [--type ext] [--since AAAA-MM-DD] [--json]
~/bin/phone-fs stat <path> | cat <path>  # metadados / texto (até 2 MB)
~/bin/phone-fs propose quarantine --match GLOB [--root R] [--note "..."]
~/bin/phone-fs plans                      # propostas pendentes
~/bin/phone-fs apply <plan_id> --yes      # o celular executa: move p/ QUARENTENA + manifesto
~/bin/phone-fs roots | health
```

## Política (não negociável)

- **Leitura**: só `storage/shared`, `media`, `docs`, `archive`, `projects`, HD externo.
- **NEGADO sempre**: WhatsApp `databases`/`*.crypt15`/`backups`, `.ssh`, `.gnupg`,
  keystore, `Android/data`, `Android/obb`, `.nomedia`.
- **Intocáveis para mutação**: `DCIM`, `Documents`, `Pictures`, `Music`, `Movies`, `Android`.
- **Delete não existe**: tudo vai para **quarentena** no HD
  (`/storage/6E7C-8AB3/quarentena-termux/<ts>-<plan>/`) + manifesto reversível.
- **Auditoria**: tudo em `~/.local/state/phone-fs.log`.

## Como o DONO organiza (aprendido com ele)

- Por **PASTA temática** (`Download/INSS-28-09/`, `SINDICATO/`, `Fichas Beneficios/`) —
  por isso o `find` casa **também no caminho**, não só no nome do arquivo.
  **Desde 09/11 esse é o comportamento PADRÃO** (`find INSS` → 15 hits; antes dava 0
  porque só olhava o nome). Para voltar ao modo antigo, use `--so-nome`.
- Antes de pedir "acha o documento do INSS", **pergunte onde ele guarda**.
- Os documentos de **benefício/saúde** do dono estão **no celular** (não no PC).

## Inventário + dedup entre os 3 dispositivos

```bash
~/bin/catalog --out ~/ai-mesh/catalogo     # sha256 do celular + HD (1.054 arq / 1,47 GB)
~/bin/catalog-cross --host linux           # cruza com o catálogo do PC
```

Catálogo no repo: `ai-mesh/catalogo/termux.json` (+ `termux-hashes.json` = índice hash→paths).
O cruzamento acha **idênticos** (mesmo sha256) e **só no celular** — **sem mover nada**.
Taxonomia (tipo/data/projeto) ainda é decisão do dono.

Doc completo: `~/ai-mesh/docs/acesso-arquivos-do-celular.md` · `~/ai-mesh/docs/catalogo-sha256.md`.
