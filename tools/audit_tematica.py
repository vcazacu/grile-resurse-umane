#!/usr/bin/env python3
"""Audit determinist al paginilor de sinteză, complementar poarții semantice.

Poarta semantică judecă fondul, dar o afirmație despre un articol absent din temeiuri
iese doar „neverificabilă". Aici se verifică trasabilitatea: fiecare cifră și fiecare
trimitere la articol dintr-un paragraf trebuie să apară în citatele aceleiași secțiuni
(sau, pentru articole, măcar în bibliografia temei). Ce nu se regăsește se verifică manual
în lege. Se verifică și că id-urile de întrebări există în bancă.

    python3 audit_tematica.py 02 03 04
"""
import json, re, sys
from pathlib import Path
from normalizare import incarca_intrebari, normalizeaza

DIR = Path(__file__).resolve().parent / "tematica"
_NUM = re.compile(r"(?<![\w^/–-])(\d+(?:[.,]\d+)?)(?:\s*%)?(?![\w^/–-])")   # nu prinde 28–30, 80/1995
_ART = re.compile(r"\bart\.\s*(\d+(?:\^\d+)?)", re.I)
_ALIN = re.compile(r"alin\.\s*\(?(\d+(?:\^\d+)?)\)?", re.I)

def numere(text):
    return {m.group(1).replace(",", ".") for m in _NUM.finditer(text)}

def audit(nr, banca_ids):
    d = json.loads((DIR / f"{nr}.json").read_text(encoding="utf-8"))
    probleme = []
    for s in d["sectiuni"]:
        citate = " ".join(t["citat"] for t in s["temei"])
        # un articol e trasabil dacă e temei al secțiunii SAU dacă legea însăși îl numește
        # în textul citat (trimitere internă, ex. „cei prevăzuți la art. 36 alin. 1 lit. a)")
        arts_temei = {m.group(1) for t in s["temei"] for m in _ART.finditer(t["articol"])} \
                   | {m.group(1) for m in _ART.finditer(citate)}
        num_citate = numere(citate) | numere(" ".join(t["articol"] for t in s["temei"]))
        for ip, par in enumerate(s["paragrafe"]):
            # cifre din paragraf care nu apar nici în citate, nici în etichetele articolelor
            for n in numere(par) - num_citate:
                # ignoră numerele care sunt doar numere de articol/alineat/literă menționate
                if re.search(r"(?:art\.|alin\.|lit\.|pct\.|nr\.|anexa|anexele|capitol|tabelul)\s*(?:\(|nr\.\s*)?%s\b" % re.escape(n), par, re.I):
                    continue
                probleme.append(("CIFRĂ", s["titlu"][:45], ip + 1, n, par[:160]))
            # articole numite în paragraf, dar absente din temeiurile secțiunii
            for a in {m.group(1) for m in _ART.finditer(par)} - arts_temei:
                probleme.append(("ART.", s["titlu"][:45], ip + 1, "art. " + a, par[:120]))
    lipsa = [i for i in d.get("intrebari") or [] if i not in banca_ids]
    return d["titlu"], probleme, lipsa

def main(argv):
    banca = {q["id"] for q in incarca_intrebari(DIR.parent.parent / "intrebari.js")}
    for nr in argv:
        titlu, probleme, lipsa = audit(nr, banca)
        cif = [p for p in probleme if p[0] == "CIFRĂ"]; art = [p for p in probleme if p[0] == "ART."]
        print("=== tema %s — %s: %d cifre netrasabile, %d articole fără temei, %d id-uri lipsă ===" % (nr, titlu[:50], len(cif), len(art), len(lipsa)))
        for tip, sec, ip, ce, ctx in probleme:
            print("  %-6s %-45s ¶%d  %-14s %s" % (tip, sec, ip, ce, ctx.replace("\n", " ")[:110]))
        if lipsa: print("  ID-URI LIPSĂ:", lipsa)
        print()

if __name__ == "__main__":
    main(sys.argv[1:])
