#!/usr/bin/env python3
"""Pure-Python retrieval over the precomputed Joint-ITQ binary index.

No numpy, no network, no embedding server — works inside Termux/offline.
"""
from __future__ import annotations
import base64, hashlib, json, re
from pathlib import Path

INDEX = Path(__file__).with_name('offline-itq-index.json')
TOKEN = re.compile(r'[a-z0-9]+')
STOP = set('a an the and or of to in for on with at by from is are was were be been being this that these those it its as if then than so not no nor but do does did have has had can could should would may might must will shall de da do das dos e ou o a os as um uma para por com sem em no na aos que se como onde quando porque qual quais seu sua'.split())
EXP = {"purificar": "purifying purification distillation", "agua": "water",
       "queimadura": "burn", "picada": "bite snake", "cobra": "snake",
       "engasgo": "choking", "febre": "fever", "ferida": "wound"}


def load(path=INDEX):
    with open(path) as f:
        d = json.load(f)
    d['codes'] = base64.b64decode(d['codes_b64'])
    return d


def _hashed(text, dim):
    v = [0.0] * dim
    for w in TOKEN.findall(text.lower()):
        if len(w) <= 2 or w in STOP:
            continue
        h = hashlib.blake2b(w.encode(), digest_size=8).digest()
        i = int.from_bytes(h[:4], 'big') % dim
        v[i] += 1.0 if h[4] & 1 else -1.0
    n = sum(x * x for x in v) ** 0.5
    if n:
        v = [x / n for x in v]
    return v


def query_code(q, idx):
    dim = idx['dim']
    # Mesmo hashing usado na geracao do indice: sem expansao assimétrica,
    # senao o código da query nao fica no mesmo espaco dos documentos.
    v = _hashed(q, dim)
    R = idx['rotation']
    bits = 0
    for i in range(dim):
        s = 0.0
        # R esta achatada row-major; queremos (v @ R)[i] = sum_j v[j]*R[j,i].
        for j in range(dim):
            s += v[j] * R[j * dim + i]
        if s > 0:
            bits |= 1 << i
    return bits


def search(q, idx, limit=8):
    code = query_code(q, idx)
    codes = idx['codes']
    dim = idx['dim']
    width = dim // 8
    out = []
    for n, src in enumerate(idx['sources']):
        b = int.from_bytes(codes[n * width:(n + 1) * width], 'little')
        dist = (code ^ b).bit_count()
        out.append((dist, src))
    out.sort(key=lambda x: (x[0], x[1]))
    return [s for d, s in out[:limit]]


def rrf(*rankings, limit=8):
    fused = {}
    for ranking in rankings:
        for i, src in enumerate(ranking):
            fused[src] = fused.get(src, 0.0) + 1.0 / (60 + i + 1)
    return [s for s, _ in sorted(fused.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]]
