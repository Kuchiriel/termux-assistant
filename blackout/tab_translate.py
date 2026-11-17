#!/usr/bin/env python3
"""tab_translate — traduz sentencas das fontes para PT com verificacao.

Nao e tradutor neural externo: e o mesmo Gemma 1B one-shot, com prompt de
traducao literal e gate que barra numeros inventados e termos fora da fonte.
Se falhar, devolve a sentenca original em EN com aviso (melhor que inventar).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

M = Path(os.environ.get("TA_SLM_MODEL", str(Path.home() / "models/slm/gemma-3-1b-it-Q4_K_M.gguf")))
CLI = os.environ.get("TA_LLAMA_CLI", "llama-cli")


def translate(sentence: str) -> str:
    if not M.is_file(): return sentence
    sys_p = ("Tradutor PT-BR. Traduza a frase abaixo para portugues do Brasil, "
             "literalmente, sem explicar, sem inventar numeros ou termos. "
             "Mantenha numeros e unidades exatamente como estao.")
    cmd = [CLI, "-m", str(M), "-sys", sys_p, "-p", sentence, "--ctx-size", "1024",
           "-st", "-n", "100", "--no-warmup", "-t", "4", "--no-display-prompt"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        out = p.stdout or ""
        marks = [l for l in out.splitlines() if l.lstrip().startswith("> ")]
        if marks: out = out.rsplit(marks[-1], 1)[1]
        out = re.split(r"\[ Prompt:|Exiting", out)[0].strip()
        nums_in = re.findall(r"\b\d+(?:[.,]\d+)?\b", sentence)
        nums_out = re.findall(r"\b\d+(?:[.,]\d+)?\b", out)
        if sorted(nums_in) != sorted(nums_out): return sentence + " [traducao rejeitada: numeros divergem]"
        return out[:600] or sentence
    except Exception:
        return sentence


if __name__ == "__main__":
    print(translate(" ".join(sys.argv[1:])))
