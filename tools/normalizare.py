"""Funcții comune pentru check_citat.py și check_articol.py:
normalizarea textului, citirea zonei (corp / anexă) dintr-un fișier-sursă și
încărcarea întrebărilor din JSON sau din ../intrebari.js.

Toate căile se rezolvă față de folderul acestui fișier, nu față de CWD.
"""
import json
import re
import unicodedata
from pathlib import Path

DIR_TOOLS = Path(__file__).resolve().parent
DIR_LEGISLATIE = (DIR_TOOLS / ".." / ".." / "legislatie").resolve()
FISIER_INTREBARI = (DIR_TOOLS / ".." / "intrebari.js").resolve()

# caractere cu variante grafice: toate se aduc la o formă unică
_DIACRITICE = str.maketrans({"ş": "ș", "ţ": "ț", "Ş": "Ș", "Ţ": "Ț"})
_GHILIMELE = re.compile("[„“”‟«»‘’‚‛′″ʼ']")
_LINIUTE = re.compile("[–—―‐‑‒−]")
_INVIZIBILE = re.compile("[­​‌‍﻿]")
_SPATII = re.compile(r"\s+")
_SEPARATOR_CITAT = re.compile(r"\[\s*(?:\.\.\.|…)\s*\]")   # „[...]" sau „[…]"


def normalizeaza(text):
    """NFC, ş/ţ→ș/ț, orice ghilimele→", orice liniuță→-, spații unice, minuscule."""
    t = unicodedata.normalize("NFC", text).translate(_DIACRITICE)
    t = _INVIZIBILE.sub("", t)
    t = _GHILIMELE.sub('"', t)
    t = _LINIUTE.sub("-", t)
    return _SPATII.sub(" ", t).strip().lower()


def fragmente_citat(citat):
    """Împarte citatul la „[...]" și normalizează fiecare fragment (fără cele goale)."""
    return [f for f in (normalizeaza(p) for p in _SEPARATOR_CITAT.split(citat or "")) if f]


def linii_zona(nume_fisier, anexa=""):
    """Liniile zonei cerute, în ordine, ca perechi (eticheta_articol | None, text).

    eticheta_articol este setată doar pe liniile „Articolul N" (ancorele reale);
    §SURSA§, §NOTA§, §ANEXA§ și titlurile „## " sunt eliminate. Zona = corpul legii
    (tot ce e înainte de prima §ANEXA§) când anexa == "", altfel anexa cu acel nume.
    Întoarce None dacă fișierul lipsește; listă goală dacă zona nu există.
    """
    cale = DIR_LEGISLATIE / nume_fisier
    if not cale.is_file():
        return None
    in_zona = (anexa == "")
    rezultat = []
    for linie in cale.read_text(encoding="utf-8").split("\n"):
        if linie.startswith("§ANEXA§"):
            in_zona = anexa != "" and normalizeaza(linie[7:]) == normalizeaza(anexa)
            continue
        if not in_zona or not linie.strip():
            continue
        if linie.startswith(("§SURSA§", "§NOTA§", "## ")):
            continue
        m = re.match(r"^Articolul (\d+(?:\^\d+)?)$", linie)
        if m:
            rezultat.append((m.group(1), linie))
        else:
            rezultat.append((None, linie))
    return rezultat


def eticheta_articol(sursa_articol):
    """„art. 20^1 alin. (1)" → „20^1"; None dacă nu începe cu „art. <număr>"."""
    m = re.match(r"^art\.\s*(\d+(?:\^\d+)?)", (sursa_articol or "").strip(), re.I)
    return m.group(1) if m else None


def incarca_intrebari(cale):
    """Lista de întrebări dintr-un .json (listă JSON) sau din intrebari.js
    („const INTREBARI = [...];", eventual precedat de un comentariu /* ... */)."""
    text = Path(cale).read_text(encoding="utf-8")
    if str(cale).endswith(".js"):
        start = text.find("INTREBARI")
        start = text.find("[", start if start >= 0 else 0)
        if start < 0:
            raise ValueError("nu găsesc lista INTREBARI în %s" % cale)
        date, _ = json.JSONDecoder().raw_decode(text, start)
    else:
        date = json.loads(text)
    if not isinstance(date, list):
        raise ValueError("%s nu conține o listă de întrebări" % cale)
    return date


def fisiere_implicite():
    """nou/*.json (sortate) plus ../intrebari.js dacă există."""
    fisiere = sorted((DIR_TOOLS / "nou").glob("*.json"))
    if FISIER_INTREBARI.is_file():
        fisiere.append(FISIER_INTREBARI)
    return fisiere


def fisiere_din_argumente(argv):
    """Fișierele de verificat: cele din linia de comandă (față de CWD) sau implicite."""
    return [Path(a) for a in argv] if argv else fisiere_implicite()


def cheie_bib(sursa):
    """Cheia din bibliografie.BIB: fișier, plus „#<anexa>" când citatul e din anexă."""
    fisier = sursa.get("fisier", "")
    anexa = sursa.get("anexa", "")
    return fisier + ("#" + anexa if anexa else "")
