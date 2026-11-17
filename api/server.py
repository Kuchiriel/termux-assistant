#!/usr/bin/env python3
"""API local do termux-assistant — contrato OpenAI-compatible em loopback.

Rotas:
  GET  /health
  GET  /v1/models
  POST /v1/chat/completions   (model: "offline" | "auto" | "<id>")
  GET  /ta/status
  GET  /ta/bus                (somente se token configurado)

Seguranca: bind 127.0.0.1 por default; token opcional em
$TA_API_TOKEN_FILE (arquivo 600). NUNCA expor 0.0.0.0 sem token.
Backend: offline (FTS5 local) -> Linux API (quando alcancavel) -> erro honesto.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOME = Path.home()
ENV = HOME / ".config/termux-assistant/.env"
if ENV.is_file():
    for line in ENV.read_text().splitlines():
        if line.strip() and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), os.path.expandvars(v.strip()))

BIND = os.environ.get("TA_API_BIND", "127.0.0.1")
PORT = int(os.environ.get("TA_API_PORT", "8787"))
TOKF = Path(os.environ.get("TA_API_TOKEN_FILE", str(HOME / ".config/termux-assistant/api.token")))
OFFLINE = os.environ.get("TA_OFFLINE_BIN", str(HOME / "bin/offline"))
HOST_URL = os.environ.get("TA_LINUX_OC_URL", "http://100.121.100.103:4599")


def offline_answer(q: str) -> str:
    try:
        p = subprocess.run([OFFLINE, q, "-k", "3"], capture_output=True, text=True, timeout=40)
        out = (p.stdout or "").strip()
        return out[:3000] if out else "(corpus local sem resultado)"
    except Exception as exc:
        return f"(offline indisponivel: {type(exc).__name__})"


def host_answer(q: str, model: str) -> str:
    tokf = Path(os.environ.get("TA_OC_ENV_FILE", str(HOME / ".config/opencode/server.env")))
    pw = ""
    if tokf.is_file():
        for line in tokf.read_text().splitlines():
            if line.startswith("OPENCODE_SERVER_PASSWORD="):
                pw = line.split("=", 1)[1].strip().strip("\"'")
                break
    import base64
    auth = "Basic " + base64.b64encode(f"opencode:{pw}".encode()).decode()
    payload = json.dumps({"model": model, "input": q}).encode()
    req = urllib.request.Request(HOST_URL.rstrip("/") + "/api/generate/text",
                                 data=payload, method="POST",
                                 headers={"Content-Type": "application/json",
                                          "Authorization": auth})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read().decode())
            return str(d.get("text") or d.get("data") or d)[:3000]
    except Exception as exc:
        return f"(host indisponivel: {type(exc).__name__})"


class H(BaseHTTPRequestHandler):
    def _auth(self) -> bool:
        if not TOKF.is_file():
            return BIND in ("127.0.0.1", "::1")
        want = TOKF.read_text().strip()
        return self.headers.get("Authorization", "") in (f"Bearer {want}", f"token {want}")

    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self._auth():
            return self._send(401, {"error": "token required"})
        if self.path == "/health":
            return self._send(200, {"ok": True, "bind": BIND, "port": PORT})
        if self.path == "/v1/models":
            return self._send(200, {"object": "list", "data": [
                {"id": "offline", "object": "model"},
                {"id": "auto", "object": "model"},
                {"id": os.environ.get("TA_API_MODEL", "nvidia/minimaxai/minimax-m3.1-flash"), "object": "model"},
            ]})
        if self.path == "/ta/status":
            return self._send(200, {"repo": str(Path(__file__).resolve().parent.parent),
                                    "offline": Path(OFFLINE).is_file(),
                                    "host": HOST_URL})
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        if not self._auth():
            return self._send(401, {"error": "token required"})
        if self.path != "/v1/chat/completions":
            return self._send(404, {"error": "not found"})
        try:
            n = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(n) or b"{}")
            msgs = body.get("messages") or []
            q = " ".join(str(m.get("content", "")) for m in msgs[-2:])
            model = str(body.get("model") or "auto")
            if model == "offline" or (model == "auto" and not os.environ.get("TA_ONLINE", "0") == "1"):
                answer, src = offline_answer(q), "offline"
            else:
                answer, src = host_answer(q, model if model != "auto" else os.environ.get("TA_API_MODEL", "")), "host"
            return self._send(200, {"id": "ta-local", "object": "chat.completion",
                                    "model": model,
                                    "choices": [{"index": 0, "message": {"role": "assistant", "content": answer},
                                                 "finish_reason": "stop"}],
                                    "ta_source": src})
        except Exception as exc:
            return self._send(500, {"error": f"{type(exc).__name__}: {exc}"})


if __name__ == "__main__":
    print(f"ta-api em http://{BIND}:{PORT}/v1 — ctrl+c para parar")
    ThreadingHTTPServer((BIND, PORT), H).serve_forever()
