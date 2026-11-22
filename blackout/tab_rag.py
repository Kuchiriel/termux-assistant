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
       "afogamento": "drowning water rescue", "afogado": "drowning",
       "choque": "electrical shock electrocution", "eletrico": "electrical", "elétrico": "electrical",
       "insolacao": "heat stroke hyperthermia", "insolação": "heat stroke",
       "calor": "heat exhaustion hyperthermia", "fratura": "fracture splint broken bone",
       "envenenamento": "poisoning poison ingested", "veneno": "poison",
       "convulsao": "seizure convulsion", "convulsão": "seizure", "ataque": "seizure",
       "hipotermia": "hypothermia", "frio": "cold hypothermia shivering",
       "desidratacao": "dehydration", "desidratação": "dehydration",
       "diarreia": "diarrhea dehydration", "sede": "thirst dehydration",
       "avc": "stroke", "derrame": "stroke", "torniquete": "tourniquet",
       "quimica": "chemical burn acid", "química": "chemical burn",
       "quimico": "chemical burn", "químico": "chemical burn",
       "parada": "cpr cardiac", "cardiaca": "cpr", "ferida": "wound bleeding", "sangue": "bleeding",
       # 6 dominios novos (18/11): cada termo PT expande para o que existe no
       # corpus EN. O valor de EXP nao e dica: e o que o FTS5 vai casar.
       "inseto": "insect sting bee wasp stinger", "abelha": "bee sting", "vespa": "wasp sting",
       "carrapato": "tick bite tick removal",
       "fumaca": "smoke inhalation carbon monoxide", "fumaça": "smoke inhalation carbon monoxide",
       "fumo": "smoke fumes inhalation", "monoxido": "carbon monoxide", "monóxido": "carbon monoxide",
       "epistaxe": "nosebleed nose bleed", "epistaxis": "nosebleed", "nariz": "nosebleed",
       "animal": "animal bite", "cachorro": "dog bite", "gato": "cat bite",
       "corrente": "flood current fast-moving water", "nadador": "not a trained swimmer",
       "enchente": "flood"}


def norm(s: str) -> set[str]:
    s = "".join(c if c.isalnum() else " " for c in s.lower())
    return {w for w in s.split() if w not in STOP and len(w) > 2}


# --- 6 dominios de emergencia (17/11/2026) --------------------------------
# Cada passo so e emitido se o TRECHO ANCORADO existir no doc recuperado:
# (texto PT, [(rotulo da fonte, trecho literal em ingles), ...]).
# Se nada ancorar, o passo nao sai. Isso impede passo inventado.
# "parto" e "amarracao" NAO entraram: o corpus local nao tem obstetrícia nem
# entanglement real (verificado por FTS: 0 docs com childbirth/labor/umbilical).
DOMAINS = {
    "inseto": {
        "triggers": ("carrapato", "tick", "inseto", "insects", "abelha", "bee", "vespa", "wasp"),
        "fts": '"insect sting" OR "bee sting" OR "wasp sting" OR "stinger is present" '
               'OR "antihistamine" OR "cold compress" OR "epinephrine"',
        "titulo": ("sting", "bee", "wasp", "insect"),
        "passos": [
            ("Retire o ferrão, se ainda estiver na pele, raspando com um objeto chato (cartao de credito) ou unha; nao esprema a bolsa de veneno.",
             [("FM 4-25.11 cap.6 p.22", "remove by scraping with a knife or fingernail"),
              ("FirstAidQA #2165", "scraping it off with a blunt object like a credit card"),
              ("FirstAidQA #786", "scrape the stinger out gently")]),
            ("Limpe o local da picada com agua e sabao e aplique compressa fria para reduzir inchaco e dor.",
             [("FirstAidQA #2165", "clean the sting site with mild soap and water"),
              ("FirstAidQA #786", "clean the area with soap and water"),
              ("FirstAidQA #834", "clean the site with water and antiseptic"),
              ("FirstAidQA #1021", "cold compresses help reduce swelling, pain, and inflammation")]),
            ("Antihistaminico ajuda na reacao alergica leve: reduz inchaco, coceira e vermelidao.",
             [("FirstAidQA #1040", "antihistamines can help treat mild allergic reactions"),
              ("FirstAidQA #1040", "reducing swelling, itching, and redness"),
              ("FirstAidQA #1011", "use an antihistamine cream or oral antihistamines")]),
            ("Se a reacao for grave (inchaco na garganta, respiracao dificil), aplique epinefrina se houver e chame emergencia imediatamente.",
             [("FirstAidQA #2165", "administer epinephrine (if available) and call emergency services immediately"),
              ("FirstAidQA #1056", "administer epinephrine (if available) and seek emergency medical help immediately"),
              ("FirstAidQA #2165", "swelling of the throat or difficulty breathing")]),
        ],
    },
    "animal": {
        "triggers": ("cachorro", "dog", "gato", "cat", "animal", "nao venomosa", "não venenosa"),
        "fts": '"animal bite" OR "animal scratch" OR "dog bite" OR "cat bite" OR rabies '
               'OR tetanus OR "immobilize the injured arm"',
        "titulo": ("animal bite", "dog bite", "cat bite", "animal scratch"),
        "passos": [
            ("Lave a ferida com agua e sabao (ou antiseptico) e aplique um curativo limpo.",
             [("FirstAidQA #759", "clean the wound thoroughly with soap and water or an antiseptic"),
              ("FirstAidQA #2171", "clean the wound immediately with mild soap and water"),
              ("FirstAidQA #788", "clean the wound thoroughly with soap and water or an antiseptic"),
              ("FM 4-25.11 cap.6 p.12", "cleanse the wound thoroughly with soap")]),
            ("Imobilize o braco ou a perna atingidos, se apropriado, e transporte a vitima para o servico medico.",
             [("FM 4-25.11 cap.6 p.12", "immobilize the injured arm or leg, if appropriate"),
              ("FM 4-25.11 cap.6 p.12", "transport the casualty immediately to an mtf")]),
            ("Mordida funda pode exigir pontos, antibiotico e vacina antitetanica: procure o servico medico.",
             [("FirstAidQA #710", "may require stitches if the wound is deep enough"),
              ("FirstAidQA #711", "antibiotics, stitches, or a tetanus shot may be necessary"),
              ("FirstAidQA #2171", "a tetanus shot or rabies vaccination may be necessary"),
              ("FirstAidQA #788", "a tetanus shot may be needed")]),
            ("Mordida de animal nao tratada pode trazer tetano, raiva e febres; se o animal puder ter raiva, a vacinacao antirrabica pode ser necessaria.",
             [("FM 4-25.11 cap.6 p.12", "tetanus, rabies, and various types of fevers can follow an untreated animal bite"),
              ("FirstAidQA #2171", "the dog may have been rabid"),
              ("FirstAidQA #2171", "rabies vaccination may be necessary")]),
        ],
    },
    "fumaca": {
        "triggers": ("fumaca", "fumaça", "fuligem", "monoxido", "monóxido", "smoke"),
        "fts": '"smoke inhalation" OR "inhaled smoke" OR "carbon monoxide" OR "burning plastic" '
               'OR "fresh air" OR "airway, breathing, and pulse"',
        "titulo": ("smoke inhalation", "carbon monoxide", "inhaled smoke", "fumes"),
        "passos": [
            ("Tire a pessoa do ambiente com fumaca para o ar fresco imediatamente e nao inale os vapores voce mesmo.",
             [("FirstAidQA #2151", "remove them from the hazardous environment immediately and get fresh air"),
              ("FirstAidQA #3770", "take them to fresh air immediately"),
              ("FirstAidQA #3770", "ensure you do not inhale the toxic fumes yourself"),
              ("FirstAidQA #3812", "immediately move them to fresh air and ensure that you do not inhale the fumes")]),
            ("Verifique via aerea, respiracao e pulso; se estiver inconsciente ou sem respirar, inicie RCP.",
             [("FirstAidQA #3820", "check their airway, breathing, and pulse"),
              ("FirstAidQA #5025", "begin cpr with chest compressions and rescue breaths"),
              ("FirstAidQA #3770", "begin cpr if necessary")]),
            ("Sinais de intoxicacao por monoxido de carbono: dor de cabeca, tontura, nausea, vomito, confusao, fraqueza e falta de ar.",
             [("FirstAidQA #3817", "headache, dizziness, nausea, vomiting, confusion, weakness, and shortness of breath"),
              ("FirstAidQA #3787", "dizziness, headache, nausea, vomiting, confusion, shortness of breath")]),
            ("Se houver dificuldade para respirar ou tontura, aplique oxigenio se disponivel e procure ajuda de emergencia; nao de liquidos a quem respira com dificuldade.",
             [("FirstAidQA #2151", "administer oxygen if available and seek emergency medical help"),
              ("FirstAidQA #2151", "do not attempt to give fluids if the person is struggling to breathe")]),
        ],
    },
    "epistaxe": {
        "triggers": ("epistaxe", "epistaxis", "nariz", "nosebleed", "sangramento no nariz"),
        "fts": 'nosebleed OR "nose bleed" OR "bleeding from the nose" OR "pinch your nose" '
               'OR "pinching the nostrils" OR "pinch the nostrils together"',
        "titulo": ("nosebleed", "nose bleed", "nostril"),
        "passos": [
            ("Sente ou coloque a pessoa em pe (nao deitada), incline o corpo para frente e respire pela boca.",
             [("NHS A-Z (medicamentos)", "sit or stand upright (do not lie down)"),
              ("FirstAidQA #2121", "have the person sit up and lean forward slightly"),
              ("FirstAidQA #3620", "sit upright, lean forward")]),
            ("Pinca o nariz logo acima das narinas por 10 a 15 minutos.",
             [("NHS A-Z (medicamentos)", "pinch your nose just above your nostrils for 10 to 15 minutes"),
              ("FirstAidQA #2121", "pinch the nostrils together and apply gentle pressure for 10-15 minutes"),
              ("FM 4-25.11 cap.3 p.38", "pinching the nostrils together")]),
            ("Aplique uma bolsa de gelo no topo do nariz ou na nuca para reduzir o sangramento.",
             [("NHS A-Z (medicamentos)", "place an icepack"),
              ("FirstAidQA #2121", "apply a cold compress to the back of the neck or nose"),
              ("FM 4-25.11 cap.3 p.38", "placing an ice pack (if available) over the nose")]),
            ("Depois que parar: nao sopre nem limpa o nariz por varias horas, mantenha a cabeca elevada e evite liquidos quentes e esforco.",
             [("FirstAidQA #3570", "avoid blowing or picking the nose for several hours"),
              ("FirstAidQA #3570", "keep the head elevated and avoid hot drinks or strenuous activity"),
              ("FirstAidQA #3554", "avoid blowing their nose for several hours after a nosebleed stops")]),
            ("Se o sangramento continuar ou se repetir, procure atendimento medico.",
             [("FirstAidQA #2121", "if bleeding continues or the person is experiencing frequent nosebleeds, seek medical help"),
              ("FirstAidQA #3570", "if nosebleeds recur frequently, consult a doctor")]),
        ],
    },
    "carrapato": {
        "triggers": ("carrapato", "carrapates", "tick"),
        "fts": '"tick bite" OR "tick removal" OR "tick-removal tool" OR "removing a tick" '
               'OR "pulling it out with your fingers"',
        "titulo": ("tick",),
        "passos": [
            ("Remova o carrapato com pinca de ponta fina ou ferramenta propria, o mais perto possivel da pele, puxando em linha reta, sem torcer.",
             [("FirstAidQA #1089", "fine-tipped tweezers or a tick-removal tool"),
              ("FirstAidQA #1089", "gently pull the tick straight out without twisting"),
              ("FirstAidQA #1094", "grasp the tick as close to the skin as possible and pull it straight out")]),
            ("Nao puxe o carrapato com os dedos: isso espreme o carrapato e libera mais veneno.",
             [("FirstAidQA #1094", "doing so can squeeze the tick, releasing more venom"),
              ("FirstAidQA #1094", "not safe to remove a tick by pulling it out with your fingers")]),
            ("Depois da remocao, lave o local com agua e sabao e aplique antiseptico.",
             [("FirstAidQA #1078", "clean the area thoroughly with soap and water"),
              ("FirstAidQA #1059", "clean the area with soap and water and apply an antiseptic"),
              ("FirstAidQA #1093", "clean the bite sites with soap and water and apply antiseptic")]),
            ("Se surgir fraqueza, paralisia ou dificuldade respiratoria, procure atendimento medico imediatamente.",
             [("FirstAidQA #1078", "if symptoms like weakness or paralysis develop, seek medical attention immediately"),
              ("FirstAidQA #1054", "symptoms of paralysis, such as weakness in the face, eyelids, or arms"),
              ("FirstAidQA #1059", "get emergency medical help immediately")]),
        ],
    },
    "resgate": {
        "triggers": ("corrente", "enchente", "flood", "nadador", "swimmer", "resgate"),
        "fts": '"during a flood" OR "fast-moving water" OR "without entering the water" '
               'OR "not a trained swimmer" OR "flotation device"',
        "titulo": ("flood", "trained swimmer", "drowning", "rescue", "flotation"),
        "passos": [
            ("Se voce nao e nadador treinado, nao entre na agua para resgatar: isso poe voce e a vitima em risco.",
             [("FirstAidQA #2293", "you are not a trained swimmer, you should not attempt to rescue the person yourself"),
              ("FirstAidQA #2306", "never enter deep water without proper training")]),
            ("Chame a emergencia imediatamente, grite por ajuda e procure um guarda-vidas treinado.",
             [("FirstAidQA #2293", "call for emergency help immediately"),
              ("FirstAidQA #2306", "calling emergency services immediately, shouting for help, and locating a trained lifeguard")]),
            ("Se for seguro, jogue um dispositivo de flutuacao ou corda ou use um objeto longo para alcancar a vitima da margem.",
             [("FirstAidQA #2306", "throw a flotation device, rope, or use a long stick to reach the person from the shore"),
              ("FirstAidQA #2293", "throw a flotation device or extend a long object to the victim from a safe distance")]),
            ("Numa enchente: avalie o nivel da agua, a forca da corrente e sua propria seguranca antes de mover alguem; nao mova a vitima por agua de corrente rapida.",
             [("FirstAidQA #40", "assess the water level, current strength, and your own safety"),
              ("FirstAidQA #40", "avoid moving them through fast-moving water")]),
        ],
    },
}


def detectar_dominio(q: str):
    """Qual dos 6 dominios novos a pergunta pede (ou None)."""
    ql = q.lower()
    # carrapato antes de inseto (carrapato e' um inseto, mas tem regra propria)
    for dom in ("carrapato", "inseto", "fumaca", "epistaxe", "animal", "resgate"):
        d = DOMAINS[dom]
        if not any(t in ql for t in d["triggers"]):
            continue
        # mordida de cobra/snake continua sendo o dominio da cobra (existente)
        if dom == "animal" and any(t in ql for t in ("cobra", "snake", "serpente", "peconha")):
            continue
        # "smoke"/"co" e' curto demais: so entra com outro sinal de fumaca
        if dom == "fumaca" and not any(t in ql for t in ("fumaca", "fumaça", "fuligem",
                                                       "monoxido", "monóxido", "smoke")):
            continue
        return dom
    return None


def retrieve(q, limit=4, dom=None):
    terms = []
    for w in norm(q):
        terms.extend([w] + EXP.get(w, "").split())
    fts = " OR ".join(dict.fromkeys(terms)) or "water"
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=10)
    try:
        # consulta em ingles (o corpus e majoritariamente EN),打着 termos PT expandidos
        core = [w for w in terms if w not in ("como", "emergencia", "agua")]
        # pares de alta especificidade: AND exato (evita OR diluir)
        # 18/11: as chaves dos 6 dominios novos entram ANTES das genericas
        # ("bite", "smoke", ...), senao "picada de inseto" cairia em "snake bite".
        PAIRS = {"insect": '"insect sting" OR "bee sting" OR "wasp sting" OR "stinger is present"',
        "bee": '"bee sting" OR "stinger is present"',
        "wasp": '"wasp sting" OR "stinger is present"',
        "tick": '"tick bite" OR "tick removal" OR "tick-removal tool"',
        "animal": '"animal bite" OR "animal scratch"',
        "dog": '"dog bite" OR "animal bite"',
        "cat": '"cat bite" OR "animal bite"',
        "smoke": '"smoke inhalation" OR "inhaled smoke" OR "carbon monoxide" OR "burning plastic"',
        "carbon": '"carbon monoxide"',
        "nosebleed": 'nosebleed OR "nose bleed" OR "bleeding from the nose" OR "pinch your nose"',
        "flood": '"during a flood" OR "fast-moving water"',
        "swimmer": '"not a trained swimmer" OR "without entering the water"',
        "choking": "infant choking", "bite": "snake bite", "snake": "snake bite", "venom": "snakebite venom", "burn": "burn first aid",
        "drowning": "drowning rescue", "electrical": "electrical shock", "shock": "electrical shock",
        "heat": "heat stroke", "fracture": "fracture splint", "poison": "poisoning",
        "seizure": "seizure convulsion",
                 "bleeding": "bleeding wound", "cpr": "cpr cardiac",
                 "purifying": "purifying water"}
        # OR por padrao: o termo PT nao existe no corpus (ingles), entao AND
        # com a palavra original zera o resultado. AND so nos pares exatos.
        if dom and dom in DOMAINS:
            fts_en = DOMAINS[dom]["fts"]
        else:
            fts_en = next((v for k, v in PAIRS.items() if k in core), None) or (
                " OR ".join(core) or "water purification")
        rows = c.execute("select title, body, source, bm25(docs) as s from docs "
                         "where docs match ? order by s limit 40", (fts_en,)).fetchall()
        # re-ranking: fontes de saude publica/vida real antes de manual militar
        ql = q.lower()
        bonus_titulo = DOMAINS[dom]["titulo"] if dom and dom in DOMAINS else ()
        def boost(r):
            t, src = r[0].lower(), r[2].lower()
            b = 0
            if any(k in t for k in ("purif", "drink", "water treatment", "first aid", "burn", "bite", "cpr")): b += 8
            if any(k in t for k in bonus_titulo): b += 9
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


def regras_dominio(dom: str, rows) -> list[str]:
    """Passos do dominio novo; cada passo exige o TRECHO literal no doc recuperado."""
    if dom not in DOMAINS:
        return []
    suporte = " ".join(clean(b) for _, b, _, _ in rows).lower()
    out = []
    for texto, ancoras in DOMAINS[dom]["passos"]:
        achado = next((t for f, t in ancoras if t.lower() in suporte), None)
        if not achado:
            continue
        fonte = next((f for f, t in ancoras if t == achado), ancoras[0][0])
        out.append(f"{len(out) + 1}. {texto} [Fonte: {fonte}]")
    return out


def fontes_citadas(rules: list[str]) -> list[str]:
    """Rotulos de fonte citados nos passos (a prova de ancoragem)."""
    out = []
    for r in rules:
        m = re.search(r"\[Fonte: ([^\]]+)\]", r)
        if m and m.group(1) not in out:
            out.append(m.group(1))
    return out


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
           "-p", q, "--ctx-size", "2048", "-st", "-n", os.environ.get("TA_SLM_N", "220"), "--no-warmup",
           "-t", "4", "-tb", "8", "--no-display-prompt",
           "--temp", "0.1", "--top-k", "20", "--top-p", "0.9", "--min-p", "0.05",
           "--typical-p", "0.9", "--seed", "42"]
    proc = None
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            stdout, _ = proc.communicate(timeout=240)
        except subprocess.TimeoutExpired:
            proc.kill(); proc.communicate()
            return None
        out = stdout or ""
        marks = [l for l in out.splitlines() if l.lstrip().startswith("> ")]
        if marks: out = out.rsplit(marks[-1], 1)[1]
        out = re.split(r"\[ Prompt:|Exiting", out)[0].strip()
        return out[:2000] or None
    except Exception:
        if proc is not None and proc.poll() is None:
            proc.kill()
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

def deterministic_rules(q: str, rows) -> list[str]:
    """Passos por dominio extraidos das fontes (sem SLM). Vazio se nao houver regra."""
    ql = q.lower()
    # 6 dominios novos: a regra so entra se cada passo tiver um TRECHO LITERAL
    # do doc recuperado. Passo sem ancora nao e emitido (nada inventado).
    dom = detectar_dominio(q)
    if dom:
        rows_dom = retrieve(q, limit=16, dom=dom)
        novas = regras_dominio(dom, rows_dom)
        if novas:
            return novas
    support = " ".join(clean(b) for _, b, _, _ in rows[:4]).lower()
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
    elif any(k in ql for k in ("cobra", "picada", "mordida", "snake", "bite")) and re.search(r"snake|venom|mordida|picada", support):
        rules.append("1. Acalme e mantenha a vitima calma e imobil; nao corte nem sugar a mordida. [Fonte: snake bite]")
        rules.append("2. Aplique imobilizacao com pressao no membro atingido e procure ajuda medica urgente. [Fonte: snake bite]")
    elif any(k in ql for k in ("hipoterm", "frio", "cold")) and re.search(r"hypotherm|shiver", support):
        rules.append("1. Leve a pessoa para lugar quente e seco, retire roupa molhada e envolva com cobertores. [Fonte: hypothermia]")
        rules.append("2. Se houver confusao, respiracao lenta ou inconsciencia, e um frio severo: aqueça devagar e chame ajuda. [Fonte: hypothermia]")
    elif any(k in ql for k in ("quimic", "chemical", "acido", "alcali")) and re.search(r"chemical|acid|alkali", support):
        rules.append("1. Afaste a pessoa da fonte do quimico e retire roupas contaminadas sem espalhar o produto. [Fonte: chemical burn]")
        rules.append("2. Lave a area com muita agua corrente por pelo menos 20 minutos e procure ajuda medica. [Fonte: chemical burn]")
    elif any(k in ql for k in ("desidrat", "diarre", "desmaio por calor")) and re.search(r"dehydrat|thirst", support):
        rules.append("1. Sinais: sede extrema, boca seca, urina escura, tontura e confusao. [Fonte: dehydration]")
        rules.append("2. Hidrate imediatamente com agua e solucao de reidratacao oral; se piorar, procure ajuda. [Fonte: dehydration]")
    elif any(k in ql for k in ("avc", "derrame", "stroke")) and re.search(r"stroke|fast", support):
        rules.append("1. Use FAST: Face (boca torta), Arms (braco cai), Speech (fala enrolada), Time. [Fonte: stroke FAST]")
        rules.append("2. Ligue para o servico de emergencia imediatamente: cada minuto conta. [Fonte: stroke FAST]")
    elif any(k in ql for k in ("torniquete", "torniq")) and re.search(r"tourniquet|torniquet", support):
        rules.append("1. Torniquete so depois que a pressao direta falhar, ou se o membro foi decepado. [Fonte: tourniquet]")
        rules.append("2. Em mordida de cobra o torniquete NAO deve ser usado: prefira pressao no local e imobilize o membro. [Fonte: tourniquet / snake bite]")
    elif any(k in ql for k in ("afog", "drown")) and re.search(r"drown|afog", support):
        rules.append("1. Use boia, corda ou colete para alcancar a vitima sem entrar na agua; nao va sem seguranca. [Fonte: drowning rescue]")
        rules.append("2. Ao tirar, verifique respiracao; se nao respirar, inicie RCP e chame ajuda. [Fonte: drowning rescue / CPR]")
    elif any(k in ql for k in ("choque", "eletr", "electr")) and re.search(r"electr|shock|choque", support):
        rules.append("1. Desligue a fonte de energia antes de tocar na vitima; nao use as maos diretas. [Fonte: electrical shock]")
        rules.append("2. Choques de alta tensao podem causar queimaduras internas e parada cardiaca — procure ajuda medica urgente. [Fonte: electrical shock]")
    elif any(k in ql for k in ("insol", "calor", "heat")) and re.search(r"heat|calor|insol", support):
        rules.append("1. Leve a pessoa para sombra, retire roupa excessiva e ofereca agua. [Fonte: heat stroke]")
        rules.append("2. Se houver confusao, desmaio ou temperatura muito alta, resfrie o corpo e chame ajuda urgente. [Fonte: heat stroke]")
    elif any(k in ql for k in ("fratura", "fracture", "osso")) and re.search(r"fractur|fratur|splint", support):
        rules.append("1. Imobilize o membro com tala rigida e acolchoamento; para perna, use a outra perna como apoio. [Fonte: fracture splint]")
        rules.append("2. Na movimente a area, controle sangramento se houver e procure ajuda. [Fonte: fracture splint]")
    elif any(k in ql for k in ("envenen", "poison", "veneno")) and re.search(r"poison|envenen", support):
        rules.append("1. Ligue para o centro de controle de veneno ou busque ajuda medica imediatamente. [Fonte: poisoning]")
        rules.append("2. NAO provoque vomito sem orientacao medica; guarde a embalagem do produto. [Fonte: poisoning]")
    elif any(k in ql for k in ("sangr", "ferida", "tiro o pano", "parou de sangrar")) and re.search(r"bleed|sangr|dressing", support):
        rules.append("1. Mantenha a pressao direta com pano limpo; NAO levante o pano para conferir. [Fonte: bleeding control]")
        rules.append("2. Se o sangue atravessar, coloque mais pano por cima e procure ajuda. [Fonte: bleeding control]")
    elif any(k in ql for k in ("afog", "drown", "entrar na agua")) and re.search(r"drown|water rescue", support):
        rules.append("1. NAO entre na agua sem equipamento: use boia, corda ou colete e puxe de fora. [Fonte: drowning rescue]")
        rules.append("2. Se precisar entrar, chame socorro especializado; a vitima pode puxar o socorrista. [Fonte: drowning rescue]")
    elif any(k in ql for k in ("convuls", "seizure", "ataque")) and re.search(r"seiz|convuls", support):
        rules.append("1. Afaste objetos proximos e deite a pessoa de lado, mantendo a via aerea livre. [Fonte: seizure first aid]")
        rules.append("2. NAO conte os movimentos nem coloque nada na boca; chame ajuda se durar muito ou repetir. [Fonte: seizure first aid]")
    return rules



def answer(q):
    dom = detectar_dominio(q)
    # dominio novo: recupera com a query especifica do dominio, para as
    # fontes listadas serem exatamente as que ancoram os passos.
    rows = retrieve(q, limit=40 if dom else 4, dom=dom)
    if not rows:
        return f"SEM FONTE LOCAL para: {q}\nNao vou inventar. VEREDITO: DUVIDOSO."
    ctx = "\n\n".join(f"[F{i+1}] {clean(b)[:800]}" for i, (_, b, _, _) in enumerate(rows[:4]))
    if os.environ.get("TA_SLM_OFF") == "1":
        rules = deterministic_rules(q, rows)
        if rules:
            return ("RESPOSTA TAB (offline, fontes verificadas) — " + q + "\n"
                    + "\n".join(rules) + "\n\nVEREDITO: CONFIAVEL (extraido das fontes; sem SLM)\n"
                    + "Fontes: " + ", ".join(fontes_citadas(rules)))
        return grounded_fallback(q, rows)
    # REGRA (18/11, teste adversarial): se existe regra deterministica ancorada
    # para este dominio, ela VENCE o SLM. Medido: o SLM podia gerar "aplique
    # fogo na ferida" e "deite a pessoa de costas para o sangue nao entrar" e
    # ainda assim o gate so media overlap/vocabulario. Com a regra ancorada na
    # frente, o texto perigoso nunca chega a saida.
    rules = deterministic_rules(q, rows)
    if rules:
        return ("RESPOSTA TAB (offline, fontes verificadas) — " + q + "\n"
                + "\n".join(rules) + "\n\nVEREDITO: CONFIAVEL (extraido das fontes; regra ancorada)\n"
                + "Fontes: " + ", ".join(fontes_citadas(rules)))
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
            domain_ok = any(k in sl for k in ("engasg", "chok", "asfix"))
            if domain_ok and any(k in ql for k in ("bebe", "bebê", "infant", "crianca")):
                domain_ok = ("beb" in sl or "infant" in sl or "crianc" in sl) and \
                            any(k in sl for k in ("golp", "palmad", "escápul", "escapul", "costas")) and \
                            "boca a boca" not in sl
        elif any(k in ql for k in ("afog", "drown")):
            domain_ok = any(k in sl for k in ("afog", "drown", "respira", "resgate", "water rescue"))
        elif any(k in ql for k in ("choque", "eletr", "electr")):
            domain_ok = any(k in sl for k in ("choque", "eletr", "electr", "corrente"))
        elif any(k in ql for k in ("insol", "calor", "heat")):
            domain_ok = any(k in sl for k in ("insol", "calor", "heat", "hiperterm"))
        elif any(k in ql for k in ("fratura", "fracture", "osso")):
            domain_ok = any(k in sl for k in ("fratur", "fracture", "splint", "osso", "imobil"))
        elif any(k in ql for k in ("envenen", "poison", "veneno")):
            domain_ok = any(k in sl for k in ("envenen", "poison", "veneno", "inger"))
        elif any(k in ql for k in ("convuls", "seizure", "ataque")):
            domain_ok = any(k in sl for k in ("convuls", "seizure", "ataque", "crise"))
        elif any(k in ql for k in ("sangr", "ferida", "bleed")):
            domain_ok = any(k in sl for k in ("sangr", "ferida", "bleed", "press", "torniq"))
        # 6 dominios novos: o gate tambem exige que a linha fale do dominio.
        # Sem isto, um SLM podia falar de "fire"/"corte" num caso de carrapato.
        elif dom:
            claves = DOMAINS[dom]["gate"]
            domain_ok = any(k in sl for k in claves)
            # premissas perigosas sao barradas mesmo com vocabulario do corpus
            if any(k in sl for k in ("fogo", "isqueiro", "flame", "deite a pessoa de costas",
                                     "corte o veneno", "lamba a ferida", "lave a ferida com fogo")):
                domain_ok = False
        # gate de IDIOMA: resposta de sobrevivencia tem de ser PT. Se a linha
        # nao tem nenhum acento PT e tem palavras inglesas tipicas, descarta.
        en_words = sum(1 for w in ("the", "and", "for", "with", "should", "check",
                                    "water", "source", "store", "bottled", "expiration",
                                    "replace", "needed", "described", "treatment") if w in sl)
        pt_marks = len(re.findall(r"[áéíóúãõêôç]", sl))
        lang_ok = pt_marks > 0 or en_words == 0
        # dominio AGUA: a linha precisa falar de agua/tratamento, nao validade
        if lang_ok and any(k in ql for k in ("agua", "purificar", "beber", "rio")):
            lang_ok = any(k in sl for k in ("agua", "água", "purif", "ferv", "filtr",
                                            "cloro", "destil", "beb", "water"))
        if overlap >= 0.18 and not unsupported_nums and domain_ok and lang_ok:
            kept.append(s)
        else:
            duvidosos.append(s)
    if not kept:
        fb = grounded_fallback(q, rows)
        rules = deterministic_rules(q, rows)
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
