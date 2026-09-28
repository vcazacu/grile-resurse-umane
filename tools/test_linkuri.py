#!/usr/bin/env python3
"""Linkurile din paginile statice ale aplicației: index.html, tematica/*.html, legislatie/*.html.

Fiecare href/src relativ trebuie să ducă la un fișier existent, iar ancora (#…) la un id din pagina-țintă.
Linkurile „Exersează tema” (../index.html?intrebari=…) trebuie să numească doar id-uri din bancă.
Linkurile construite în JavaScript (panoul „Temei legal” din app.js, chenarele din paginile de legislație)
nu apar aici — pe acelea le verifică tools/linkuri_panou.js în browser.
Utilizare: python3 test_linkuri.py"""
import glob, html, os, re, sys
from urllib.parse import urlsplit, unquote, parse_qs
DIR = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(DIR)

PAGINI = [os.path.join(APP, "index.html")] + sorted(glob.glob(os.path.join(APP, "tematica", "*.html"))) \
    + sorted(glob.glob(os.path.join(APP, "legislatie", "*.html")))
ATRIBUT = re.compile(r'\b(?:href|src)="([^"]*)"')

def id_uri(cale, _cache={}):
    if cale not in _cache:
        with open(cale, encoding="utf-8") as f:
            _cache[cale] = set(re.findall(r'\bid="([^"]+)"', f.read()))
    return _cache[cale]

def banca():
    with open(os.path.join(APP, "intrebari.js"), encoding="utf-8") as f:
        return set(re.findall(r'"id":\s*"([^"]+)"', f.read()))

def verifica(pagini=PAGINI):
    """Întoarce lista de probleme: (pagina relativă, href, motiv)."""
    probleme, ids_banca = [], banca()
    for pag in pagini:
        with open(pag, encoding="utf-8") as f:
            text = f.read()
        # fără <script>: acolo href-urile sunt bucăți de șir JS ('+pag+'), nu linkuri
        text = re.sub(r"<script\b.*?</script>", "", text, flags=re.S)
        for brut in ATRIBUT.findall(text):
            h = html.unescape(brut)
            u = urlsplit(h)
            if u.scheme or h.startswith("//"):
                continue
            tinta = os.path.normpath(os.path.join(os.path.dirname(pag), unquote(u.path))) if u.path else pag
            rel = os.path.relpath(pag, APP)
            if not tinta.startswith(APP + os.sep) or not os.path.isfile(tinta):
                probleme.append((rel, h, "fișierul nu există")); continue
            anc = unquote(u.fragment)
            if anc and tinta.endswith(".html") and anc not in id_uri(tinta):
                probleme.append((rel, h, "ancora nu există"))
            if u.query and os.path.basename(tinta) == "index.html":
                for i in ",".join(parse_qs(u.query).get("intrebari", [])).split(","):
                    if i and i not in ids_banca:
                        probleme.append((rel, h[:80], "întrebare inexistentă: " + i))
    return probleme

if __name__ == "__main__":
    p = verifica()
    for rel, h, motiv in p[:30]:
        print("EȘEC %s: %s — %s" % (rel, h, motiv))
    print("OK: linkuri în %d pagini" % len(PAGINI) if not p else "%d linkuri rupte" % len(p))
    sys.exit(1 if p else 0)
