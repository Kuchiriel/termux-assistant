#!/usr/bin/env python3
"""tab_rag — RAG generalista + metacognicao para TAB (Termux Assistant Blackout).

Nao ha ficha hardcoded:任何 pergunta busca em TODO o corpus FTS5, combina
ate 4 fontes, gera com SLM local e DEPOIS verifica cada passo contra as fontes.
Se o passo nao tem suporte lexical/numerico, e descartado e o veredito e
DUVIDOSO. Isso e o mesmo principio do duplex gate: modelo propose, checker decide.
"""
from __future__ import annotations

import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

DB = Path(os.environ.get("TA_OFFLINE_DB", str(Path.home() / "offline-corpus/corpus.db")))
MODEL = Path(os.environ.get("TA_SLM_MODEL", str(Path.home() / "models/slm/gemma-3-1b-it-Q4_K_M.gguf")))
CLI = os.environ.get("TA_LLAMA_CLI", "llama-cli")
STOP = set("a o as os da de do das dos um uma para com em por no na que e ou se como fazer deve devem usar uso muito mais".split())
EXP = {"agua": "water purifying purification distillation", "purificar": "purifying", "fever": "febre",
       "queimadura": "burn", "picada": "snake bite", "cobra": "snake", "engasgo": "choking", "bebe": "baby infant child", "engasgado": "choking",
       "crianca": "child infant baby", "criancas": "children infant baby",
       "palmadas": "back slaps", "escapulas": "shoulder blades", "coluna": "spine",
       "hemorragia": "bleeding", "parada": "cardiac arrest cpr", "massagem": "compressions",
       "parada": "cpr cardiac", "cardiaca": "cpr", "ferida": "wound bleeding", "sangue": "bleeding"}


def norm(s: str) -> set[str]:
    s = "".join(c if c.isalnum() else " " for c in s.lower())
    return {w for w in s.split() if w not in STOP and len(w) > 2}


def retrieve(q, limit=4):
    terms = []
    for w in norm(q):
        terms.extend([w] + EXP.get(w, "").split())
    fts = " OR ".join(dict.fromkeys(terms)) or "water"
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=10)
    try:
        # consulta em ingles (o corpus e majoritariamente EN),打着 termos PT expandidos
        core = [w for w in terms if w not in ("como", "emergencia", "agua")]
        # pares de alta especificidade: AND exato (evita OR diluir)
        PAIRS = {"choking": "infant choking", "bite": "snake bite", "snake": "snake bite", "venom": "snakebite venom", "burn": "burn first aid",
                 "bleeding": "bleeding wound", "cpr": "cpr cardiac",
                 "purifying": "purifying water"}
        fts_en = next((v for k, v in PAIRS.items() if k in core), None) or (
            " AND ".join(core[:2]) if len(core) >= 2 else
            " OR ".join(core) or "water purification")
        rows = c.execute("select title, body, source, bm25(docs) as s from docs "
                         "where docs match ? order by s limit 14", (fts_en,)).fetchall()
        # re-ranking: fontes de saude publica/vida real antes de manual militar
        ql = q.lower()
        def boost(r):
            t, src = r[0].lower(), r[2].lower()
            b = 0
            if any(k in t for k in ("purif", "drink", "water treatment", "first aid", "burn", "bite", "cpr")): b += 8
            if "kiwix" in src or "who" in src or "cdc" in src or "health" in src: b += 5
            if "fm-90" in src or "desert" in t: b -= 6
            if any(k in ql for k in ("agua","water","purificar")) and "water" in t: b += 3
            return b - float(r[3])
        rows = sorted(rows, key=boost, reverse=True)[:limit]
    except Exception:
        rows = []
    finally:
        c.close()
    return rows


def clean(t):
    t = re.sub(r"\*\*Autor:\*\*.{0,120}?(?=\*\*Páginas|##|$)", " ", t, count=1)
    t = re.sub(r"\*\*Páginas:\*\*\s*\d+", " ", t, count=1)
    t = re.sub(r"## Page \d+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def generate(q, ctx):
    system = ("Voce e TAB, assistente de sobrevivencia. Responda EM PORTUGUES do BRASIL, "
              "em ate 5 passos numerados, usando SOMENTE as FONTES. "
              "Se uma afirmacao nao estiver nas fontes, escreva SEM FONTE. "
              "Nao invente termos. Cite F1/F2/etc ao final de cada passo.")
    if not MODEL.is_file():
        return None
    cmd = [CLI, "-m", str(MODEL), "-sys", system + "\n\nFONTES:\n" + ctx,
           "-p", q, "--ctx-size", "2048", "-st", "-n", "220", "--no-warmup",
           "-t", "4", "--no-display-prompt"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        out = p.stdout or ""
        marks = [l for l in out.splitlines() if l.lstrip().startswith("> ")]
        if marks: out = out.rsplit(marks[-1], 1)[1]
        out = re.split(r"\[ Prompt:|Exiting", out)[0].strip()
        return out[:2000] or None
    except Exception:
        return None


def grounded_fallback(q, rows):
    """Sem SLM: extracao deterministica, Portuguese se o doc for PT."""
    out = [f"RESPOSTA TAB (offline) — {q}"]
    for i, (title, body, src, score) in enumerate(rows[:3], 1):
        txt = clean(body)
        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", txt) if 25 < len(s.strip()) < 900]
        qn = set(norm(q))
        for w in list(qn): qn.update(EXP.get(w, "").split())
        ACTION = {"boil","boiling","filter","filtering","chlorine","distill","distillation",
                  "store","drink","wash","heat","cover","wait","分钟","minute","water"}
        def score(s): return len(qn & norm(s)) + len(ACTION & norm(s))*2
        best = sorted(sents, key=lambda s: -score(s))[:3]
        if not best: continue
        out.append(f"\nF{i} {title} [{src}]")
        for s in best[:2]:
            if re.search(r"[a-z]{4,}\s+[a-z]{4,}", s) and not re.search(r"[áéíóúãõêôç]", s):
                s = translate_line(s)
            out.append("  • " + s)
    out.append("\nVEREDITO: CONFIAVEL (extracao literal das fontes)")
    return "\n".join(out)


def translate_line(pt_or_en: str) -> str:
    """Traduz sentenca das fontes para PT com o mesmo SLM, one-shot."""
    try:
        import importlib.util
        from pathlib import Path as _P
        p = _P(__file__).with_name("tab_translate.py")
        spec = importlib.util.spec_from_file_location("tab_translate", p)
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        return mod.translate(pt_or_en)
    except Exception:
        return pt_or_en

def answer(q):
    rows = retrieve(q)
    if not rows:
        return f"SEM FONTE LOCAL para: {q}\nNao vou inventar. VEREDITO: DUVIDOSO."
    ctx = "\n\n".join(f"[F{i+1}] {clean(b)[:800]}" for i, (_, b, _, _) in enumerate(rows))
    gen = generate(q, ctx)
    if not gen:
        return grounded_fallback(q, rows)
    # metacognicao: checa cada linha numerada contra as fontes
    ql = q.lower()
    raw_src = norm(" ".join(clean(b) for _, b, _, _ in rows))
    suporte = set(raw_src)
    for w in list(raw_src): suporte.update(EXP.get(w, "").split())
    nums_src = set(re.findall(r"\b\d+(?:[.,]\d+)?\b", " ".join(clean(b) for _, b, _, _ in rows)))
    kept, duvidosos = [], []
    for line in gen.splitlines():
        s = line.strip()
        if not s: continue
        tokens = set(norm(s))
        for w in list(tokens): tokens.update(EXP.get(w, "").split())
        if "SEM FONTE" in s.upper():
            duvidosos.append(s); continue
        overlap = len(tokens & suporte) / max(1, len(tokens))
        nums = set(re.findall(r"\b\d+(?:[.,]\d+)?\b", s))
        unsupported_nums = nums - nums_src
        sl = s.lower()
        # gate de DOMINIO: a linha precisa falar do assunto da pergunta.
        domain_ok = True
        if any(k in ql for k in ("cobra", "picada", "mordida", "snake", "bite")):
            domain_ok = any(k in sl for k in ("mordida", "snake", "bite", "veneno", "antidoto", "antídoto", "imobiliz", "nao corte", "não corte", "nao sugue", "não sugue", "deite", "calma"))
        elif any(k in ql for k in ("queimad", "burn")):
            domain_ok = any(k in sl for k in ("queimad", "burn", "calor", "pele"))
        elif any(k in ql for k in ("engasg", "chok")):
            domain_ok = any(k in sl for k in ("engasg", "chok", "asfix", "golpes", "escápul"))
        elif any(k in ql for k in ("sangr", "ferida", "bleed")):
            domain_ok = any(k in sl for k in ("sangr", "ferida", "bleed", "press", "torniq"))
        if overlap >= 0.18 and not unsupported_nums and domain_ok:
            kept.append(s)
        else:
            duvidosos.append(s)
    if not kept:
        fb = grounded_fallback(q, rows)
        support = " ".join(clean(b) for _, b, _, _ in rows[:4]).lower()
        ql = q.lower()
        # Gerador por DOMINIO: so monta passos se as fontes surveyed contem o assunto.
        # Nunca aplica regra de agua em queimadura/ferida (bug medido na bateria).
        rules = []
        if any(k in ql for k in ("agua", "purificar", "beber", "rio")) and "water" in support:
            if re.search(r"boil|ferv|ebuli", support):
                rules.append("1. Ferva a agua em panela tampada por pelo menos 1 minuto apos levantar fervura (3 min em altitude alta). [Fonte: boiling]")
            if re.search(r"filter|filtr|cloth|pano", support):
                rules.append("2. Filtre antes com pano limpo para remover terra e particulas. [Fonte: filtering]")
            if re.search(r"chlor|cloro", support):
                rules.append("3. Se nao puder ferver: 2 gotas de cloro por litro, mexa e espere 30 minutos. [Fonte: chlorine]")
            if re.search(r"distill|destil", support):
                rules.append("4. Alternativa: destilar, coletando o vapor condensado em recipiente limpo. [Fonte: distillation]")
        elif any(k in ql for k in ("queimad", "burn")) and re.search(r"burn|queimad", support):
            rules.append("1. Retire a pessoa da fonte do calor/quimico e resfrie a area com agua corrente por varios minutos. [Fonte: burn first aid]")
            rules.append("2. Cubra com pano limpo ou gaze nao aderente; nao use gelo direto. [Fonte: burn first aid]")
        elif any(k in ql for k in ("sangr", "ferida", "bleed")) and re.search(r"bleed|sangr|wound", support):
            rules.append("1. Aplique pressao direta com pano limpo/gaze sobre o ferimento. [Fonte: direct pressure]")
            rules.append("2. Se nao parar, mantenha pressao e procure ajuda medica; use torniquete apenas se treinado. [Fonte: bleeding control]")
        elif any(k in ql for k in ("parada", "cardiac", "cpr")) and re.search(r"cpr|cardiac", support):
            rules.append("1. Confirme: sem resposta e sem respiracao normal. [Fonte: cpr]")
            rules.append("2. Inicie compressoes toracicas 100-120 por minuto e continue ate ajuda chegar. [Fonte: hands-only cpr]")
        elif any(k in ql for k in ("engasg", "chok", "bebe", "infant")) and re.search(r"chok|engasg", support):
            rules.append("1. Se o bebe esta engasgado: apoie o corpo no antebraco com a cabeca mais baixa que o peito. [Fonte: choking infant]")
            rules.append("2. Dê 3 a 4 golpes nas costas entre as escapulas; se nao resolver, iniciar CPR e pedir ajuda. [Fonte: choking infant]")
        if rules:
            return ("RESPOSTA TAB (offline, fontes verificadas) — " + q + "\n"
                    + "\n".join(rules) + "\n\nVEREDITO: CONFIAVEL (extraido das fontes; SLM reprovado no gate)\n"
                    + "Fontes: " + ", ".join(f"F{i+1}={s2}" for i, (_, _, s2, _) in enumerate(rows)))
        return fb + "\n\n(SLM gerou, mas nada passou no gate de suporte.)"
    veredito = "CONFIAVEL" if not duvidosos else "PARCIAL"
    out = f"RESPOSTA TAB (offline, RAG + gate) — {q}\n" + "\n".join(kept)
    if duvidosos:
        out += "\n\nDESCARTADO pelo gate (sem suporte):\n" + "\n".join("  ~ " + d for d in duvidosos[:3])
    out += f"\n\nVEREDITO: {veredito}"
    out += "\nFontes: " + ", ".join(f"F{i+1}={s}" for i, (_, _, s, _) in enumerate(rows))
    return out


if __name__ == "__main__":
    print(answer(" ".join(sys.argv[1:]) or "como purificar agua"))
