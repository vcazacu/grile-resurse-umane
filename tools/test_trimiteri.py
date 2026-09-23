#!/usr/bin/env python3
"""Teste pentru gramatica trimiterilor (trimiteri.py). Rulare: python3 test_trimiteri.py"""
import re, sys
from trimiteri import marcheaza

def rez(fel, art, alin, lit, grup):
    """Rezolvator de test: totul există, cu excepția art. 999, alin. 9 și lit. z)."""
    if art == "999" or alin == "9" or lit == "z": return None
    idd = "art-%s" % art.replace("^", "-")
    if alin: idd += "-al-" + alin.replace("^", "-")
    if grup: idd += "-g" + grup
    if lit: idd += "-lit-" + lit.replace("^", "-")
    return idd, "et"

def linkuri(html):
    return re.findall(r'<a class="trm" href="#([^"]+)"[^>]*>([^<]*)</a>', html)

CAZURI = [
 # text, context (art, alin, grup), linkuri așteptate [(id, text)]
 ("prevăzute la art. 36 alin. 1 lit. a)", ("50", "2", None),
  [("art-36", "art. 36"), ("art-36-al-1", "alin. 1"), ("art-36-al-1-lit-a", "a)")]),
 ("potrivit alin. 1 și 2 se aprobă", ("50", "3", None),
  [("art-50-al-1", "alin. 1"), ("art-50-al-2", "2")]),
 ("celor prevăzute la lit. a) și b);", ("50", "2", None),
  [("art-50-al-2-lit-a", "a)"), ("art-50-al-2-lit-b", "b)")]),
 ("în condițiile prevăzute la alin. 1 lit. b), c) și e)", ("50", "2", None),
  [("art-50-al-1", "alin. 1"), ("art-50-al-1-lit-b", "b)"), ("art-50-al-1-lit-c", "c)"), ("art-50-al-1-lit-e", "e)")]),
 ("acordarea gradelor prevăzute la alin. 1 lit. b)-f) și înaintarea", ("50", "2", None),
  [("art-50-al-1", "alin. 1"), ("art-50-al-1-lit-b", "b)-f)")]),          # interval: un singur link, ținte b..f
 ("art. 45 alin. (1) lit. a), b) și h) din Legea nr. 384/2006, cu modificările", ("50", "2", None), []),  # alt act
 ("prevăzute la art. 20^1 alin. 1, 2 și 2^1 din prezenta lege", ("50", "2", None),
  [("art-20-1", "art. 20^1"), ("art-20-1-al-1", "alin. 1"), ("art-20-1-al-2", "2"), ("art-20-1-al-2-1", "2^1")]),
 ("generali și amirali, prevăzuți la alin. 2^1 paragraful B lit. c);", ("2", "2", None),
  [("art-2-al-2-1", "alin. 2^1"), ("art-2-al-2-1-gB-lit-c", "c)")]),
 ("Art. 7 alin. (2) se aplică", ("50", "1", None), [("art-7", "Art. 7"), ("art-7-al-2", "alin. (2)")]),
 ("prevăzute la art. 999", ("50", "1", None), []),                          # țintă inexistentă: text simplu
 ("potrivit alin. 9 lit. a)", ("50", "1", None), []),                       # alineat inexistent: nici litera
 ("lit. z) nu există", ("50", "1", None), []),
 ("art. 3 din anexa nr. VI la prezenta lege", ("50", "1", None), []),      # anexă: alt spațiu de numerotare
 ("în condițiile art. 15 alin. (1) lit. c^1) din", ("50", "1", None),
  [("art-15", "art. 15"), ("art-15-al-1", "alin. (1)"), ("art-15-al-1-lit-c-1", "c^1)")]),
 ("<b>&amp; text fără trimiteri", ("50", "1", None), []),
 ("potrivit art. 67, art. 70 și art. 76 alin. (1) și (2) din Legea nr. 227/2015", ("50", "1", None), []),  # listă externă
 ("potrivit art. 67 și alin. 2", ("50", "1", None), [("art-67", "art. 67"), ("art-50-al-2", "alin. 2")]),
]

ok = 0
for text, ctx, astept in CAZURI:
    h = marcheaza(text, ctx, rez)
    got = linkuri(h)
    if got == astept and "<b>" not in h: ok += 1
    else: print("EȘEC:", text, "\n   așteptat:", astept, "\n   obținut: ", got, "\n   html:", h)
# interval: țintele b..f
h = marcheaza("lit. b)-f)", ("50", "1", None), rez)
t = re.search(r'data-t="([^"]+)"', h).group(1).split()
if t == ["art-50-al-1-lit-%s" % c for c in "bcdef"]: ok += 1
else: print("EȘEC interval:", t)
print("%d/%d teste trec" % (ok, len(CAZURI) + 1))
sys.exit(0 if ok == len(CAZURI) + 1 else 1)
