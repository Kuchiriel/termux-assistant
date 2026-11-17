#!/usr/bin/env python3
"""Varredura de segredos — roda antes de cada push (tests/scan-secrets.py)."""
import re, sys
from pathlib import Path
PATS = [
 (re.compile(r'nvapi-[A-Za-z0-9_\-]{20,}'), 'NVIDIA_API_KEY'),
 (re.compile(r'\b(?:hf_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,})\b'), 'TOKEN'),
 (re.compile(r'(?i)(?:OPENCODE_SERVER_PASSWORD|HF_TOKEN|GITHUB_TOKEN)\s*=\s*["\']?[A-Za-z0-9_\-]{16,}'), 'ENV_SECRET'),
 (re.compile(r'(?i)bearer\s+[A-Za-z0-9_\-\.]{30,}'), 'BEARER'),
]
root = Path(sys.argv[1] if len(sys.argv) > 1 else '.')
hits = 0
for p in root.rglob('*'):
    if not p.is_file() or '/.git/' in str(p): continue
    if p.name == 'scan-secrets.py': continue
    try: s = p.read_text(encoding='utf-8', errors='replace')
    except Exception: continue
    for rx, label in PATS:
        for m in rx.finditer(s):
            hits += 1
            print(f'{label}: {p.relative_to(root)}:{s[:m.start()].count(chr(10))+1}')
print(f'segredos encontrados: {hits}')
raise SystemExit(1 if hits else 0)
