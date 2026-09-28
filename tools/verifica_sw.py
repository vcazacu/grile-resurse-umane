#!/usr/bin/env python3
"""Lista FISIERE din sw.js = exact fișierele aplicației + toate paginile generate; fiecare pagină încarcă
actualizare.js (altfel prima deschidere după o actualizare rămâne pe versiunea veche din cache).
Rulare: python3 verifica_sw.py   (exit 1 la fișier lipsă din listă sau din disc)"""
import pathlib, re, sys
APP = pathlib.Path(__file__).resolve().parent.parent
sw = (APP / "sw.js").read_text(encoding="utf-8")
lista = set(re.findall(r'"\./([^"]*)"', sw.split("FISIERE", 1)[1].split("];", 1)[0]))
pe_disc = {p.relative_to(APP).as_posix() for d in ("tematica", "legislatie") for p in (APP / d).glob("*.html")}
esec = ["lipsește din FISIERE: " + f for f in sorted(pe_disc - lista)]
esec += ["în FISIERE, dar nu pe disc: " + f for f in sorted(lista) if f and not (APP / f).is_file()]
if "actualizare.js" not in lista:
    esec.append("lipsește din FISIERE: actualizare.js")
for f in ["index.html"] + sorted(pe_disc):
    if 'src="%sactualizare.js"' % ("../" if "/" in f else "") not in (APP / f).read_text(encoding="utf-8"):
        esec.append("nu încarcă actualizare.js: " + f)
print("\n".join(esec) if esec else "OK: %d fișiere în cache-ul offline" % len(lista))
sys.exit(1 if esec else 0)
