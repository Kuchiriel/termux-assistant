#!/usr/bin/env python3
"""offline-answer — resposta direta do corpus FTS5, sem internet e sem LLM.

Busca em corpus.db, limpa metadados e devolve sentencas acionaveis com fonte.
Contrato: se nao houver fonte, dizer SEM FONTE LOCAL (nunca inventar).
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys

DB = os.path.expanduser(os.environ.get("TA_OFFLINE_DB", "~/offline-corpus/corpus.db"))
STOP = set("a o as os da de do das dos um uma para com em por no na que e ou se como fazer deve devem usar uso water health page".split())


def norm(s):
    s = "".join(c if c.isalnum() else " " for c in s.lower())
    return " ".join(w for w in s.split() if w not in STOP)


def search(q, limit=3):
    # FTS5 casa por termo; PT->EN简单 expandido com sinonimos de emergencia.
    EXP = {"purificar":"purifying distillation treatment", "agua":"water",
           "primeiros":"first aid", "socorros":"aid", "queimadura":"burn",
           "picada":"bite snake", "cobra":"snake", "engasgo":"choking",
           "febre":"fever", "ferida":"wound", "sangrando":"bleeding"}
    words = norm(q).split()
    expanded = []
    for w in words:
        expanded.append(w)
        expanded.extend(EXP.get(w, "").split())
    fts = " OR ".join(dict.fromkeys(expanded)) or "water"
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=10)
    try:
        rows = c.execute(
            "select title, body, source, license, bm25(docs) as s "
            "from docs where docs match ? order by s limit ?", (fts, limit)).fetchall()
    except Exception:
        rows = []
    finally:
        c.close()
    return rows


def clean(body):
    body = re.sub(r"\*\*Autor:\*\*[^\n]*", " ", body)
    body = re.sub(r"\*\*Páginas:\*\*[^\n]*", " ", body)
    body = re.sub(r"## Page \d+", " ", body)
    body = re.sub(r"#{1,4}\s*", "", body)
    body = re.sub(r"\s+", " ", body)
    return body.strip()


def answer(q, limit=3):
    rows = search(q, limit)
    if not rows:
        return f"SEM FONTE LOCAL para: {q}\nNao vou inventar resposta."
    # pontuao com raizes PT+EN (as mesmas do FTS), nao so as palavras da pergunta
    qn = set(norm(q).split())
    EXP = {"purificar":"purifying distillation treatment", "agua":"water",
           "primeiros":"first aid", "socorros":"aid", "queimadura":"burn",
           "picada":"bite snake", "cobra":"snake", "engasgo":"choking",
           "febre":"fever", "ferida":"wound", "sangrando":"bleeding"}
    for w in list(qn):
        qn.update(EXP.get(w, "").split())
    out = [f"RESPOSTA OFFLINE (sem internet) — {q}"]
    for title, body, source, license_, score in rows:
        txt = clean(body)
        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", txt) if len(s.strip()) > 35]
        ranked = sorted(sents, key=lambda s: -len(qn & set(norm(s).split())))[:3]
        out.append(f"\n[{title}] fonte: {source} · {license_}")
        for s in ranked:
            out.append("  • " + (s[:360] + "…" if len(s) > 360 else s))
    out.append("\nNota: extracao literal do corpus local. Para sintese em linguagem natural, "
               "configure um GGUF local em TA_LOCAL_MODEL_URL.")
    return "\n".join(out)


if __name__ == "__main__":
    print(answer(" ".join(sys.argv[1:]) or "como purificar agua"))
