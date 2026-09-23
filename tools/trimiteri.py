#!/usr/bin/env python3
"""Gramatica trimiterilor interne dintr-un text de lege, pentru paginile de citit.

Recunoaște, determinist, formele:
  art. 36 alin. 1 lit. a)      art. 20^1 alin. 1, 2 și 2^1      art. 7 alin. (2)
  alin. 1 și 2 (același articol)          lit. a) și b) (același alineat)
  alin. 1 lit. b)-f) (interval)           alin. 2^1 paragraful B lit. c) (grup de litere)
Trimiterile către alt act („… din Legea nr. 384/2006") sau către anexe rămân text simplu.

marcheaza(text, ctx, rez) întoarce HTML (text scăpat) în care fiecare element rezolvat
e un <a class="trm" href="#id" data-t="id …" data-e="etichetă|…">. `ctx` = (articol,
alineat, grup) în care stă textul; `rez(fel, art, alin, lit, grup)` — dat de apelant —
întoarce (id, etichetă) sau None când ținta nu există (fel ∈ art, alin, lit).
"""
import html, re, string

NR = r"\d+(?:\^\d+)?"
LT = r"[a-zșț](?:\^\d+)?"
_SEP = r"\s*(?:,|și|ori|sau|precum și)\s*"
_RNG = r"\s*[-–]\s*"
_AI = r"\(?" + NR + r"\)?"
_LI = LT + r"\)"
_ALIST = _AI + r"(?:(?:" + _SEP + "|" + _RNG + ")" + _AI + ")*"
_LLIST = _LI + r"(?:(?:" + _SEP + "|" + _RNG + ")" + _LI + ")*"
_G = r"(?:\s*(?:paragraful|punctul|pct\.)\s*(?P<%s>[A-Z](?:\^\d+)?))"
_TOKEN = re.compile(
    r"(?:(?P<art>\bart\.\s*(?P<artnr>" + NR + r"))(?:\s*\balin\.\s*(?P<alin1>" + _ALIST + r"))?"
    r"|\balin\.\s*(?P<alin2>" + _ALIST + r"))" + _G % "grupA" + r"?(?:\s*\blit\.\s*(?P<lit1>" + _LLIST + r"))?"
    r"|" + _G % "grupB" + r"?\s*\blit\.\s*(?P<lit2>" + _LLIST + r")", re.I)
_ITEM_A = re.compile(r"(\(?" + NR + r"\)?)(?:" + _RNG + r"(\(?" + NR + r"\)?))?")
_ITEM_L = re.compile(r"(" + LT + r")\)(?:" + _RNG + r"(" + LT + r")\))?")
_EXTERN = re.compile(r"^\s*,?\s*(?:din|al|ale|a|la|potrivit)\s+(?:Legea|Legii|Ordonan|O\.\s*U\.\s*G|Hotărâr|H\.\s*G|"
                     r"Codul|Codului|Constituț|Regulament|Decret|Statut|Normel|anexa|anexei|Anexa|Tratat)", re.I)
_LIT_PREFIX = re.compile(r"\blit\.\s*$", re.I)

def _extern_dupa(text, poz):
    """E tokenul urmat de „din Legea…"? Sare peste o listă „…, art. 70 și art. 103" ca să vadă
    ce vine după ultimul element — altfel primele articole din listă s-ar lega în actul curent."""
    while True:
        if _EXTERN.match(text[poz:poz + 60]): return True
        m2 = re.match(r"\s*(?:,|și|sau|ori)\s*", text[poz:])
        if not m2: return False
        m3 = _TOKEN.match(text, poz + m2.end())
        if not m3 or not m3.group("art"): return False
        poz = m3.end()

def _curat(x):
    return x.strip("()")

def _interval(a, b, litere):
    """Extinde un interval: 1–3 → 1,2,3; b–f → b,c,d,e,f. Cu indice (2^1) rămân capetele."""
    if "^" in a or "^" in b:
        return [a, b]
    if litere:
        abc = string.ascii_lowercase
        if a in abc and b in abc and abc.index(a) < abc.index(b):
            return list(abc[abc.index(a):abc.index(b) + 1])
        return [a, b]
    ia, ib = int(a), int(b)
    return [str(x) for x in range(ia, ib + 1)] if ia < ib and ib - ia <= 30 else [a, b]

def _link(text, tinte):
    ids = " ".join(i for i, _ in tinte); et = "|".join(e for _, e in tinte)
    return '<a class="trm" href="#%s" data-t="%s" data-e="%s">%s</a>' % (tinte[0][0], ids, html.escape(et, quote=True), html.escape(text))

def marcheaza(text, ctx, rez, stat=None):
    ctx_art, ctx_alin, ctx_grup = ctx
    out, poz = [], 0
    for m in _TOKEN.finditer(text):
        s = m.group(0)
        out.append(html.escape(text[poz:m.start()])); poz = m.end()
        if _extern_dupa(text, m.end()):
            if stat is not None: stat["extern"] = stat.get("extern", 0) + 1
            out.append(html.escape(s)); continue
        art = m.group("artnr") or ctx_art
        grup = m.group("grupA") or m.group("grupB")
        piese = []                      # (start, end, text, tinte|None)
        # articolul
        if m.group("art"):
            a, b = m.span("art"); a -= m.start(); b -= m.start()
            t = rez("art", art, None, None, None)
            piese.append((a, b, s[a:b], [t] if t else None))
            if not t:                   # articol inexistent: nimic din token nu se leagă
                if stat is not None: stat["nelegate"] = stat.get("nelegate", 0) + 1
                out.append(html.escape(s)); continue
        # alineatele
        alineate = []
        nume_alin = "alin1" if m.group("alin1") else ("alin2" if m.group("alin2") else None)
        if nume_alin:
            a, b = m.span(nume_alin); a -= m.start(); b -= m.start()
            kw = re.search(r"\balin\.\s*$", s[:a], re.I)
            for k, im in enumerate(_ITEM_A.finditer(s[a:b])):
                x, y = _curat(im.group(1)), (_curat(im.group(2)) if im.group(2) else None)
                nrs = _interval(x, y, False) if y else [x]
                tinte = [rez("alin", art, n, None, None) for n in nrs]
                tinte = [t for t in tinte if t]
                st = (kw.start() if (k == 0 and kw) else a + im.start())
                piese.append((st, a + im.end(), s[st:a + im.end()], tinte or None))
                alineate.extend(nrs)
        # literele
        nume_lit = "lit1" if m.group("lit1") else ("lit2" if m.group("lit2") else None)
        if nume_lit:
            a, b = m.span(nume_lit); a -= m.start(); b -= m.start()
            baza_alin = alineate or [None if m.group("art") else ctx_alin]
            g = grup if grup else (ctx_grup if not m.group("art") and not nume_alin else None)
            for im in _ITEM_L.finditer(s[a:b]):
                x, y = im.group(1), im.group(2)
                lts = _interval(x, y, True) if y else [x]
                tinte = [rez("lit", art, al, lt, g) for al in baza_alin for lt in lts]
                tinte = [t for t in tinte if t]
                piese.append((a + im.start(), a + im.end(), s[a + im.start():a + im.end()], tinte or None))
        # asamblare
        cur = 0
        for st, en, tx, tinte in sorted(piese):
            out.append(html.escape(s[cur:st]))
            if tinte:
                out.append(_link(tx, tinte))
                if stat is not None: stat["legate"] = stat.get("legate", 0) + 1
            else:
                out.append(html.escape(tx))
                if stat is not None: stat["nelegate"] = stat.get("nelegate", 0) + 1
            cur = en
        out.append(html.escape(s[cur:]))
    out.append(html.escape(text[poz:]))
    return "".join(out)
