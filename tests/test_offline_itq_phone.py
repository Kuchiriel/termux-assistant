#!/usr/bin/env python3
"""Validate fused offline retrieval on the phone's own corpus.db."""
import json, re, sqlite3, sys, time
from pathlib import Path
B = Path.home() / 'projects/termux-assistant/blackout'
sys.path.insert(0, str(B))
import itq_index
DB = Path.home() / 'offline-corpus/corpus.db'
STOP = set('a o as os da de do das dos e um uma para com em por no na que se como fazer deve devem usar uso'.split())

def norm(s):
    return ' '.join(w for w in re.sub(r'[^a-z0-9]+', ' ', s.lower()).split() if w not in STOP)

def fts(c, q, k=8):
    expr = ' OR '.join(norm(q).split()[:8]) or 'water'
    try:
        return [r[0] for r in c.execute(
            'select source from docs where docs match ? order by rank limit ?',
            (expr, k)).fetchall()]
    except Exception:
        return []

def main():
    idx = itq_index.load(B / 'offline-itq-index.json')
    c = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
    rows = c.execute('select title,body,source from docs').fetchall()
    qs = [(r[0], r[2]) for r in rows[:60]]
    f = b = r = 0
    t0 = time.perf_counter()
    for q, want in qs:
        a = fts(c, q)
        bb = itq_index.search(q, idx, 8)
        rr = itq_index.rrf(list(dict.fromkeys(a)), bb, limit=8)
        f += want in a
        b += want in bb
        r += want in rr
    ms = (time.perf_counter() - t0) * 1000 / len(qs)
    print(json.dumps({'docs': len(rows), 'queries': len(qs),
                      'fts5': round(f/len(qs),3), 'binary': round(b/len(qs),3),
                      'fusion': round(r/len(qs),3), 'ms_per_query': round(ms,1)}, indent=2))

if __name__ == '__main__':
    main()
