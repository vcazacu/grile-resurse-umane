#!/usr/bin/env python3
"""Descompunerea unui articol în alineate și litere, și rezolvarea trimiterilor.

Rezolvarea trimiterilor („art. 85 alin. 1 lit. g), h), j)…”) e motivul principal:
la L80-328 cheia corectă era „prin demisie”, iar dovada — că lit. h) din art. 85
chiar înseamnă demisie — cerea o căutare pe care modelul o rata chiar și cu
articolul 85 întreg în stare. Codul face căutarea, modelul judecă rezultatul.
"""
import re

import bibliografie
from normalizare import DIR_LEGISLATIE

_ALIN = re.compile(r"^\((\d+(?:\^\d+)?)\)\s*")
_LIT = re.compile(r"^([a-zșț](?:\^\d+)?)\)\s*")
_LINIUTA = re.compile(r"^[-–]\s+")
# „A. Subofițeri:", „B. Maiștri militari:", „A^1. Maiștri militari:" — paragrafe majuscule
# care grupează litere. Fără ele, literele a)-e) ale grupului B le suprascriu pe ale lui A
# (art. 2 alin. (2) din Legea 80/1995 ajungea o listă amestecată).
_GRUP = re.compile(r"^([A-ZȘȚ](?:\^\d+)?)\.\s+(.*)$")

# „art. 85 alin. 1 lit. g), h) și n)" / „art. 15 alin. (1) lit. c^1)" / „art. 7 alin. (2)"
_TRIMITERE = re.compile(
    r"art\.\s*(?P<art>\d+(?:\^\d+)?)"
    r"(?P<rest>(?:\s*(?:alin\.|lit\.)\s*\(?[0-9a-zșț](?:\^\d+)?\)?"
    r"(?:\s*(?:,|și|ori|sau)\s*\(?[0-9a-zșț](?:\^\d+)?\)?)*)*)", re.I)
_NUM = re.compile(r"\(?(\d+(?:\^\d+)?)\)?")
_LIT_REF = re.compile(r"([a-zșț](?:\^\d+)?)\)")


def descompune(linii):
    """[linii normative] → {„alin. (N)": {"text": …, "litere": {„a)": …}}}.

    Articolele fără alineate numerotate intră sub cheia „text unic"; literele care
    apar înaintea oricărui alineat se atașează tot acolo. Liniuțele se lipesc de
    litera sau alineatul curent — sunt continuări, nu unități de sine stătătoare."""
    out, alin_curent, lit_curenta, grup = {}, None, None, ""

    def pune(cheie):
        out.setdefault(cheie, {"text": "", "litere": {}})
        return out[cheie]

    for l in linii:
        l = l.strip()
        if not l:
            continue
        m = _ALIN.match(l)
        if m:
            alin_curent, lit_curenta, grup = "alin. (%s)" % m.group(1), None, ""
            pune(alin_curent)["text"] = l[m.end():].strip()
            continue
        if alin_curent is None:
            alin_curent = "text unic"
            pune(alin_curent)
        m = _GRUP.match(l)
        if m:
            grup, lit_curenta = m.group(1) + ". ", None
            tinta = pune(alin_curent)
            tinta["text"] = (tinta["text"] + " " + l).strip()
            continue
        m = _LIT.match(l)
        if m and not _LINIUTA.match(l):
            lit_curenta = "%s%s)" % (grup, m.group(1))
            pune(alin_curent)["litere"][lit_curenta] = l[m.end():].strip()
            continue
        tinta = pune(alin_curent)
        if lit_curenta:
            tinta["litere"][lit_curenta] += " " + l
        else:
            tinta["text"] = (tinta["text"] + " " + l).strip()
    return out


def trimiteri(text):
    """Trimiterile dintr-un text → [(articol, [alineate], [litere])], în ordine."""
    gasite = []
    for m in _TRIMITERE.finditer(text or ""):
        rest = m.group("rest") or ""
        parte_alin, parte_lit = rest, ""
        jos = rest.lower()
        if "lit." in jos:
            i = jos.index("lit.")
            parte_alin, parte_lit = rest[:i], rest[i:]
        alineate = _NUM.findall(parte_alin)
        litere = ["%s)" % x for x in _LIT_REF.findall(parte_lit)]
        gasite.append((m.group("art"), alineate, litere))
    return gasite


def rezolva(text, sursa, cache, fara=(), maxim=12):
    """Trimiterile din `text`, rezolvate în bucăți numite: {„art. 85 alin. 1 lit. h)": „prin demisie;"}.

    Se caută în zona declarată (anexă) și apoi în corpul legii — explicațiile din
    anexa VI trimit des la corpul Legii 153/2017."""
    fisier, anexa = sursa.get("fisier", ""), sursa.get("anexa", "")
    out = {}
    for art, alineate, litere in trimiteri(text):
        if len(out) >= maxim:
            break
        arts = None
        for zona in ([anexa, ""] if anexa else [""]):
            k = (fisier, zona)
            if k not in cache:
                cale = DIR_LEGISLATIE / fisier
                cache[k] = bibliografie.articole_din_text(str(cale), zona) if cale.is_file() else {}
            if art in cache[k] and cache[k][art]:
                arts = descompune(cache[k][art])
                break
        if not arts:
            continue
        if art in fara and not litere and not alineate:
            continue
        cheie_alin = ["alin. (%s)" % a for a in alineate] or list(arts)
        for ca in cheie_alin:
            if ca not in arts:
                continue
            bloc = arts[ca]
            eticheta_alin = "art. %s%s" % (art, "" if ca == "text unic" else " " + ca)
            if litere:
                for lt in litere:
                    if lt in bloc["litere"]:
                        out["%s lit. %s" % (eticheta_alin, lt)] = bloc["litere"][lt]
            elif alineate:
                corp = bloc["text"]
                if bloc["litere"]:
                    corp += " " + " ".join("%s %s" % (k, v) for k, v in bloc["litere"].items())
                out[eticheta_alin] = corp[:1200]
    return out
