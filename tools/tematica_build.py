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

CSS = """
.tem-nav { display:flex; gap:0.75rem; flex-wrap:wrap; font-size:0.85rem; margin:0.25rem 0 0.75rem; }
.tem-nav a { color: var(--info); text-decoration:none; } .tem-nav a:hover { text-decoration:underline; }
.tem-list { list-style:none; padding:0; margin:0; display:grid; gap:0.5rem; }
.tem-list li { border:1px solid var(--border); border-radius:0.6rem; padding:0.7rem 0.9rem; display:flex; gap:0.6rem; align-items:baseline; }
.tem-list .nr { font-weight:700; color: var(--muted-foreground); min-width:1.6rem; }
.tem-list a { color: var(--foreground); text-decoration:none; font-weight:600; } .tem-list a:hover { text-decoration:underline; }
.tem-list .soon { color: var(--muted-foreground); }
.tem-sec { margin: 1rem 0; } .tem-sec h3 { font-size:1.02rem; margin:0 0 0.5rem; letter-spacing:-0.01em; }
.tem-sec p { line-height:1.55; margin:0 0 0.6rem; }
.tem-rezumat { font-size:0.95rem; line-height:1.55; border-left:3px solid var(--info); padding-left:0.8rem; margin:0.5rem 0 1rem; }
.tem-capcane li { margin:0.35rem 0; line-height:1.5; }
.legal-card + .legal-card { margin-top:0.6rem; }
"""

def sablon(titlu, corp, subtitlu="", adancime=1):
    css = "../style.css"
    return f"""<!DOCTYPE html>
<html lang="ro"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="light dark"><meta name="theme-color" content="#09090b">
<link rel="icon" href="../icon-192.png"><link rel="stylesheet" href="{css}"><style>{CSS}</style>
<title>{html.escape(titlu)} — Grile Resurse Umane</title></head>
<body><div class="container"><header><h1>🪖 Grile — Resurse Umane</h1><div class="subtitle">{html.escape(subtitlu)}</div>
<nav class="tem-nav"><a href="../index.html">← Teste</a><a href="index.html">Tematica</a><a href="../legislatie/index.html">Legislația</a></nav></header>
<main>{corp}</main>
<footer>Surse: formele consolidate la zi de pe legislatie.just.ro; citatele sunt verificate automat contra textului.</footer>
</div></body></html>"""

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
    if adresa: art = '<a href="%s" style="color:inherit">%s</a>' % (adresa, art)
    return ('<div class="legal-card"><div class="act">%s</div><span class="articol">%s</span>'
            '<blockquote>„%s”</blockquote><div class="fisier">Sursă: %s</div></div>'
            % (html.escape(t["act"]), art, html.escape(t["citat"]), html.escape(t["fisier"])))

def pagina(d, slug):
    corp = ['<div class="hero"><h2>%d. %s</h2></div>' % (d["nr"], html.escape(d["titlu"]))]
    corp.append('<div class="card"><div class="explic-section-title">Pe scurt</div><div class="tem-rezumat">%s</div>' % html.escape(d["rezumat"]))
    for s in d["sectiuni"]:
        corp.append('<section class="tem-sec"><h3>%s</h3>' % html.escape(s["titlu"]))
        for p in s["paragrafe"]: corp.append("<p>%s</p>" % html.escape(p))
        if s.get("temei"):
            corp.append('<details class="accordion" open><summary><span>Temei legal (%d)</span></summary><div class="accordion-body">' % len(s["temei"]))
            corp += [temei_html(t) for t in s["temei"]]
            corp.append("</div></details>")
        corp.append("</section>")
    if d.get("capcane"):
        corp.append('<div class="explic-section-title">Capcane de examen</div><ul class="tem-capcane">' + "".join("<li>%s</li>" % html.escape(c) for c in d["capcane"]) + "</ul>")
    if d.get("intrebari"):
        corp.append('<p class="fisier" style="color:var(--muted-foreground);font-size:0.8rem">Întrebări din bancă pe această temă: %s</p>' % html.escape(", ".join(d["intrebari"])))
    corp.append("</div>")
    corp.append('<div class="actions"><a class="btn btn-outline" href="index.html">Toate temele</a><a class="btn btn-primary" href="../index.html">Înapoi la teste</a></div>')
    return sablon("%d. %s" % (d["nr"], d["titlu"]), "\n".join(corp), "Tematica — sinteză cu temei legal")

def index_html(gata):
    li = []
    for nr, slug, titlu in TEME:
        if nr in gata: li.append('<li><span class="nr">%d.</span><a href="%02d-%s.html">%s</a></li>' % (nr, nr, slug, html.escape(titlu)))
        else: li.append('<li><span class="nr">%d.</span><span class="soon">%s <em>(în pregătire)</em></span></li>' % (nr, html.escape(titlu)))
    corp = ('<div class="hero"><h2>Tematica examenului</h2><p>Câte o sinteză pe temă, în același stil ca explicațiile din teste: '
            'reguli, termene, excepții și capcane, fiecare cu temeiul legal citat verbatim din forma consolidată la zi.</p></div>'
            '<div class="card"><ul class="tem-list">%s</ul></div>' % "".join(li))
    return sablon("Tematica", corp, "Sinteze pe teme, cu temei legal")

def main():
    os.makedirs(OUT, exist_ok=True)
    gata, erori, fisiere = set(), 0, ["./tematica/index.html"]
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
        open(os.path.join(OUT, nume), "w", encoding="utf-8").write(pagina(d, slug))
        gata.add(nr); fisiere.append("./tematica/" + nume)
        print("tema %d: %d secțiuni, %d/%d citate confirmate → tematica/%s" % (nr, len(d["sectiuni"]), n_ok, n_tot, nume))
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(index_html(gata))
    sw = os.path.join(DIR, "..", "sw.js"); s = open(sw, encoding="utf-8").read()
    bloc = "/* TEMATICA-START */\n" + "".join('  "%s",\n' % f for f in fisiere) + "  /* TEMATICA-END */"
    s2 = re.sub(r"/\* TEMATICA-START \*/.*?/\* TEMATICA-END \*/", bloc, s, flags=re.S)
    if s2 != s: open(sw, "w", encoding="utf-8").write(s2); print("sw.js: %d fișiere de tematică în FISIERE" % len(fisiere))
    print("teme gata: %d/18; erori de citat: %d" % (len(gata), erori))
    sys.exit(1 if erori else 0)

if __name__ == "__main__":
    main()
