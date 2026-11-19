#!/usr/bin/env python3
"""ta — unica entrada da casa no Termux.

Sem argumentos: mostra o mapa. Subcomandos curtos, todos com --help:
  ta doctor            saude local e do host
  ta chat "pergunta"   roteia local/offline/linux/API
  ta offline "pergunta" corpus FTS5, sem rede
  ta linux "comando"   SSH no host (ou ta linux status)
  ta api               sobe a API OpenAI-compatible em loopback
  ta widgets           instala atalhos em ~/.shortcuts e refresca
  ta backup | restore  prova contra uninstall do Termux
  ta secrets           auditoria de segredos antes de publicar
  ta status            resumo de frota/lab/casa

Nada de segredo em stdout; tokens ficam em arquivos 600 apontados pelo .env.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
_repos = [Path(__file__).resolve().parent,
          HOME / "projects/termux-assistant",
          HOME / ".local/share/termux-assistant"]
REPO = next((p for p in _repos if (p / "README.md").is_file()), _repos[0])
STATE = HOME / ".local/state/termux-assistant"
ENVFILE = HOME / ".config/termux-assistant/.env"


def load_env():
    if not ENVFILE.is_file():
        return
    for line in ENVFILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), os.path.expandvars(v.strip()))


def run(cmd, timeout=60):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as exc:
        return 1, f"{type(exc).__name__}: {exc}"


def doctor(_a):
    checks = []
    for c in ("python3", "jq", "curl", "ssh", "gh"):
        checks.append((f"bin/{c}", "OK" if shutil.which(c) else "FALTA"))
    for p in (HOME / "bin", HOME / ".shortcuts", HOME / ".termux/widget",
              HOME / "offline-corpus", HOME / "ai-mesh"):
        checks.append((str(p).replace(str(HOME), "~"), "OK" if p.exists() else "FALTA"))
    for n, v in checks:
        print(f"{n:42} {v}")
    rc, out = run([str(HOME / "bin/jobs-audit")], 30)
    print("jobs:", out.strip().splitlines()[-1] if out.strip() else f"rc={rc}")


def chat(a):
    script = HOME / "bin/assistant-router"
    if not script.is_file():
        script = REPO / "bin/assistant-router"
    print(run([str(script), *a.rest], 180)[1], end="")


def offline(a):
    script = REPO / "bin/offline" if (REPO / "bin/offline").is_file() else HOME / "bin/offline"
    print(run([str(script), *a.rest], 60)[1], end="")


def linux(a):
    if not a.rest:
        return print("uso: ta linux status | ta linux ssh | ta linux <comando>")
    if a.rest[0] == "status":
        rc, out = run(["ssh", "-6", "-o", "ConnectTimeout=8", "-o", "BatchMode=yes",
                       f"{os.environ.get('TA_LINUX_USER', 'nixos')}@{os.environ.get('TA_LINUX_HOST6', 'fd7a:115c:a1e0::7f01:64bd')}",
                       "hostname; uptime; systemctl --user is-active agent-hub.service"])
    elif a.rest[0] == "ssh":
        return os.execvp("ssh", ["ssh", "-6", "-o", "ConnectTimeout=8",
                                 f"{os.environ.get('TA_LINUX_USER', 'nixos')}@{os.environ.get('TA_LINUX_HOST6', 'fd7a:115c:a1e0::7f01:64bd')}"])
    else:
        cmd = " ".join(a.rest)
        rc, out = run(["ssh", "-6", "-o", "ConnectTimeout=8", "-o", "BatchMode=yes",
                       f"{os.environ.get('TA_LINUX_USER', 'nixos')}@{os.environ.get('TA_LINUX_HOST6', 'fd7a:115c:a1e0::7f01:64bd')}",
                       cmd], 120)
    print(out, end="")


def api(_a):
    script = REPO / "api/server.py"
    if not script.is_file():
        return print("API ausente no pacote")
    os.execvp(sys.executable, [sys.executable, str(script)])


def widgets(_a):
    script = REPO / "scripts/install-widgets.sh"
    rc, out = run(["bash", str(script)], 60)
    print(out, end="")
    return rc


def backup(_a):
    script = REPO / "backup/backup.sh"
    rc, out = run(["bash", str(script)], 600)
    print(out, end="")
    return rc


def restore(a):
    script = REPO / "backup/restore.sh"
    rc, out = run(["bash", str(script), *a.rest], 600)
    print(out, end="")
    return rc


def tabfast(a):
    script = REPO / "bin/tab-fast"
    rc, out = run([str(script), *a.rest], 60)
    print(out, end="")
    return rc


def slm(a):
    script = REPO / "bin/tab-slm"
    rc, out = run([str(script), *a.rest], 300)
    print(out, end="")
    return rc


def secrets(_a):
    script = REPO / "tests/scan-secrets.py"
    rc, out = run([sys.executable, str(script), str(REPO)], 60)
    print(out, end="")
    return rc


def status(_a):
    failed = 0
    for label, cmd in [
        ("LAB", [str(HOME / "bin/lab"), "status"]),
        ("HOUSE", [str(HOME / "bin/house"), "status"]),
    ]:
        rc, out = run(cmd, 60)
        print(f"=== {label} (rc={rc})")
        print("\n".join(out.splitlines()[:12]))
        if rc != 0:
            failed = 1
    return failed


def main(argv=None):
    load_env()
    p = argparse.ArgumentParser(prog="ta", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd")
    for name, fn, helptext in [
        ("doctor", doctor, "saude local/host"),
        ("chat", chat, "roteador de perguntas"),
        ("offline", offline, "corpus offline"),
        ("linux", linux, "host Linux"),
        ("api", api, "API local OpenAI-compatible"),
        ("widgets", widgets, "instalar/refrescar atalhos"),
        ("backup", backup, "backup completo"),
        ("restore", restore, "restaurar backup"),
        ("tab", tabfast, "emergencia offline rapida (sem SLM)"),
        ("slm", slm, "pergunta one-shot ao SLM local"),
        ("secrets", secrets, "auditar segredos"),
        ("status", status, "lab + casa"),
    ]:
        q = sub.add_parser(name, help=helptext)
        q.set_defaults(fn=fn)
        if name in ("slm", "tab", "chat", "offline", "linux"):
            q.add_argument("rest_args", nargs="*", help=argparse.SUPPRESS)
    a = p.parse_args(argv)
    if getattr(a, "rest_args", None):
        a.rest = a.rest_args
    elif a.cmd and argv and argv[0] == a.cmd:
        a.rest = argv[1:]
    else:
        a.rest = argv[argv.index(a.cmd) + 1:] if a.cmd and argv and a.cmd in argv else []
    if not getattr(a, "fn", None):
        print("termux-assistant — um comando para a casa\n")
        print("  ta doctor | chat | offline | linux | api | widgets | backup | restore | secrets | status")
        print(f"\nrepo: {REPO}\nenv: {ENVFILE}")
        return 0
    return a.fn(a) or 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
