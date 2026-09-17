#!/usr/bin/env python3
"""Verifică dacă fiecare citat (sursa.citat) apare CUVÂNT CU CUVÂNT în textul
normativ al fișierului-sursă declarat (și al anexei declarate, dacă e cazul).

Utilizare:
    python3 check_citat.py [fisiere...]
    (implicit: nou/*.json plus ../intrebari.js, dacă există)

Citatul se împarte la „[...]"; fiecare fragment trebuie să apară, în ordine,
în corpusul normativ al zonei (fără §NOTA§, fără titluri „## ", fără antet),
comparat după normalizare (diacritice, ghilimele, liniuțe, spații, majuscule).
Codul de ieșire este 1 dacă cel puțin un citat nu se confirmă.
"""
import difflib
import sys

import bibliografie
from normalizare import (DIR_LEGISLATIE, eticheta_articol, fisiere_din_argumente,
                         fragmente_citat, incarca_intrebari, linii_zona, normalizeaza)

LUNGIME_AFISATA = 80   # câte caractere din fragment / din indiciu afișăm


def corpus_zona(fisier, anexa, cache):
    """Textul normativ al zonei, normalizat și unit cu spații (None dacă fișierul lipsește)."""
    cheie = (fisier, anexa)
    if cheie not in cache:
        linii = linii_zona(fisier, anexa)
        if linii is None:
            cache[cheie] = None
        else:
            # titlurile „Articolul N" nu sunt text citabil, le lăsăm afară
            cache[cheie] = " ".join(normalizeaza(text) for et, text in linii if et is None)
    return cache[cheie]


def corpus_note(fisier, cache):
    """Toate liniile §NOTA§ din fișier, normalizate (ca să explicăm citatele luate din note)."""
    cheie = ("§NOTA§", fisier)
    if cheie not in cache:
        text = (DIR_LEGISLATIE / fisier).read_text(encoding="utf-8")
        cache[cheie] = " ".join(normalizeaza(l[6:]) for l in text.split("\n") if l.startswith("§NOTA§"))
    return cache[cheie]


def indiciu(fisier, anexa, articol, fragment):
    """Linia din articolul declarat care acoperă cea mai mare parte a fragmentului
    (blocurile comune găsite de SequenceMatcher, raportate la lungimea fragmentului;
    ratio() simplu ar dezavantaja alineatele lungi)."""
    if not articol:
        return None
    arts = bibliografie.articole_din_text(str(DIR_LEGISLATIE / fisier), anexa)
    scor, cea_mai_buna = 0.0, None
    for linie in arts.get(articol) or []:
        sm = difflib.SequenceMatcher(None, fragment, normalizeaza(linie), autojunk=False)
        acoperire = sum(b.size for b in sm.get_matching_blocks()) / len(fragment)
        if acoperire > scor:
            scor, cea_mai_buna = acoperire, linie
    return cea_mai_buna


def verifica_intrebare(q, cache):
    """Întoarce lista de mesaje de eroare (goală = citat confirmat)."""
    sursa = q.get("sursa") or {}
    fisier, anexa = sursa.get("fisier", ""), sursa.get("anexa", "")
    fragmente = fragmente_citat(sursa.get("citat"))
    if not fisier or not fragmente:
        return ["sursa.fisier sau sursa.citat lipsește"]
    corpus = corpus_zona(fisier, anexa, cache)
    if corpus is None:
        return ["fișierul-sursă nu există: %s" % fisier]
    if not corpus:
        return ["zona declarată este goală (anexa „%s” nu există în %s?)" % (anexa, fisier)]
    articol = eticheta_articol(sursa.get("articol"))
    pozitie = 0
    for i, frag in enumerate(fragmente, 1):
        gasit = corpus.find(frag, pozitie)
        if gasit >= 0:
            pozitie = gasit + len(frag)
            continue
        if frag in corpus:
            motiv = "există în text, dar NU în ordinea din citat"
        elif frag in corpus_note(fisier, cache):
            motiv = "apare DOAR într-o linie §NOTA§ (istoric de modificări/decizii, nu text normativ)"
        else:
            motiv = "NU apare în text"
        mesaj = "fragmentul %d/%d %s: „%s”" % (i, len(fragmente), motiv, frag[:LUNGIME_AFISATA])
        apropiat = indiciu(fisier, anexa, articol, frag)
        if apropiat and "§NOTA§" not in motiv:
            mesaj += "\n      indiciu (art. %s): „%s”" % (articol, apropiat[:LUNGIME_AFISATA * 2])
        return [mesaj]
    return []


def verifica_fisier(cale, cache):
    """Verifică toate întrebările dintr-un fișier; întoarce (confirmate, total)."""
    print("== %s ==" % cale)
    try:
        intrebari = incarca_intrebari(cale)
    except (OSError, ValueError) as e:
        print("  EROARE: nu pot citi fișierul: %s" % e)
        return 0, 1
    confirmate = 0
    for q in intrebari:
        erori = verifica_intrebare(q, cache)
        if erori:
            for e in erori:
                print("  EROARE %s: %s" % (q.get("id", "?"), e))
        else:
            confirmate += 1
    print("  %d/%d citate confirmate" % (confirmate, len(intrebari)))
    return confirmate, len(intrebari)


def main(argv):
    fisiere = fisiere_din_argumente(argv)
    if not fisiere:
        print("Niciun fișier de verificat (nou/ este gol și ../intrebari.js lipsește).")
        return 0
    cache, confirmate, total = {}, 0, 0
    for cale in fisiere:
        c, t = verifica_fisier(cale, cache)
        confirmate += c
        total += t
    print("TOTAL: %d/%d citate confirmate în %d fișier(e)" % (confirmate, total, len(fisiere)))
    return 0 if confirmate == total else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
