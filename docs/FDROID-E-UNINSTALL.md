# F-Droid, update e uninstall — runbook

## Estado medido neste aparelho (17/11/2026)

```
TERMUX_APP__APK_RELEASE=F_DROID
TERMUX_APP__APP_VERSION_NAME=0.119.0-beta.3
TERMUX_APP__APK_FILE=/data/app/.../com.termux-.../base.apk
```

Termux, Termux:API, Termux:Widget e Termux:Window devem vir **todos** da mesma
fonte. O README oficial do termux-app diz que APKs de fontes diferentes têm
chaves de assinatura diferentes e usam `sharedUserId=com.termux`; misturar
causa `INSTALL_FAILED_SHARED_USER_INCOMPATIBLE` / `signatures do not match`.

## Regra pratica

1. **Fique no F-Droid.** Atualize Termux + plugins pelo F-Droid (às vezes é
   preciso puxar para baixo na aba Updates; o app nem sempre notifica).
2. **Nunca** instale apenas um plugin de outra fonte.
3. Se precisar migrar de fonte:
   - `ta backup` (gera tarball + sha256 em `~/storage/shared/termux-assistant/backups`);
   - copie esse tarball para outro dispositivo/HD;
   - desinstale **todos** os APKs Termux (isso apaga `$HOME`);
   - instale todos da nova fonte;
   - abra o Termux uma vez (bootstrap), dê permissão de storage;
   - `ta restore <tar.gz>`.
4. Não reinicie o opencode no meio de um turno para aplicar plugin/config.

## Por que o widget mostrava só umativo

Medido: o diretório que o Termux:Widget usa é `~/.shortcuts` (com
`~/.shortcuts/tasks` para background). Ele continha apenas
`Assistente Termux.sh`; os 20 scripts `crouton-*` estavam em
`~/.termux/widget` e por isso não apareciam. O instalador agora cria symlinks
em `~/.shortcuts` e dispara:

```bash
am broadcast -n com.termux.widget/.TermuxWidgetProvider \
  -a com.termux.widget.ACTION_REFRESH_WIDGET --ei appWidgetId 0
```

Fonte: README oficial de `termux/termux-widget` (seção Script Directories).
Se ainda não aparecer, é o seletor do launcher: remova o widget antigo da tela
e adicione um novo (isso é ação humana; não dá via shell sem permissão de
launcher — medido: `SecurityException`).

## Provavedor de update/uninstall/install

`tests/verify-layout.sh` checa, sem destruir nada:
- diretorios criticos e permissoes;
- presenca de `~/.shortcuts` com os atalhos;
- `.env` existe e nao tem valor de token;
- backup mais recente com sha256 valido.
