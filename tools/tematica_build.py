#!/usr/bin/env python3
"""Construiește paginile de sinteză pe teme (quiz-app/tematica/*.html) din fișierele
de conținut tools/tematica/NN.json și verifică fiecare citat contra legislației.

Utilizare: python3 tematica_build.py            (construiește + verifică; exit 1 la citat neconfirmat)
Fișier de conținut (NN.json): {nr, titlu, rezumat, sectiuni:[{titlu, paragrafe:[…],
temei:[{act, articol, citat, fisier, anexa?}]}], capcane:[…], intrebari:[id-uri]}.
Scrie și lista fișierelor în sw.js între marcajele /* TEMATICA-START */ … /* TEMATICA-END */.
"""
import json, os, re, sys, html, glob
from normalizare import normalizeaza, fragmente_citat, linii_zona
from bibliografie import tematica as bib_tematica
from legislatie_build import ACTE, ancora
import carcasa
from urllib.parse import quote

SLUG_ACT = {fisier: slug for fisier, slug, _, _ in ACTE}

DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(DIR, "..", "tematica")
LEG = os.path.join(DIR, "..", "..", "legislatie")

TEME = [
 (1, "gradele-militare-si-stagiile-minime-in-grad", "Gradele militare și stagiile minime în grad"),
 (2, "indatoririle-si-drepturile-cadrelor-militare", "Îndatoririle și drepturile cadrelor militare"),
 (3, "interzicerea-sau-restrangerea-unor-drepturi", "Interzicerea sau restrângerea exercițiului unor drepturi și libertăți"),
 (4, "provenienta-ofiterilor-maistrilor-si-subofiterilor", "Proveniența ofițerilor, maiștrilor militari și subofițerilor"),
 (5, "disciplina-militara", "Disciplina militară"),
 (6, "acordarea-gradelor-si-inaintarea-in-grad", "Acordarea gradelor și înaintarea cadrelor militare în gradele următoare"),
 (7, "trecerea-in-rezerva-sau-in-retragere", "Trecerea în rezervă sau direct în retragere a cadrelor militare"),
 (8, "organizarea-si-functionarea-sie", "Organizarea și funcționarea Serviciului de Informații Externe"),
 (9, "contractul-individual-de-munca", "Raporturile de muncă – contractul individual de muncă: încheierea, executarea, modificarea, suspendarea și încetarea"),
 (10, "tipurile-de-contract-individual-de-munca", "Tipurile de contract individual de muncă"),
 (11, "timpul-de-munca-si-timpul-de-odihna", "Timpul de muncă și timpul de odihnă"),
 (12, "raspunderea-disciplinara-a-salariatilor", "Răspunderea disciplinară a salariaților"),
 (13, "sistemul-pensiilor-militare-de-stat", "Sistemul pensiilor militare de stat"),
 (14, "sistemul-public-de-pensii", "Sistemul public de pensii"),
 (15, "salarizarea-personalului-militar-si-contractual", "Salarizarea personalului militar și contractual (familia ocupațională „apărare, ordine publică și securitate națională”)"),
 (16, "concediul-si-indemnizatia-pentru-cresterea-copiilor", "Concediul și indemnizația lunară pentru creșterea copiilor"),
 (17, "stimulentul-de-insertie", "Stimulentul de inserție"),
 (18, "compensatia-lunara-pentru-chirie", "Acordarea compensației lunare pentru chirie cadrelor militare în activitate"),
]

SCURT = {"01": "Legea 80/1995", "02": "Legea 1/1998", "03": "Codul muncii", "04": "Legea 223/2015",
         "05": "Legea 360/2023", "06": "Legea 153/2017", "07": "O.U.G. 111/2010", "08": "Normele H.G. 52/2011",
         "09": "H.G. 1867/2005"}
SUBSOL = "Surse: formele consolidate la zi de pe legislatie.just.ro; citatele sunt verificate automat contra textului."

def nr_cu(n, cuvant):
    """„3 întrebări”, „20 de întrebări”, „110 întrebări”: de la 20 în sus (fără 101–119, 201–219 …) se pune „de”."""
    return "%d %s%s" % (n, "de " if n % 100 == 0 and n or n % 100 >= 20 else "", cuvant)

def ids_din_banca():
    """Id-urile întrebărilor din ../intrebari.js: butonul de exersare trimite doar întrebări care există."""
    cale = os.path.join(DIR, "..", "intrebari.js")
    return set(re.findall(r'"id":\s*"([^"]+)"', open(cale, encoding="utf-8").read())) if os.path.exists(cale) else set()

def verifica_temei(t):
    """Întoarce (ok, mesaj). Citatul trebuie găsit verbatim (normalizat) în zona declarată."""
    L = linii_zona(os.path.join(LEG, t["fisier"]), t.get("anexa", ""))
    if L is None: return False, "fișier lipsă: " + t["fisier"]
    corp = normalizeaza(" ".join(l for _, l in L))
    poz = 0
    for f in fragmente_citat(t["citat"]):
        i = corp.find(f, poz)
        if i < 0: return False, "fragment negăsit: „%s”" % f[:70]
        poz = i + len(f)
    return True, ""

def in_tematica(t):
    m = re.match(r"^art\.\s*(\d+(?:\^\d+)?)", t["articol"])
    if not m: return None
    k = t["fisier"] + ("#" + t["anexa"] if t.get("anexa") else "")
    tt = bib_tematica().get(k)
    return bool(tt) and m.group(1) in tt[2]

def link_lege(t):
    """Adresa articolului în paginile de legislație (legislatie/<slug>.html#art-N), sau "" dacă nu se poate."""
    m = re.search(r"art\.\s*(\d+(?:\^\d+)?)", t["articol"])
    slug = SLUG_ACT.get(t["fisier"])
    return "../legislatie/%s.html#%s" % (slug, ancora(m.group(1), t.get("anexa", ""))) if m and slug else ""

def temei_html(t):
    art = html.escape(t["articol"]); adresa = link_lege(t)
    link = '<div class="fisier"><a href="%s">Deschide în lege</a></div>' % adresa if adresa else ""
    return ('<div class="legal-card"><div class="act">%s</div><span class="articol">%s</span>'
            '<blockquote>„%s”</blockquote>%s</div>'
            % (html.escape(t["act"]), art, html.escape(t["citat"]), link))

def referinte(temei):
    """Rezumatul din titlul unui temei restrâns: „art. 2 · art. 3 alin. (1)”, cu actul în față
    doar când secțiunea citează din mai multe acte (sau din anexă)."""
    def act(t): return SCURT.get(t["fisier"][:2], "") + (" anexa VI" if t.get("anexa") else "")
    acte = {act(t) for t in temei}
    parti = []
    for t in temei:   # două citate din același articol apar o singură dată
        x = (act(t) + ", " if len(acte) > 1 else "") + t["articol"]
        if x not in parti: parti.append(x)
    return " · ".join(html.escape(x) for x in parti)

def consolidari_html(d):
    """„Forma consolidată folosită: <act> — <data>” pentru fiecare fișier din temeiurile temei."""
    fis = []
    for sct in d["sectiuni"]:
        for t in sct.get("temei", []):
            if t["fisier"] not in fis: fis.append(t["fisier"])
    rand = []
    for f in fis:
        antet = open(os.path.join(LEG, f), encoding="utf-8").readline()
        m = re.search(r"consolidarea din ([\d.]+)", antet)
        den = next((dn for ff, _, dn, _ in ACTE if ff == f), f)
        rand.append("%s — %s" % (den, m.group(1) if m else "?"))
    return '<p class="nota-mica">Forma consolidată folosită: %s.</p>' % html.escape("; ".join(rand)) if rand else ""

def pagina(d, slug, vecini=(None, None), in_banca=frozenset()):
    nr = d["nr"]
    corp = [carcasa.cap("Tema %d din %d" % (nr, len(TEME)), d["titlu"], ("index.html", "Toate temele"))]
    corp.append('<section class="pe-scurt"><span class="eyebrow">Pe scurt</span><p>%s</p></section>' % html.escape(d["rezumat"]))
    for s in d["sectiuni"]:
        corp.append('<section class="tem-sec"><h2>%s</h2>' % html.escape(s["titlu"]))
        for p in s["paragrafe"]: corp.append("<p>%s</p>" % html.escape(p))
        if s.get("temei"):
            corp.append('<details class="temei"><summary><span class="eyebrow">Temei legal</span>'
                        '<span class="refs">%s</span><svg class="chevron" width="18" height="18" viewBox="0 0 24 24" fill="none" '
                        'stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
                        '<polyline points="6 9 12 15 18 9"></polyline></svg></summary><div class="temei-corp">' % referinte(s["temei"]))
            corp += [temei_html(t) for t in s["temei"]]
            corp.append("</div></details>")
        corp.append("</section>")
    if d.get("capcane"):
        corp.append('<section class="capcane"><h2>Capcane de examen</h2><ul>%s</ul></section>'
                    % "".join("<li>%s</li>" % html.escape(c) for c in d["capcane"]))
    ids = [i for i in d.get("intrebari", []) if i in in_banca]
    if ids:
        n = min(len(ids), 20)
        href = "../index.html?titlu=%s&intrebari=%s" % (quote("Tema %d" % nr), quote(",".join(ids), safe=","))
        corp.append('<section class="exersare"><div><h2>Exersează tema</h2><p>%s, întâi cele greșite și cele nedate încă.</p></div>'
                    '<a class="btn btn-primary" href="%s">Începe · %s</a></section>'
                    % ("Toate cele %s ale băncii pe această temă" % nr_cu(len(ids), "întrebări") if n == len(ids)
                       else "%s alese din cele %s ale băncii pe această temă" % (nr_cu(n, "întrebări"), nr_cu(len(ids), "întrebări")),
                       href, nr_cu(n, "întrebări")))
    corp.append(consolidari_html(d))
    prec, urm = vecini
    if prec or urm:
        def v(t, cls, eticheta):
            if not t: return '<span></span>'
            return ('<a class="%s" href="%02d-%s.html"><span class="eyebrow">%s</span><span>%s</span></a>'
                    % (cls, t[0], t[1], eticheta, html.escape(t[2])))
        corp.append('<nav class="vecini" aria-label="Teme vecine">%s%s</nav>'
                    % (v(prec, "prec", "← Tema %d" % prec[0] if prec else ""), v(urm, "urm", "Tema %d →" % urm[0] if urm else "")))
    return carcasa.pagina("%d. %s" % (nr, d["titlu"]), "\n".join(corp), "tematica", subsol=SUBSOL, cls="pagina-tema")

def index_html(gata, nr_intrebari=None):
    nr_intrebari = nr_intrebari or {}
    li = []
    for nr, slug, titlu in TEME:
        n = nr_intrebari.get(nr)
        det = '<span class="det">%s în bancă</span>' % nr_cu(n, "întrebări") if n else ""
        if nr in gata:
            li.append('<li><a class="rand-lista" href="%02d-%s.html"><span class="nr">%02d</span><span class="text"><span class="titlu">%s</span>%s</span>%s</a></li>'
                      % (nr, slug, nr, html.escape(titlu), det, carcasa.icon("dreapta", 18)))
        else:
            li.append('<li><span class="rand-lista"><span class="nr">%02d</span><span class="text"><span class="titlu">%s</span>'
                      '<span class="det">în pregătire</span></span></span></li>' % (nr, html.escape(titlu)))
    corp = (carcasa.cap(nr_cu(len(TEME), "teme"), "Tematica examenului",
                        meta="Câte o sinteză pe temă, în același stil ca explicațiile din teste: reguli, termene, excepții și capcane, "
                             "fiecare cu temeiul legal citat verbatim din forma consolidată la zi.")
            + '<ul class="lista">%s</ul>' % "".join(li))
    return carcasa.pagina("Tematica", corp, "tematica", pe_index=True, subsol=SUBSOL)

def main():
    os.makedirs(OUT, exist_ok=True)
    gata, erori, fisiere, pagini = set(), 0, ["./tematica/index.html"], []
    for cale in sorted(glob.glob(os.path.join(DIR, "tematica", "[0-9][0-9].json"))):
        d = json.load(open(cale, encoding="utf-8"))
        nr = d["nr"]; slug = next(s for n, s, _ in TEME if n == nr)
        n_ok = n_tot = 0
        for s in d["sectiuni"]:
            for t in s.get("temei", []):
                n_tot += 1; ok, msg = verifica_temei(t)
                if ok: n_ok += 1
                else: erori += 1; print("  EROARE tema %d, secțiunea „%s”, %s: %s" % (nr, s["titlu"], t["articol"], msg))
                if in_tematica(t) is False: print("  ATENȚIE tema %d: %s din %s nu e în bibliografie (doar context)" % (nr, t["articol"], t["fisier"]))
        nume = "%02d-%s.html" % (nr, slug)
        pagini.append((nume, d, slug)); gata.add(nr); fisiere.append("./tematica/" + nume)
        print("tema %d: %d secțiuni, %d/%d citate confirmate → tematica/%s" % (nr, len(d["sectiuni"]), n_ok, n_tot, nume))
    banca = ids_din_banca()
    for k, (nume, d, slug) in enumerate(pagini):
        prec = next((t for t in TEME if t[0] == pagini[k - 1][1]["nr"]), None) if k > 0 else None
        urm = next((t for t in TEME if t[0] == pagini[k + 1][1]["nr"]), None) if k + 1 < len(pagini) else None
        open(os.path.join(OUT, nume), "w", encoding="utf-8").write(pagina(d, slug, (prec, urm), banca))
    nr_intrebari = {d["nr"]: len([i for i in d.get("intrebari", []) if i in banca]) for _, d, _ in pagini}
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(index_html(gata, nr_intrebari))
    sw = os.path.join(DIR, "..", "sw.js"); s = open(sw, encoding="utf-8").read()
    bloc = "/* TEMATICA-START */\n" + "".join('  "%s",\n' % f for f in fisiere) + "  /* TEMATICA-END */"
    s2 = re.sub(r"/\* TEMATICA-START \*/.*?/\* TEMATICA-END \*/", bloc, s, flags=re.S)
    if s2 != s: open(sw, "w", encoding="utf-8").write(s2); print("sw.js: %d fișiere de tematică în FISIERE" % len(fisiere))
    print("teme gata: %d/18; erori de citat: %d" % (len(gata), erori))
    sys.exit(1 if erori else 0)

if __name__ == "__main__":
    main()
