#!/usr/bin/env python3
"""slm_answer — resposta de sobrevivencia em PT com SLM local + corpus (RAG).

Motorola Edge (arm64, 8 cores, ~5.5GB RAM): Qwen2.5-1.5B-Instruct Q4_K_M
roda em CPU via llama.cpp. O modelo NAO inventa: so recebe trechos do corpus
e deve responder em portugues com passos acionaveis + fonte.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

MODEL = Path(os.environ.get("TA_SLM_MODEL", str(Path.home() / "models/slm/qwen2.5-1.5b-Q4_K_M.gguf")))
CLI = os.environ.get("TA_LLAMA_CLI", "llama-cli")
DB = Path(os.environ.get("TA_OFFLINE_DB", str(Path.home() / "offline-corpus/corpus.db")))
STOP = set("a o as os da de do das dos um uma para com em por no na que e ou se como fazer deve devem usar uso".split())
EXP = {"purificar": "purifying purification distillation treatment water", "agua": "water",
       "queimadura": "burn", "picada": "snake bite", "cobra": "snake", "engasgo": "choking",
       "primeiros": "first aid", "socorros": "aid", "febre": "fever", "ferida": "wound"}


def norm(s):
    s = "".join(c if c.isalnum() else " " for c in s.lower())
    return " ".join(w for w in s.split() if w not in STOP)


def retrieve(q, limit=3):
    import sqlite3
    words = norm(q).split()
    terms = []
    for w in words:
        terms.append(w); terms.extend(EXP.get(w, "").split())
    fts = " OR ".join(dict.fromkeys(terms)) or "water"
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=10)
    try:
        rows = c.execute("select title, body, source, bm25(docs) as s from docs "
                         "where docs match ? order by s limit ?", (fts, limit)).fetchall()
    except Exception:
        rows = []
    finally:
        c.close()
    return rows


def clean(t):
    t = re.sub(r"\*\*Autor:\*\*[^\n]*|\\*\\*Páginas:\\*\\*[^\n]*", " ", t)
    t = re.sub(r"## Page \d+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def grounded(q):
    rows = retrieve(q)
    if not rows:
        return "SEM FONTE LOCAL. Nao vou inventar."
    ctx = "\n\n".join(f"[FONTE {i+1}: {src}]\n{clean(b)[:750]}" for i, (_, b, src, _) in enumerate(rows[:4]))
    system = ("Voce e TAB, assistente de sobrevivencia. Responda EM PORTUGUES do BRASIL, "
              "em ate 5 passos numerados. Use SOMENTE as FONTES abaixo, combinando "
              "informacoes de documentos diferentes quando fizer sentido. "
              "Se uma afirmacao nao estiver nas fontes, escreva SEM FONTE. "
              "Nao invente termos, nao troque palavras. "
              "Ao final, em linha propria, escreva VEREDITO: CONFIAVEL ou DUVIDOSO "
              "e cite os numeros das fontes usadas.")
    system = system + "\n\nCONTEXTO (fonte primaria):\n" + ctx
    if not MODEL.is_file():
        return f"(modelo local ausente: {MODEL})\n\nFonte bruta:\n{ctx}"
    cmd = [CLI, "-m", str(MODEL), "-sys", system, "-p", q,
           "--ctx-size", "1536", "-st", "-n", "200", "--no-warmup", "-t", "4",
           "--no-display-prompt"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        out = p.stdout or ""
        # o llama-cli imprime o prompt ecoado apos "> "; a resposta vem depois
        marker = [l for l in out.splitlines() if l.lstrip().startswith("> ")]
        if marker:
            out = out.rsplit(marker[-1], 1)[1]
        else:
            out = out.split("available commands:")[-1]
        out = re.split(r"\[ Prompt:|Exiting\.\.\.", out)[0].strip()
        fontes = ", ".join(f"F{i+1}={s2}" for i, (_, _, s2, _) in enumerate(rows[:4]))
        return (out[:2400] or "(sem texto gerado)") + ("\n\nFontes: " + fontes)
    except Exception as exc:
        return f"(SLM falhou: {type(exc).__name__})\n\nFonte bruta:\n{ctx}"


if __name__ == "__main__":
    print(grounded(" ".join(sys.argv[1:]) or "como purificar agua"))
