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
           "-st", "-n", "100", "--no-warmup", "-t", "4", "--no-display-prompt",
           "--temp", "0.1", "--top-k", "20", "--top-p", "0.9", "--min-p", "0.05",
           "--typical-p", "0.9", "--seed", "42"]
    proc = None
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            stdout, _ = proc.communicate(timeout=120)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            return sentence + " [traducao abortada por timeout]"
        out = stdout or ""
        marks = [l for l in out.splitlines() if l.lstrip().startswith("> ")]
        if marks: out = out.rsplit(marks[-1], 1)[1]
        out = re.split(r"\[ Prompt:|Exiting", out)[0].strip()
        nums_in = re.findall(r"\b\d+(?:[.,]\d+)?\b", sentence)
        nums_out = re.findall(r"\b\d+(?:[.,]\d+)?\b", out)
        if sorted(nums_in) != sorted(nums_out): return sentence + " [traducao rejeitada: numeros divergem]"
        # gate de TERMOS: conceitos-chave da fonte precisam sobreviver a traducao.
        # Mapa PT->EN inverted: se a fonte tem o termo EN, a saida PT deve ter o equivalente.
        REQ = {
            "back slaps": ("palmad", "golp", "batidas"),
            "shoulder blades": ("escápul", "escapul", "omoplat"),
            "chest": ("peito", "tórax", "torax"),
            "pressure": ("press", "compress"),
            "immobilization": ("imobiliz", "imobil"),
            "boil": ("ferv", "ebuli"),
            "water": ("agua", "água"),
            "burn": ("queimad", "queimadura"),
            "wound": ("ferida", "ferimento"),
        }
        low = out.lower(); src = sentence.lower()
        for en, pts in REQ.items():
            if en in src and not any(k in low for k in pts):
                return sentence + f" [traducao rejeitada: termo '{en}' perdido]"
        return out[:600] or sentence
    except Exception:
        if proc is not None and proc.poll() is None:
            proc.kill()
        return sentence


if __name__ == "__main__":
    print(translate(" ".join(sys.argv[1:])))
