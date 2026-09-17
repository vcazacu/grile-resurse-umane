#!/usr/bin/env python3
"""Verifică dacă citatul fiecărei întrebări se află chiar în articolul declarat
(sursa.articol) și dacă acel articol face parte din tematica examenului.

Utilizare:
    python3 check_articol.py [fisiere...]
    (implicit: nou/*.json plus ../intrebari.js, dacă există)

Pași, pentru fiecare întrebare:
  1. eticheta articolului din sursa.articol („art. 20^1 alin. (1)" → „20^1");
  2. corpusul zonei declarate, cu fiecare titlu „Articolul X" înlocuit de
     santinela @@ART:X@@ (notele și titlurile de capitol sunt eliminate);
  3. TOATE aparițiile primului fragment: cel puțin una trebuie să fie sub
     santinela articolului declarat, iar restul fragmentelor trebuie să urmeze
     înainte de santinela următoare (textul se repetă între articole, deci
     oricare apariție potrivită este acceptată);
  4. tematica: articolul trebuie să fie printre cele cerute în bibliografie;
     dacă există o restricție pe alineate/litere, verificăm ce declară sursa.articol.
Fișierul opțional articol-exceptii.txt (id<TAB>motiv, o linie per întrebare)
sare peste pasul 3 pentru acele id-uri. Cod de ieșire 1 la orice eroare.
"""
import re
import sys

import bibliografie
from normalizare import (DIR_TOOLS, cheie_bib, eticheta_articol, fisiere_din_argumente,
                         fragmente_citat, incarca_intrebari, linii_zona, normalizeaza)

SANTINELA = "@@ART:"
FISIER_EXCEPTII = DIR_TOOLS / "articol-exceptii.txt"
_TEMATICA = {}


def tematica():
    """bibliografie.tematica(), calculată o singură dată (citește toate sursele)."""
    if not _TEMATICA:
        _TEMATICA.update(bibliografie.tematica())
    return _TEMATICA


def corpus_cu_santinele(fisier, anexa, cache):
    """Zona normalizată, cu „Articolul X" → @@ART:X@@; None dacă fișierul lipsește."""
    cheie = (fisier, anexa)
    if cheie not in cache:
        linii = linii_zona(fisier, anexa)
        cache[cheie] = None if linii is None else " ".join(
            SANTINELA + et + "@@" if et else normalizeaza(text) for et, text in linii)
    return cache[cheie]


def articolul_de_la(corpus, pozitie):
    """Eticheta ultimei santinele dinaintea poziției (None = înainte de primul articol)."""
    i = corpus.rfind(SANTINELA, 0, pozitie)
    return None if i < 0 else corpus[i + len(SANTINELA):corpus.index("@@", i + len(SANTINELA))]


def potriveste_articol(corpus, fragmente, declarat):
    """None dacă citatul stă în articolul declarat, altfel mesajul de eroare."""
    primul, rest = fragmente[0], fragmente[1:]
    if SANTINELA + declarat + "@@" not in corpus:
        return "art. %s nu există în zona declarată" % declarat
    gasite, in_articol = [], False
    p = corpus.find(primul)
    while p >= 0:
        art = articolul_de_la(corpus, p) or "(înainte de primul articol)"
        if art not in gasite:
            gasite.append(art)
        if art == declarat:
            in_articol = True
            limita = corpus.find(SANTINELA, p)
            limita = len(corpus) if limita < 0 else limita
            poz, complet = p + len(primul), True
            for k, frag in enumerate(rest, 2):
                g = corpus.find(frag, poz, limita)
                if g < 0:
                    complet = False
                    break
                poz = g + len(frag)
            if complet:
                return None
        p = corpus.find(primul, p + 1)
    if not gasite:
        return "declarat art. %s, dar primul fragment nu apare deloc în zonă" % declarat
    if in_articol:
        return "declarat art. %s: începutul citatului e acolo, dar fragmentul %d nu urmează în același articol" % (declarat, k)
    return "declarat art. %s, dar citatul se găsește în art. %s" % (declarat, ", ".join(gasite))


def verifica_restrictie(restrictie, sursa_articol):
    """(eroare, avertisment) față de „doar alin. (1)-(3)" / „doar lit. a)-f)"."""
    m = re.search(r"(alin|lit)\.\s*\(?([^)\s]+)\)(?:\s*-\s*\(?([^)\s]+)\))?", restrictie)
    tip, de_la, pana_la = m.group(1), m.group(2), m.group(3) or m.group(2)
    numite = re.findall(r"%s\.\s*\(?([^)\s]+)\)" % tip, sursa_articol or "")
    if not numite:
        return None, "restricție „%s” — sursa.articol nu precizează %s., verificați manual" % (restrictie, tip)
    for n in numite:
        ordine = bibliografie.cheie if tip == "alin" else (lambda x: x.lower())
        if not ordine(de_la) <= ordine(n) <= ordine(pana_la):
            return "%s. %s este în afara restricției „%s”" % (tip, n, restrictie), None
    return None, None


def verifica_tematica(sursa, declarat):
    """(in_tematica, eroare, avertisment) pentru articolul declarat."""
    cheie = cheie_bib(sursa)
    if cheie not in tematica():
        return False, "„%s” nu figurează în bibliografie" % cheie, None
    cerute = tematica()[cheie][2]
    if declarat not in cerute:
        return False, "art. %s din „%s” NU este în tematică" % (declarat, cheie), None
    restrictie = bibliografie.RESTRICTII.get((cheie, declarat))
    if not restrictie:
        return True, None, None
    eroare, avert = verifica_restrictie(restrictie, sursa.get("articol"))
    return True, eroare, avert


def verifica_fisier(cale, cache, exceptii):
    """Întoarce (potrivite, total, in_tematica, in_afara, exceptii_aplicate, erori)."""
    print("== %s ==" % cale)
    try:
        intrebari = incarca_intrebari(cale)
    except (OSError, ValueError) as e:
        print("  EROARE: nu pot citi fișierul: %s" % e)
        return 0, 1, 0, 1, 0, 1
    potrivite = in_tem = in_afara = aplicate = erori = 0
    for q in intrebari:
        qid, sursa = q.get("id", "?"), q.get("sursa") or {}
        declarat = eticheta_articol(sursa.get("articol"))
        fragmente = fragmente_citat(sursa.get("citat"))
        corpus = corpus_cu_santinele(sursa.get("fisier", ""), sursa.get("anexa", ""), cache)
        if not declarat or not fragmente or corpus is None:
            print("  EROARE %s: sursa incompletă (articol/citat/fișier)" % qid)
            in_afara += 1
            erori += 1
            continue
        if qid in exceptii:
            aplicate += 1
            potrivite += 1
            print("  EXCEPȚIE %s: %s" % (qid, exceptii[qid]))
        else:
            e = potriveste_articol(corpus, fragmente, declarat)
            if e:
                print("  EROARE %s: %s" % (qid, e))
                erori += 1
            else:
                potrivite += 1
        ok, e, avert = verifica_tematica(sursa, declarat)
        in_tem += ok
        in_afara += not ok
        if e:
            print("  EROARE %s: %s" % (qid, e))
            erori += 1
        if avert:
            print("  ATENȚIE %s: %s" % (qid, avert))
    print("  %d/%d articole potrivite" % (potrivite, len(intrebari)))
    print("  ÎN tematică: %d / ÎN AFARĂ: %d" % (in_tem, in_afara))
    return potrivite, len(intrebari), in_tem, in_afara, aplicate, erori


def citeste_exceptii():
    """{id: motiv} din articol-exceptii.txt (linii goale sau cu # sunt ignorate)."""
    if not FISIER_EXCEPTII.is_file():
        return {}
    out = {}
    for linie in FISIER_EXCEPTII.read_text(encoding="utf-8").splitlines():
        if linie.strip() and not linie.startswith("#"):
            qid, _, motiv = linie.partition("\t")
            out[qid.strip()] = motiv.strip() or "(fără motiv)"
    return out


def main(argv):
    fisiere = fisiere_din_argumente(argv)
    if not fisiere:
        print("Niciun fișier de verificat (nou/ este gol și ../intrebari.js lipsește).")
        return 0
    exceptii, cache = citeste_exceptii(), {}
    tot = [0, 0, 0, 0, 0, 0]
    for cale in fisiere:
        for i, v in enumerate(verifica_fisier(cale, cache, exceptii)):
            tot[i] += v
    print("TOTAL: %d/%d articole potrivite, ÎN tematică: %d / ÎN AFARĂ: %d, excepții aplicate: %d"
          % (tot[0], tot[1], tot[2], tot[3], tot[4]))
    return 1 if tot[5] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
