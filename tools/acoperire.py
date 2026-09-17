#!/usr/bin/env python3
"""Acoperirea tematicii: pentru fiecare articol cerut de bibliografie, câte întrebări
există în fișierele date (implicit nou/*.json, sau ../intrebari.js).
Utilizare: python3 acoperire.py [fișiere...]   — exit 1 dacă vreun articol cerut are 0 întrebări."""
import sys, re, glob, os, json
from bibliografie import tematica, cheie
from valideaza import incarca
DIR = os.path.dirname(os.path.abspath(__file__))
fis = sys.argv[1:] or (sorted(glob.glob(os.path.join(DIR, "nou", "*.json"))) or [os.path.join(DIR, "..", "intrebari.js")])
lista = []
for f in fis: lista += incarca(f)
cnt = {}
for q in lista:
    s = q["sursa"]; k = s["fisier"] + ("#" + s["anexa"] if s.get("anexa") else "")
    m = re.match(r"^art\.\s*(\d+(?:\^\d+)?)", s["articol"])
    if m: cnt[(k, m.group(1))] = cnt.get((k, m.group(1)), 0) + 1
lipsa_tot = 0
for k, (fisier, anexa, want, lipsa, abrog, arts) in tematica().items():
    zero = [a for a in want if cnt.get((k, a), 0) == 0 and a not in abrog]
    nq = sum(cnt.get((k, a), 0) for a in want)
    print("%-62s întrebări=%3d articole cerute=%3d neacoperite=%d %s" % (k, nq, len(want), len(zero), ("→ " + ", ".join(zero)) if zero else ""))
    lipsa_tot += len(zero)
print("ACOPERIRE COMPLETĂ" if lipsa_tot == 0 else "ARTICOLE NEACOPERITE: %d" % lipsa_tot)
sys.exit(1 if lipsa_tot else 0)
