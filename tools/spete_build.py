#!/usr/bin/env python3
"""Construiește paginile de spețe (quiz-app/spete/*.html) din tools/spete/NN.json.

Utilizare: python3 spete_build.py        (construiește + verifică; exit 1 la citat neconfirmat)

Fișier de conținut (NN.json): {nr, nivel: simpla|medie|complexa, titlu, teme:[nr temă], fapte:[…],
intrebare, calcul?: {serviciu:{…}, munca:{…}, conditii:{deosebite|speciale|alte: ani}},
sectiuni:[{titlu, paragrafe:[…], arata_calcul?: true, temei:[{act, articol, citat, fisier, anexa?, tip?}]}],
verdict, capcane:[…]}. Secțiunile sunt pașii rezolvării; în pagină se deschid unul câte unul.

Verificări (aceleași ca la tematica, plus două): fiecare citat e găsit verbatim în lege
(temeiurile cu tip="decizie" — dispozitivul unei hotărâri prealabile — se caută în notele
portalului de la articolul respectiv, nu în textul normativ); cifrele din `calcul` se
calculează aici, după art. 3, 24, 29 și 30 din Legea 223/2015, și fiecare valoare trebuie să
apară în textul rezolvării. Scrie lista fișierelor în sw.js între /* SPETE-START */ … /* SPETE-END */.
"""
import glob, html, json, os, re, sys
import carcasa
from tematica_build import (verifica_temei, in_tematica, temei_html, referinte, consolidari_html,
                            TEME, SUBSOL, nr_cu, LEG)

DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(DIR, "..", "spete")
NIVELURI = [("simpla", "simplă", "Un articol, o condiție"), ("medie", "medie", "Două-trei articole și un calcul"),
            ("complexa", "complexă", "Mai multe acte și o excepție")]
NIVEL_NUME = {k: v for k, v, _ in NIVELURI}

_NUM = re.compile(r"(?<![\w^/–-])(\d+(?:[.,]\d+)?)(?![\w^/–-])")      # nu prinde 40/2025, 20^1, 2^1
_REF = re.compile(r"(?:art\.|alin\.|lit\.|pct\.|nr\.|anexa|anexele|capitol)\s*(?:\(|nr\.\s*)?$", re.I)

def _numere(text):
    """Cifrele din text care nu sunt numere de articol/alineat/literă/act („art. 94”, „HP nr. 40/2025”)."""
    return [m.group(1) for m in _NUM.finditer(text) if not _REF.search(text[max(0, m.start() - 12):m.start()])]

def note_articol(fisier, art):
    """Notele portalului (§NOTA§) din interiorul articolului dat, în corpul legii."""
    note, in_art = [], False
    for l in open(os.path.join(LEG, fisier), encoding="utf-8").read().split("\n"):
        if l.startswith("§ANEXA§"): break
        m = re.match(r"^Articolul (\d+(?:\^\d+)?)$", l)
        if m: in_art = (m.group(1) == art); continue
        if l.startswith("## "): in_art = False; continue
        if in_art and l.startswith("§NOTA§"): note.append(l[len("§NOTA§"):].strip())
    return note

def verifica_decizie(t):
    """Citatul unei hotărâri prealabile trebuie găsit verbatim în notele articolului."""
    from normalizare import normalizeaza
    m = re.search(r"art\.\s*(\d+(?:\^\d+)?)", t["articol"])
    if not m: return False, "articolul deciziei nu e identificabil: " + t["articol"]
    corp = normalizeaza(" ".join(note_articol(t["fisier"], m.group(1))))
    return (True, "") if normalizeaza(t["citat"]) in corp else (False, "dispozitiv negăsit în notele art. %s" % m.group(1))

def calculeaza(c):
    """Vechimile după Legea 223/2015: art. 3 lit. e)/f)/g), art. 24, art. 29, art. 30."""
    serviciu = sum(c.get("serviciu", {}).values())
    munca = sum(c.get("munca", {}).values())
    cond = c.get("conditii", {})
    spor = cond.get("deosebite", 0) * 0.25 + cond.get("speciale", 0) * 0.5 + cond.get("alte", 0) * 1.0
    cumulata = serviciu + munca + spor
    efectiva = cumulata - spor
    ani_cum = int(cumulata + 0.5) if cumulata - int(cumulata) >= 0.5 else int(cumulata)   # art. 25 alin. (3)
    procent = min(85, 65 + (ani_cum - 25)) if ani_cum >= 25 else 65 - (25 - ani_cum)
    def f(x): return ("%d" % x) if float(x).is_integer() else ("%.1f" % x).replace(".", ",")
    rows = [(k + " (vechime în serviciu)", f(v)) for k, v in c.get("serviciu", {}).items()]
    rows += [(k + " (vechime în muncă)", f(v)) for k, v in c.get("munca", {}).items()]
    rows += [("spor de timp, art. 24: %s" % ", ".join("%s ani în condiții %s" % (f(v), k) for k, v in cond.items()), f(spor))]
    rows += [("vechime în serviciu (art. 3 lit. e))", f(serviciu)), ("vechime cumulată (art. 3 lit. f))", f(cumulata)),
             ("vechime efectivă (art. 3 lit. g))", f(efectiva)), ("procent din baza de calcul (art. 29, 30)", f(procent) + "%")]
    return rows, {f(serviciu), f(munca), f(spor), f(cumulata), f(efectiva), f(procent)}

JS = """
(function(){
  var pasi = Array.prototype.slice.call(document.querySelectorAll('details.pas'));
  function deblocheaza(i){ var p = pasi[i]; if(!p) return; p.classList.remove('blocat'); p.querySelector('summary').removeAttribute('aria-disabled'); }
  pasi.forEach(function(p, i){
    if(i > 0){ p.classList.add('blocat'); p.querySelector('summary').setAttribute('aria-disabled', 'true'); }
    p.querySelector('summary').addEventListener('click', function(e){ if(p.classList.contains('blocat')) e.preventDefault(); });
    p.addEventListener('toggle', function(){ if(p.open) deblocheaza(i + 1); });
  });
  var tot = document.getElementById('arata-tot');
  if(tot) tot.addEventListener('click', function(){ pasi.forEach(function(p, i){ deblocheaza(i); p.open = true; }); tot.hidden = true; });
})();
"""

def pagina(d, slug, vecini):
    nr, nivel = d["nr"], d["nivel"]
    corp = [carcasa.cap("Speța %d · nivel %s" % (nr, NIVEL_NUME[nivel]), d["titlu"], ("index.html", "Toate spețele"),
                        meta='<span class="nivel %s">%s</span>' % (nivel, NIVEL_NUME[nivel]))]
    corp.append('<section class="fapte"><span class="eyebrow">Situația de fapt</span><ol>%s</ol><p class="intrebare">%s</p></section>'
                % ("".join("<li>%s</li>" % html.escape(f) for f in d["fapte"]), html.escape(d["intrebare"])))
    corp.append('<section class="rezolvare"><div class="spete-bara"><h2>Rezolvarea, pas cu pas</h2>'
                '<button type="button" class="btn btn-outline" id="arata-tot">Arată toată rezolvarea</button></div>')
    rows = calculeaza(d["calcul"])[0] if d.get("calcul") else None
    for k, s in enumerate(d["sectiuni"], 1):
        corp.append('<details class="pas" id="pas-%d"%s><summary><span class="nr-pas">Pasul %d</span><span>%s</span></summary><div class="pas-corp">'
                    % (k, " open" if k == 1 else "", k, html.escape(s["titlu"])))
        for p in s["paragrafe"]: corp.append("<p>%s</p>" % html.escape(p))
        if s.get("arata_calcul") and rows:
            corp.append('<table class="calcul">%s</table>' % "".join("<tr><td>%s</td><td>%s</td></tr>" % (html.escape(a), html.escape(b)) for a, b in rows))
        if s.get("temei"):
            corp.append('<details class="temei"><summary><span class="eyebrow">Temei legal</span><span class="refs">%s</span>'
                        '<svg class="chevron" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" '
                        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="6 9 12 15 18 9"></polyline></svg></summary>'
                        '<div class="temei-corp">' % referinte(s["temei"]))
            for t in s["temei"]:
                h = temei_html(t)
                if t.get("tip") == "decizie": h = h.replace('<div class="legal-card">', '<div class="legal-card decizie">', 1)
                corp.append(h)
            corp.append("</div></details>")
        corp.append("</div></details>")
    corp.append('<details class="pas verdict"><summary><span class="nr-pas">Verdict</span><span>Răspunsul</span></summary>'
                '<div class="pas-corp"><p>%s</p></div></details></section>' % html.escape(d["verdict"]))
    if d.get("capcane"):
        corp.append('<section class="capcane"><h2>Capcane de examen</h2><ul>%s</ul></section>'
                    % "".join("<li>%s</li>" % html.escape(c) for c in d["capcane"]))
    teme = [(n, sl, ti) for n, sl, ti in TEME if n in d.get("teme", [])]
    if teme:
        corp.append('<section class="exersare"><div><h2>Tema din tematica</h2><p>%s</p></div></section>'
                    % " · ".join('<a href="../tematica/%02d-%s.html">%d. %s</a>' % (n, sl, n, html.escape(ti)) for n, sl, ti in teme))
    corp.append(consolidari_html(d))
    prec, urm = vecini
    if prec or urm:
        def v(t, cls, et):
            if not t: return "<span></span>"
            return '<a class="%s" href="%s.html"><span class="eyebrow">%s</span><span>%s</span></a>' % (cls, t[0], et, html.escape(t[1]))
        corp.append('<nav class="vecini" aria-label="Spețe vecine">%s%s</nav>'
                    % (v(prec, "prec", "← Speța anterioară"), v(urm, "urm", "Speța următoare →")))
    return carcasa.pagina("Speța %d. %s" % (nr, d["titlu"]), "\n".join(corp), "spete", subsol=SUBSOL, script=JS, cls="pagina-tema")

def index_html(lista):
    corp = [carcasa.cap(nr_cu(len(lista), "spețe"), "Spețe din domeniul militar",
                        meta=html.escape("Situații concrete rezolvate pas cu pas, cu temeiul citat din lege. Încearcă întâi singur: pașii se deschid unul câte unul."))]
    for cheie, nume, desc in NIVELURI:
        rows = [x for x in lista if x[1]["nivel"] == cheie]
        if not rows: continue
        li = "".join('<li><a class="rand-lista" href="%s.html"><span class="nr">%02d</span><span class="text"><span class="titlu">%s</span>'
                     '<span class="det">%s</span></span>%s</a></li>'
                     % (slug, d["nr"], html.escape(d["titlu"]), html.escape(d["intrebare"][:110] + ("…" if len(d["intrebare"]) > 110 else "")), carcasa.icon("dreapta", 18))
                     for slug, d in rows)
        corp.append('<section class="tem-sec"><h2><span class="nivel %s">%s</span> %s</h2><ul class="lista">%s</ul></section>'
                    % (cheie, nume, html.escape(desc), li))
    return carcasa.pagina("Spețe", "\n".join(corp), "spete", pe_index=True, subsol=SUBSOL)

def slug_din(d):
    s = re.sub(r"[^a-z0-9]+", "-", d["titlu"].lower().translate(str.maketrans("ăâîșțĂÂÎȘȚ", "aaistAAIST"))).strip("-")
    if len(s) > 60: s = s[:60].rsplit("-", 1)[0]      # taie la o liniuță, nu în mijlocul unui cuvânt
    return "%02d-%s" % (d["nr"], s.rstrip("-"))

def main():
    os.makedirs(OUT, exist_ok=True)
    erori, lista = 0, []
    for cale in sorted(glob.glob(os.path.join(DIR, "spete", "[0-9][0-9].json"))):
        d = json.load(open(cale, encoding="utf-8"))
        lista.append((slug_din(d), d))
    for i, (slug, d) in enumerate(lista):
        n_ok = n_tot = 0
        for s in d["sectiuni"]:
            for t in s.get("temei", []):
                n_tot += 1
                ok, msg = verifica_decizie(t) if t.get("tip") == "decizie" else verifica_temei(t)
                if ok: n_ok += 1
                else: erori += 1; print("  EROARE speța %d, „%s”, %s: %s" % (d["nr"], s["titlu"], t["articol"], msg))
                if t.get("tip") != "decizie" and in_tematica(t) is False:
                    print("  ATENȚIE speța %d: %s din %s nu e în bibliografie (doar context)" % (d["nr"], t["articol"], t["fisier"]))
        if d.get("calcul"):
            _, valori = calculeaza(d["calcul"])
            text = " ".join(p for s in d["sectiuni"] for p in s["paragrafe"]) + " " + d["verdict"]
            for v in sorted(valori):
                if not re.search(r"(?<![\d,.])%s(?![\d,])" % re.escape(v), text):
                    erori += 1; print("  EROARE speța %d: valoarea calculată %s nu apare în rezolvare" % (d["nr"], v))
            # și invers: orice procent din text trebuie să fie ori cel calculat, ori o cifră a legii
            # (65%, 85%, 1%/an, diferența de ani) — poarta semantică nu face aritmetică, codul da
            _, val = calculeaza(d["calcul"]); permise = set(val) | {"65", "85", "1", "50"}
            for m in re.finditer(r"(?<![\d,.])(\d+(?:,\d+)?)%", text):
                if m.group(1) not in permise:
                    erori += 1; print("  EROARE speța %d: procentul %s%% din rezolvare nu rezultă din calcul" % (d["nr"], m.group(1)))
        # orice cifră din rezolvare trebuie să vină din fapte, dintr-un citat, din calcul sau să fie
        # declarată în `cifre_derivate` (cu derivarea ei) — poarta semantică nu face aritmetică
        text = " ".join(p for s in d["sectiuni"] for p in s["paragrafe"]) + " " + d["verdict"]
        surse = " ".join(d["fapte"]) + " " + " ".join(t["citat"] for s in d["sectiuni"] for t in s.get("temei", []))
        permise = set(_numere(surse)) | set(d.get("cifre_derivate", {}))
        if d.get("calcul"): permise |= calculeaza(d["calcul"])[1]
        for n in sorted(set(_numere(text)) - permise):
            erori += 1; print("  EROARE speța %d: cifra %s din rezolvare nu vine din fapte, citate, calcul sau cifre_derivate" % (d["nr"], n))
        prec = (lista[i - 1][0], lista[i - 1][1]["titlu"]) if i > 0 else None
        urm = (lista[i + 1][0], lista[i + 1][1]["titlu"]) if i + 1 < len(lista) else None
        open(os.path.join(OUT, slug + ".html"), "w", encoding="utf-8").write(pagina(d, slug, (prec, urm)))
        print("speța %d (%s): %d pași, %d/%d citate confirmate → spete/%s.html" % (d["nr"], d["nivel"], len(d["sectiuni"]), n_ok, n_tot, slug))
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(index_html(lista))
    fisiere = ["./spete/index.html"] + ["./spete/%s.html" % slug for slug, _ in lista]
    sw = os.path.join(DIR, "..", "sw.js"); s = open(sw, encoding="utf-8").read()
    bloc = "/* SPETE-START */\n" + "".join('  "%s",\n' % f for f in fisiere) + "  /* SPETE-END */"
    s2 = re.sub(r"/\* SPETE-START \*/.*?/\* SPETE-END \*/", bloc, s, flags=re.S)
    if s2 != s: open(sw, "w", encoding="utf-8").write(s2); print("sw.js: %d fișiere de spețe în FISIERE" % len(fisiere))
    print("spețe: %d; erori: %d" % (len(lista), erori))
    sys.exit(1 if erori else 0)

if __name__ == "__main__":
    main()
