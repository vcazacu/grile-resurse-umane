#!/usr/bin/env python3
"""Construiește paginile de citit ale legislației (quiz-app/legislatie/*.html) din
fișierele-sursă ../../legislatie/*.txt, în același stil ca tematica.

Utilizare: python3 legislatie_build.py        (construiește toate cele 9 acte + index)

Fișierele .txt NU se modifică: sunt sursa de adevăr pentru toate uneltele. Parsarea e
deterministă, pe marcajele deja existente în text:
  §SURSA§ …            metadate (portal, consolidare)      ## Capitolul I / Secţiunea / Titlul / §n.
  Articolul N          articol (N poate fi 9^1)            (n)  alineat      x)  literă
  A. / B. / A^1.       grupuri de litere                   – …  liniuțe
  §NOTA§ …             notele portalului (modificări, abrogări, decizii) — strânse pe articol
  §ANEXA§ Anexa nr. X  anexă (numerotare proprie a articolelor)
Implicit paginile arată doar articolele cerute în bibliografie (bibliografie.py); un
comutator descoperă toată legea. Scrie și lista fișierelor în sw.js între marcajele
/* LEGISLATIE-START */ … /* LEGISLATIE-END */.
"""
import html, os, re, sys
from bibliografie import BIB, RESTRICTII, tematica as bib_tematica
from trimiteri import marcheaza

DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(DIR, "..", "legislatie")
LEG = os.path.join(DIR, "..", "..", "legislatie")

# (fișier-sursă, slug, denumire scurtă, anexe redate — None = toate)
ACTE = [
 ("01_Legea_80-1995_statutul_cadrelor_militare.txt", "01-legea-80-1995-statutul-cadrelor-militare",
  "Legea nr. 80/1995 privind statutul cadrelor militare", None),
 ("02_Legea_1-1998_organizarea_SIE.txt", "02-legea-1-1998-organizarea-sie",
  "Legea nr. 1/1998 privind organizarea și funcționarea Serviciului de Informații Externe", None),
 ("03_Legea_53-2003_Codul_muncii.txt", "03-legea-53-2003-codul-muncii",
  "Legea nr. 53/2003 – Codul muncii", None),
 ("04_Legea_223-2015_pensiile_militare.txt", "04-legea-223-2015-pensiile-militare",
  "Legea nr. 223/2015 privind pensiile militare de stat", None),
 ("05_Legea_360-2023_sistemul_public_de_pensii.txt", "05-legea-360-2023-sistemul-public-de-pensii",
  "Legea nr. 360/2023 privind sistemul public de pensii", None),
 ("06_Legea_153-2017_salarizarea_bugetara.txt", "06-legea-153-2017-salarizarea-bugetara",
  "Legea-cadru nr. 153/2017 privind salarizarea personalului plătit din fonduri publice", ["Anexa nr. VI"]),
 ("07_OUG_111-2010_concediul_crestere_copil.txt", "07-oug-111-2010-concediul-crestere-copil",
  "O.U.G. nr. 111/2010 privind concediul și indemnizația lunară pentru creșterea copiilor", None),
 ("08_Norme_HG_52-2011_aplicare_OUG_111-2010.txt", "08-norme-hg-52-2011-aplicare-oug-111-2010",
  "Normele metodologice de aplicare a O.U.G. nr. 111/2010 (H.G. nr. 52/2011)", None),
 ("09_HG_1867-2005_compensatia_chirie.txt", "09-hg-1867-2005-compensatia-chirie",
  "H.G. nr. 1867/2005 privind compensația lunară pentru chirie a cadrelor militare", None),
]

# Etapa 2: trimiteri către alt act din cele 9. Cum numește textul actul (regex la începutul
# frazei de după „din/al/potrivit”) → (fișier-țintă, anexă). Se încearcă în ordine.
SCURT = {
 "01_Legea_80-1995_statutul_cadrelor_militare.txt": "Legea 80/1995",
 "02_Legea_1-1998_organizarea_SIE.txt": "Legea 1/1998",
 "03_Legea_53-2003_Codul_muncii.txt": "Codul muncii",
 "04_Legea_223-2015_pensiile_militare.txt": "Legea 223/2015",
 "05_Legea_360-2023_sistemul_public_de_pensii.txt": "Legea 360/2023",
 "06_Legea_153-2017_salarizarea_bugetara.txt": "Legea 153/2017",
 "07_OUG_111-2010_concediul_crestere_copil.txt": "OUG 111/2010",
 "08_Norme_HG_52-2011_aplicare_OUG_111-2010.txt": "Normele HG 52/2011",
 "09_HG_1867-2005_compensatia_chirie.txt": "HG 1867/2005",
}
ALIASURI = [
 (r"anexa nr\.\s*VI\s+la\s+Legea(?:-cadru)? nr\.\s*153/2017", "06_Legea_153-2017_salarizarea_bugetara.txt", "Anexa nr. VI"),
 (r"Legea nr\.\s*80/1995", "01_Legea_80-1995_statutul_cadrelor_militare.txt", ""),
 (r"Legea nr\.\s*1/1998", "02_Legea_1-1998_organizarea_SIE.txt", ""),
 (r"Legea nr\.\s*53/2003|Codul(?:ui)? muncii", "03_Legea_53-2003_Codul_muncii.txt", ""),
 (r"Legea nr\.\s*223/2015", "04_Legea_223-2015_pensiile_militare.txt", ""),
 (r"Legea nr\.\s*360/2023", "05_Legea_360-2023_sistemul_public_de_pensii.txt", ""),
 (r"Legea(?:-cadru)? nr\.\s*153/2017", "06_Legea_153-2017_salarizarea_bugetara.txt", ""),
 (r"Ordonanța de urgență a Guvernului nr\.\s*111/2010|O\.\s*U\.\s*G\.\s*nr\.\s*111/2010", "07_OUG_111-2010_concediul_crestere_copil.txt", ""),
 (r"Hotărârea Guvernului nr\.\s*52/2011|H\.\s*G\.\s*nr\.\s*52/2011", "08_Norme_HG_52-2011_aplicare_OUG_111-2010.txt", ""),
 (r"Hotărârea Guvernului nr\.\s*1867/2005|H\.\s*G\.\s*nr\.\s*1867/2005", "09_HG_1867-2005_compensatia_chirie.txt", ""),
]
# denumiri prescurtate valabile doar într-un anumit act (Normele spun „ordonanța de urgență” pentru OUG 111/2010)
ALIASURI_LOCALE = {
 "08_Norme_HG_52-2011_aplicare_OUG_111-2010.txt": [(r"ordonan[țt]a de urgen[țt]ă\b(?!\s+a Guvernului nr\.)", "07_OUG_111-2010_concediul_crestere_copil.txt", "")],
 "06_Legea_153-2017_salarizarea_bugetara.txt": [(r"anexa nr\.\s*VI\b", "06_Legea_153-2017_salarizarea_bugetara.txt", "Anexa nr. VI")],
}
INDEX = {}      # (fișier, anexă) → indexeaza(...), umplut de main() înainte de redare

def fabrica_extern(fisier_curent):
    """rez_extern(fraza) pentru trimiteri.marcheaza: actul numit după trimitere → (rezolvator, pagina)."""
    aliasuri = ALIASURI_LOCALE.get(fisier_curent, []) + ALIASURI
    slug_de = {f: s for f, s, _, _ in ACTE}
    def rez_extern(fraza):
        for rx, f, anexa in aliasuri:
            if not re.match(rx, fraza, re.I): continue
            idx = INDEX.get((f, anexa))
            if not idx: return None
            baza, prefix = rezolvator(idx), SCURT[f] + (" " + anexa if anexa else "") + ", "
            def r(fel, art, alin, lit, grup, _b=baza, _p=prefix):
                t = _b(fel, art, alin, lit, grup); return (t[0], _p + t[1]) if t else None
            return r, ("" if f == fisier_curent else slug_de[f] + ".html")
        return None
    return rez_extern

_ART = re.compile(r"^Articolul (\d+(?:\^\d+)?)$")
_ALIN = re.compile(r"^\((\d+(?:\^\d+)?)\)\s*(.*)$")
_LIT = re.compile(r"^([a-zșț](?:\^\d+)?)\)\s*(.*)$")
_GRUP = re.compile(r"^([A-ZȘȚ](?:\^\d+)?)\.\s+(.*)$")
_LINIUTA = re.compile(r"^[-–]\s+(.*)$")
_TITLU_SECT = re.compile(r"^## (Titlul|Capitolul|Sec[țţ]iunea|§\d+\.)\s*(.*)$")
_NIVEL = {"Titlul": 1, "Capitolul": 2, "Secțiunea": 3, "Secţiunea": 3}
_TABEL = re.compile(r"^Tabelul nr\.\s*\d+")
_ABROGAT = re.compile(r"^\s*(\(\d+\)\s*)?Abrogat")

def _structurala(l):
    return bool(_ART.match(l) or _ALIN.match(l) or _LIT.match(l) or _GRUP.match(l)
                or l.startswith("## ") or l.startswith("§"))

def parseaza(cale, anexe_redate=None):
    """Întoarce {sursa, titlu:[…], meta:{}, corp:[blocuri], anexe:[{nume, titlu, blocuri}]}.
    Bloc = {"tip":"sect", nivel, eticheta, titlu} | {"tip":"art", nr, titlu, continut:[(tip, text)], note:[…]}
         | {"tip":"text", text}."""
    linii = [l.rstrip() for l in open(cale, encoding="utf-8").read().split("\n")]
    linii = [l[:-2] if l.endswith(" +") else l for l in linii]       # artefact al portalului
    doc = {"sursa": "", "titlu": [], "meta": {}, "corp": [], "anexe": []}
    blocuri, art, in_preambul, anexa_activa = doc["corp"], None, True, True
    i = 0
    while i < len(linii):
        l = linii[i]; i += 1
        if not l: continue
        if l.startswith("§SURSA§"):
            doc["sursa"] = l[len("§SURSA§"):].strip(); continue
        if l.startswith("§ANEXA§"):
            nume = l[len("§ANEXA§"):].strip()
            anexa_activa = anexe_redate is None or nume in anexe_redate
            art, in_preambul = None, False
            if anexa_activa:
                titlu = ""
                if i < len(linii) and linii[i] and not _structurala(linii[i]):
                    titlu = linii[i]; i += 1
                doc["anexe"].append({"nume": nume, "titlu": titlu, "blocuri": []})
                blocuri = doc["anexe"][-1]["blocuri"]
            continue
        if not anexa_activa: continue
        if l.startswith("§NOTA§"):
            nota = l[len("§NOTA§"):].strip()
            if art: art["note"].append(nota)
            elif blocuri: blocuri.append({"tip": "nota", "text": nota})
            continue
        if l.startswith("## "):
            if l in ("## EMITENT", "## Publicat în"):
                if i < len(linii): doc["meta"][l[3:]] = linii[i]; i += 1
                continue
            m = _TITLU_SECT.match(l)
            fel = m.group(1) if m else l[3:]
            nivel = _NIVEL.get(fel, 4 if fel.startswith("§") else 2)
            titlu = ""
            if i < len(linii) and linii[i] and not _structurala(linii[i]):
                titlu = linii[i]; i += 1
            blocuri.append({"tip": "sect", "nivel": nivel, "eticheta": l[3:], "titlu": titlu})
            art, in_preambul = None, False
            continue
        m = _ART.match(l)
        if m:
            art = {"tip": "art", "nr": m.group(1), "titlu": "", "continut": [], "note": []}
            blocuri.append(art); in_preambul = False
            # titlu marginal: rând scurt, fără punctuație finală, care nu e text normativ
            if i < len(linii) and linii[i] and not _structurala(linii[i]) \
               and len(linii[i]) <= 90 and not linii[i].endswith((".", ";", ":", ",")):
                art["titlu"] = linii[i]; i += 1
            continue
        if in_preambul:
            doc["titlu"].append(l); continue
        tinta = art["continut"] if art else None
        if tinta is None:
            blocuri.append({"tip": "text", "text": l}); continue
        if _TABEL.match(l):
            rows = [l]
            while i < len(linii) and linii[i] and not _structurala(linii[i]) and not _TABEL.match(linii[i]):
                rows.append(linii[i]); i += 1
            tinta.append(("tabel", rows)); continue
        m = _ALIN.match(l)
        if m: tinta.append(("alin", (m.group(1), m.group(2)))); continue
        m = _GRUP.match(l)
        if m: tinta.append(("grup", l)); continue
        m = _LIT.match(l)
        if m: tinta.append(("lit", (m.group(1), m.group(2)))); continue
        m = _LINIUTA.match(l)
        if m: tinta.append(("liniuta", m.group(1))); continue
        tinta.append(("text", l))
    return doc

# ---------------------------------------------------------------- HTML

CSS = """
.tem-nav { display:flex; gap:0.75rem; flex-wrap:wrap; font-size:0.85rem; margin:0.25rem 0 0.75rem; }
.tem-nav a { color: var(--info); text-decoration:none; } .tem-nav a:hover { text-decoration:underline; }
.tem-list { list-style:none; padding:0; margin:0; display:grid; gap:0.5rem; }
.tem-list li { border:1px solid var(--border); border-radius:0.6rem; padding:0.7rem 0.9rem; display:flex; gap:0.6rem; align-items:baseline; }
.tem-list .nr { font-weight:700; color: var(--muted-foreground); min-width:1.6rem; }
.tem-list a { color: var(--foreground); text-decoration:none; font-weight:600; } .tem-list a:hover { text-decoration:underline; }
.tem-list small { display:block; font-weight:400; color: var(--muted-foreground); font-size:0.8rem; margin-top:0.15rem; }
.leg-meta { color: var(--muted-foreground); font-size:0.85rem; margin:0.3rem 0 0; }
.leg-preambul p { color: var(--muted-foreground); font-size:0.9rem; margin:0.2rem 0; }
.leg-bar { position:sticky; top:0; z-index:5; background: var(--background); border-bottom:1px solid var(--border);
  padding:0.5rem 0; margin:0 0 0.5rem; display:flex; gap:0.9rem; align-items:center; flex-wrap:wrap; font-size:0.9rem; }
.leg-bar label { display:flex; gap:0.4rem; align-items:center; cursor:pointer; }
.leg-bar form { display:flex; gap:0.3rem; align-items:center; margin-left:auto; }
.leg-bar input[type=text] { width:4.5rem; padding:0.25rem 0.4rem; border:1px solid var(--border); border-radius:0.4rem; background: var(--card); color: var(--foreground); }
.leg-bar button { padding:0.25rem 0.6rem; border:1px solid var(--border); border-radius:0.4rem; background: var(--card); color: var(--foreground); cursor:pointer; }
.leg-cuprins ul { list-style:none; padding:0; margin:0; } .leg-cuprins li { margin:0.2rem 0; line-height:1.4; font-size:0.9rem; }
.leg-cuprins li.n1 { font-weight:700; margin-top:0.5rem; } .leg-cuprins li.n3, .leg-cuprins li.n4 { padding-left:1.2rem; font-size:0.85rem; }
.leg-cuprins a { color: var(--foreground); text-decoration:none; } .leg-cuprins a:hover { text-decoration:underline; }
.leg-cuprins .cnt { color: var(--muted-foreground); font-size:0.8rem; margin-left:0.3rem; }
.leg-sect h3 { margin:1.4rem 0 0.4rem; font-size:1.05rem; letter-spacing:-0.01em; }
.leg-sect h3 small { display:block; font-weight:500; color: var(--muted-foreground); font-size:0.82rem; }
.leg-sect.n1 h3 { font-size:1.15rem; border-bottom:2px solid var(--border); padding-bottom:0.3rem; }
.leg-sect.n3 h3, .leg-sect.n4 h3 { font-size:0.95rem; margin-top:1rem; }
.leg-art { padding:0.7rem 0; border-top:1px solid var(--border); scroll-margin-top:3.2rem; }
.leg-art h4 { margin:0 0 0.3rem; font-size:1rem; display:flex; gap:0.5rem; align-items:center; flex-wrap:wrap; }
.leg-art h4 .restr { font-weight:500; color: var(--muted-foreground); font-size:0.8rem; }
.leg-titlu { font-weight:600; color: var(--muted-foreground); font-size:0.9rem; margin:0 0 0.35rem; }
.leg-art p { margin:0.3rem 0; line-height:1.55; }
.leg-art p.alin .nr { font-weight:700; color: var(--muted-foreground); margin-right:0.35rem; }
.leg-art p.lit { padding-left:1.5rem; } .leg-art p.lit .nr { font-weight:600; margin-right:0.3rem; }
.leg-art p.liniuta { padding-left:2.6rem; } .leg-art p.liniuta::before { content:"– "; color: var(--muted-foreground); }
.leg-art .grup { padding-left:0.7rem; font-weight:600; margin:0.4rem 0 0.1rem; }
.leg-art.abrogat p, .leg-art.abrogat .leg-titlu { color: var(--muted-foreground); }
.leg-tabel { font-family: ui-monospace, Menlo, Consolas, monospace; font-size:0.78rem; background: var(--muted); border-radius:0.5rem;
  padding:0.5rem 0.7rem; margin:0.4rem 0; line-height:1.5; white-space:pre-wrap; overflow-wrap:anywhere; }
.leg-tabel .t { font-weight:700; display:block; margin-bottom:0.2rem; }
.leg-note { margin-top:0.4rem; } .leg-note summary { font-size:0.8rem; color: var(--muted-foreground); cursor:pointer; list-style:none; }
.leg-note summary::before { content:"▸ "; } .leg-note[open] summary::before { content:"▾ "; }
.leg-note p { font-size:0.82rem; color: var(--muted-foreground); line-height:1.45; margin:0.25rem 0 0.25rem 0.9rem; }
.leg-nota-libera { font-size:0.82rem; color: var(--muted-foreground); margin:0.3rem 0; }
.leg-anexa > h3 { margin:1.6rem 0 0.4rem; font-size:1.15rem; border-bottom:2px solid var(--border); padding-bottom:0.3rem; }
.badge.bib { background: var(--success-bg); color: var(--success); border-color: var(--success-border); }
.badge.abrogat { background: var(--muted); color: var(--muted-foreground); border-color: var(--border); }
.doar-bib .leg-art:not(.bib), .doar-bib .leg-sect:not(.are-bib), .doar-bib .leg-anexa:not(.are-bib),
.doar-bib .leg-cuprins li:not(.are-bib), .doar-bib .leg-text, .doar-bib .leg-nota-libera { display:none; }
.leg-omis { color: var(--muted-foreground); font-size:0.85rem; font-style:italic; margin:1rem 0; }
a.trm { color: var(--info); text-decoration:none; border-bottom:1px dotted var(--info-border); cursor:pointer; }
a.trm:hover, a.trm.deschis { background: var(--info-bg); }
.trm-box { border-left:3px solid var(--info-border); background: var(--info-bg); border-radius:0 0.5rem 0.5rem 0;
  padding:0.45rem 0.7rem 0.5rem; margin:0.35rem 0 0.55rem; font-size:0.9rem; }
.trm-box .trm-h { display:flex; gap:0.6rem; align-items:center; font-size:0.8rem; color: var(--muted-foreground); margin:0.35rem 0 0.15rem; }
.trm-box .trm-h:first-child { margin-top:0; }
.trm-box .trm-h b { color: var(--info); font-weight:700; }
.trm-box .trm-h a { color: var(--info); margin-left:auto; text-decoration:none; white-space:nowrap; }
.trm-box .trm-h button { background:none; border:0; color: var(--muted-foreground); font-size:1.1rem; line-height:1; cursor:pointer; padding:0 0.2rem; }
.trm-box p { margin:0.2rem 0; } .trm-box p.lit { padding-left:1.2rem; } .trm-box .grup { padding-left:0.4rem; }
.trm-box .trm-box { background: var(--card); }
.leg-art p[id], .leg-art .grup[id] { scroll-margin-top:3.2rem; }
"""

JS = """
(function(){
  var K='leg-toata', cb=document.getElementById('leg-tot'); if(!cb) return;
  function aplica(){ document.body.classList.toggle('doar-bib', !cb.checked);
    try{ localStorage.setItem(K, cb.checked?'1':'0'); }catch(e){} }
  try{ cb.checked = localStorage.getItem(K)==='1'; }catch(e){}
  cb.addEventListener('change', aplica); aplica();
  function tinta(){ var h=location.hash; if(!h) return; var el=document.getElementById(h.slice(1)); if(!el) return;
    var a=el.closest('.leg-art'); if(!cb.checked && ((a && !a.classList.contains('bib')) || el.closest('.leg-sect:not(.are-bib), .leg-anexa:not(.are-bib)'))){ cb.checked=true; aplica(); }
    el.scrollIntoView(); }
  window.addEventListener('hashchange', tinta); tinta();
  var f=document.getElementById('leg-sari'); if(f) f.addEventListener('submit', function(e){ e.preventDefault();
    var v=f.querySelector('input').value.trim().replace(/\\s+/g,'').replace('^','-'); if(!v) return;
    var id='art-'+v; if(!document.getElementById(id)){ f.querySelector('input').setCustomValidity('Nu există art. '+v); f.reportValidity();
      setTimeout(function(){ f.querySelector('input').setCustomValidity(''); },1500); return; }
    location.hash='#'+id; });

  /* Trimiteri: la apăsare, sub paragraf se deschide un chenar cu textul țintei, copiat din pagină. */
  function urmatoarele(el, oprire, accepta){ var out=[el], s=el.nextElementSibling;
    while(s && !oprire(s)){ if(accepta(s)) out.push(s); s=s.nextElementSibling; } return out; }
  function extrage(el){
    if(el.classList.contains('leg-art')) return Array.prototype.filter.call(el.children, function(c){ return c.tagName!=='H4' && !c.classList.contains('leg-note'); });
    if(el.classList.contains('alin')) return urmatoarele(el, function(s){ return s.classList.contains('alin') || s.tagName==='DETAILS'; }, function(s){ return s.tagName==='P' || s.classList.contains('grup'); });
    if(el.classList.contains('grup')) return urmatoarele(el, function(s){ return s.classList.contains('alin') || s.classList.contains('grup') || s.tagName==='DETAILS'; }, function(s){ return s.tagName==='P'; });
    return urmatoarele(el, function(s){ return !s.classList.contains('liniuta') && !s.classList.contains('trm-box'); }, function(s){ return s.classList.contains('liniuta'); });
  }
  function curata(n, pag){ var c=n.cloneNode(true); if(c.removeAttribute) c.removeAttribute('id');
    c.querySelectorAll('[id]').forEach(function(x){ x.removeAttribute('id'); });
    c.querySelectorAll('.trm-box').forEach(function(x){ x.remove(); });
    if(pag) c.querySelectorAll('a.trm').forEach(function(x){   /* textul vine din altă pagină: trimiterile lui interne rămân ale acelei pagini */
      x.dataset.t=x.dataset.t.split(' ').map(function(t){ return t.indexOf('#')<0 ? pag+'#'+t : t; }).join(' ');
      if(x.getAttribute('href').charAt(0)==='#') x.setAttribute('href', pag+x.getAttribute('href')); });
    return c; }
  /* Ținta poate fi în altă pagină („07-….html#art-8”): pagina se ia cu fetch (e în cache-ul offline) și se parsează o singură dată. */
  var docs={};
  function iaDoc(pag, cb){ if(!pag) return cb(document); if(docs[pag]) return cb(docs[pag]);
    fetch(pag).then(function(r){ return r.text(); }).then(function(t){ docs[pag]=new DOMParser().parseFromString(t,'text/html'); cb(docs[pag]); })
      .catch(function(){ cb(null); }); }
  document.addEventListener('click', function(ev){
    var a=ev.target.closest('a.trm'); if(!a) return; ev.preventDefault();
    var bloc=a.closest('p, .grup, .leg-titlu'); if(!bloc) return;
    var existent=bloc.nextElementSibling;
    if(existent && existent.classList.contains('trm-box') && existent.dataset.de===a.dataset.t){ existent.remove(); a.classList.remove('deschis'); return; }
    var box=document.createElement('div'); box.className='trm-box'; box.dataset.de=a.dataset.t;
    var ids=a.dataset.t.split(' '), et=a.dataset.e.split('|');
    ids.forEach(function(ref, i){ var p=ref.split('#'), pag=p.length>1?p[0]:'', id=p[p.length-1];
      var cont=document.createElement('div'); box.appendChild(cont);
      var h=document.createElement('div'); h.className='trm-h';
      h.innerHTML='<b></b><a href="'+pag+'#'+id+'">mergi la text ↗</a>'+(i===0?'<button type="button" aria-label="Închide">×</button>':'');
      h.querySelector('b').textContent=et[i]||id; cont.appendChild(h);
      iaDoc(pag, function(doc){ var el=doc && doc.getElementById(id);
        if(!el){ var e=document.createElement('p'); e.textContent=doc?'Textul nu a fost găsit.':'Pagina actului nu a putut fi încărcată.'; cont.appendChild(e); return; }
        extrage(el).forEach(function(n){ cont.appendChild(curata(n, pag)); }); }); });
    box.addEventListener('click', function(e){ if(e.target.tagName==='BUTTON'){ box.remove(); a.classList.remove('deschis'); } });
    bloc.insertAdjacentElement('afterend', box); a.classList.add('deschis');
  });
})();
"""

def sablon(titlu, corp, subtitlu=""):
    return f"""<!DOCTYPE html>
<html lang="ro"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="light dark"><meta name="theme-color" content="#09090b">
<link rel="icon" href="../icon-192.png"><link rel="stylesheet" href="../style.css"><style>{CSS}</style>
<title>{html.escape(titlu)} — Grile Resurse Umane</title></head>
<body><div class="container"><header><h1>🪖 Grile — Resurse Umane</h1><div class="subtitle">{html.escape(subtitlu)}</div>
<nav class="tem-nav"><a href="../index.html">← Teste</a><a href="../tematica/index.html">Tematica</a><a href="index.html">Legislația</a></nav></header>
<main>{corp}</main>
<footer>Textele sunt formele consolidate la zi de pe legislatie.just.ro, redate fără modificări; notele portalului sunt strânse sub fiecare articol.</footer>
<script>{JS}</script></div></body></html>"""

def ancora(nr, anexa=""):
    a = "art-" + nr.replace("^", "-")
    return ("anexa-%s-" % re.sub(r"[^A-Za-z0-9]+", "-", anexa).strip("-").lower() + a) if anexa else a

def _ph(cls, inner, nr=None, idd=None):
    """Paragraf cu conținut deja redat în HTML (textul trece prin txt()/marcheaza)."""
    n = '<span class="nr">%s</span>' % html.escape(nr) if nr else ""
    return '<p class="%s"%s>%s%s</p>' % (cls, ' id="%s"' % idd if idd else "", n, inner)

def indexeaza(blocuri, anexa):
    """Id-urile alineatelor, grupurilor și literelor fiecărui articol din zonă, pentru ancore și
    pentru rezolvarea trimiterilor. d["ids"][k] = id-ul elementului k din continut (sau None)."""
    idx = {}
    for b in blocuri:
        if b["tip"] != "art": continue
        e = ancora(b["nr"], anexa)
        d = {"id": e, "alin": {}, "lit": {}, "grup": {}, "ids": []}
        alin = grup = None
        for tip, v in b["continut"]:
            idd = None
            if tip == "alin":
                alin, grup = v[0], None
                idd = "%s-al-%s" % (e, alin.replace("^", "-"))
                d["alin"][alin] = {"id": idd, "lit": {}, "grup": {}}
            elif tip == "grup":
                grup = _GRUP.match(v).group(1)
                tinta = d["alin"][alin] if alin else d
                idd = "%s-g%s" % (tinta["id"], grup.replace("^", "-"))
                tinta["grup"].setdefault(grup, {"id": idd, "lit": {}})
            elif tip == "lit":
                tinta = d["alin"][alin] if alin else d
                baza = tinta["grup"][grup] if grup else tinta
                idd = "%s-lit-%s" % (baza["id"], v[0].replace("^", "-"))
                if idd in d["ids"]: idd += "-%d" % (d["ids"].count(idd) + 1)   # literă repetată fără grup
                if grup: baza["lit"][v[0]] = idd
                tinta["lit"].setdefault(v[0], []).append(idd)
            d["ids"].append(idd)
        idx[b["nr"]] = d
    return idx

def rezolvator(idx):
    """rez(fel, art, alin, lit, grup) → (id, etichetă) sau None, pentru trimiteri.marcheaza."""
    def rez(fel, art, alin, lit, grup):
        d = idx.get(art)
        if not d: return None
        et = "art. %s" % art
        if fel == "art": return d["id"], et
        if alin is not None:
            al = d["alin"].get(alin)
            if not al: return None
            et += " alin. (%s)" % alin
            if fel == "alin": return al["id"], et
            tinta = al
        else:
            if fel == "alin": return None
            tinta = d
        if grup:
            g = tinta["grup"].get(grup)
            lid = g["lit"].get(lit) if g else None
            return (lid, "%s %s. lit. %s)" % (et, grup, lit)) if lid else None
        ids = tinta["lit"].get(lit, [])
        return (ids[0], "%s lit. %s)" % (et, lit)) if len(ids) == 1 else None    # ambiguu (mai multe grupuri) → nelegat
    return rez

def art_html(art, anexa, cerute, restrictii, idx=None, stat=None, rez_extern=None):
    nr, e = art["nr"], ancora(art["nr"], anexa)
    in_bib = nr in cerute
    d = (idx or {}).get(nr, {"ids": [None] * len(art["continut"])})
    rez = rezolvator(idx) if idx else None
    alin = grup = None
    def txt(s):
        return marcheaza(s, (nr, alin, grup), rez, stat, rez_extern) if rez else html.escape(s)
    prim = art["continut"][0] if art["continut"] else None
    prim_text = (prim[1] if prim[0] == "text" else (prim[1][1] if prim[0] in ("alin", "lit") else "")) if prim else ""
    abrogat = not art["continut"] or bool(_ABROGAT.match(prim_text)) or (prim and prim[0] == "alin" and prim[1][0] == "1" and _ABROGAT.match(prim[1][1]) and len(art["continut"]) == 1)
    cls = "leg-art" + (" bib" if in_bib else "") + (" abrogat" if abrogat else "")
    h = ['<article class="%s" id="%s"><h4>Art. %s' % (cls, e, html.escape(nr))]
    if in_bib: h.append('<span class="badge bib">bibliografie</span>')
    if abrogat: h.append('<span class="badge abrogat">abrogat</span>')
    r = restrictii.get(nr)
    if r and in_bib: h.append('<span class="restr">în bibliografie %s</span>' % html.escape(r))
    h.append("</h4>")
    if art["titlu"]: h.append('<div class="leg-titlu">%s</div>' % html.escape(art["titlu"]))
    for k, (tip, v) in enumerate(art["continut"]):
        idd = d["ids"][k] if k < len(d["ids"]) else None
        if tip == "alin":
            alin, grup = v[0], None
            h.append(_ph("alin", txt(v[1]), "(%s)" % v[0], idd))
        elif tip == "lit": h.append(_ph("lit", txt(v[1]), "%s)" % v[0], idd))
        elif tip == "grup":
            grup = _GRUP.match(v).group(1)
            h.append('<div class="grup"%s>%s</div>' % (' id="%s"' % idd if idd else "", txt(v)))
        elif tip == "liniuta": h.append(_ph("liniuta", txt(v)))
        elif tip == "tabel": h.append('<div class="leg-tabel"><span class="t">%s</span>%s</div>' % (html.escape(v[0]), html.escape(" ".join(v[1:]))))
        else: h.append(_ph("text", txt(v)))
    if art["note"]:
        h.append('<details class="leg-note"><summary>Note (%d)</summary>%s</details>'
                 % (len(art["note"]), "".join("<p>%s</p>" % html.escape(n) for n in art["note"])))
    h.append("</article>")
    return "".join(h), in_bib

def blocuri_html(blocuri, anexa, cerute, restrictii, stat=None, rez_extern=None):
    """Redă o listă de blocuri; secțiunile se închid la următoarea secțiune de nivel ≤."""
    idx = indexeaza(blocuri, anexa)
    # 1) ce secțiune conține articole din bibliografie (până la următoarea de nivel ≤)
    are_bib = []
    for i, b in enumerate(blocuri):
        if b["tip"] != "sect": continue
        ok = False
        for c in blocuri[i + 1:]:
            if c["tip"] == "sect" and c["nivel"] <= b["nivel"]: break
            if c["tip"] == "art" and c["nr"] in cerute: ok = True; break
        are_bib.append(ok)
    # 2) HTML
    out, cuprins, deschise, n_bib, n_art, k = [], [], [], 0, 0, 0
    for b in blocuri:
        if b["tip"] == "sect":
            ok = are_bib[k]; k += 1
            while deschise and deschise[-1] >= b["nivel"]:
                out.append("</section>"); deschise.pop()
            sid = "s-%d" % k + ("-" + re.sub(r"[^A-Za-z0-9]+", "-", anexa).strip("-").lower() if anexa else "")
            out.append('<section class="leg-sect n%d%s" id="%s"><h3>%s%s</h3>'
                       % (b["nivel"], " are-bib" if ok else "", sid, html.escape(b["eticheta"]),
                          "<small>%s</small>" % html.escape(b["titlu"]) if b["titlu"] else ""))
            deschise.append(b["nivel"])
            cuprins.append((b["nivel"], sid, b["eticheta"], b["titlu"], ok))
        elif b["tip"] == "art":
            h, in_bib = art_html(b, anexa, cerute, restrictii, idx, stat, rez_extern)
            out.append(h); n_art += 1; n_bib += in_bib
        elif b["tip"] == "nota":
            out.append('<p class="leg-nota-libera">%s</p>' % html.escape(b["text"]))
        else:
            out.append('<p class="leg-text">%s</p>' % html.escape(b["text"]))
    out.extend("</section>" for _ in deschise)
    return "".join(out), cuprins, n_art, n_bib

def cuprins_html(intrari):
    li = []
    for nivel, sid, eticheta, titlu, ok in intrari:
        li.append('<li class="n%d%s"><a href="#%s">%s%s</a></li>'
                  % (nivel, " are-bib" if ok else "", sid, html.escape(eticheta), (" — " + html.escape(titlu)) if titlu else ""))
    return '<details class="accordion leg-cuprins" open><summary><span>Cuprins</span></summary><div class="accordion-body"><ul>%s</ul></div></details>' % "".join(li)

def pagina(fisier, slug, denumire, anexe_redate, bib, doc=None):
    doc = doc or parseaza(os.path.join(LEG, fisier), anexe_redate)
    cerute_corp = set(bib.get(fisier, ("", "", [], [], [], {}))[2])
    restr_corp = {a: r for (f, a), r in RESTRICTII.items() if f == fisier}
    stat, rez_extern = {}, fabrica_extern(fisier)
    corp_html, cuprins, n_art, n_bib = blocuri_html(doc["corp"], "", cerute_corp, restr_corp, stat, rez_extern)
    anexe_html = []
    for ax in doc["anexe"]:
        cheie = fisier + "#" + ax["nume"]
        cerute = set(bib[cheie][2]) if cheie in bib else set()
        restr = {a: r for (f, a), r in RESTRICTII.items() if f == cheie}
        h, cup, na, nb = blocuri_html(ax["blocuri"], ax["nume"], cerute, restr, stat, rez_extern)
        n_art += na; n_bib += nb
        aid = "anexa-" + re.sub(r"[^A-Za-z0-9]+", "-", ax["nume"]).strip("-").lower()
        anexe_html.append('<section class="leg-anexa%s" id="%s"><h3>%s%s</h3>%s</section>'
                          % (" are-bib" if nb else "", aid, html.escape(ax["nume"]),
                             "<small style='display:block;font-weight:500;color:var(--muted-foreground);font-size:0.82rem'>%s</small>" % html.escape(ax["titlu"]) if ax["titlu"] else "", h))
        cuprins.append((1, aid, ax["nume"], ax["titlu"], bool(nb)))
        cuprins.extend((min(nivel + 1, 4), sid, et, ti, ok) for nivel, sid, et, ti, ok in cup)
    consolidare = re.search(r"consolidarea din [\d.]+", doc["sursa"])
    url = doc["sursa"].split("|")[0].strip()
    meta = " · ".join(x for x in [consolidare.group(0) if consolidare else "", "%d articole, %d cerute în bibliografie" % (n_art, n_bib)] if x)
    corp = ['<div class="hero"><h2>%s</h2><p class="leg-meta">%s</p>%s</div>'
            % (html.escape(denumire), html.escape(meta),
               '<p class="leg-meta">Sursă: <a href="https://%s" style="color:var(--info)">%s</a></p>' % (html.escape(url), html.escape(url)) if url else "")]
    corp.append('<div class="leg-bar"><label><input type="checkbox" id="leg-tot"> Arată toată legea</label>'
                '<form id="leg-sari"><span>Art.</span><input type="text" inputmode="numeric" placeholder="nr." aria-label="numărul articolului"><button type="submit">Sari</button></form></div>')
    if doc["titlu"] or doc["meta"]:
        corp.append('<div class="card leg-preambul">%s%s</div>'
                    % ("".join("<p>%s</p>" % html.escape(t) for t in doc["titlu"]),
                       "".join('<p><strong>%s:</strong> %s</p>' % (html.escape(k), html.escape(v)) for k, v in doc["meta"].items())))
    corp.append(cuprins_html(cuprins))
    corp.append(corp_html)
    corp.extend(anexe_html)
    if anexe_redate is not None:
        corp.append('<p class="leg-omis">Celelalte anexe ale actului (grile de salarizare) nu sunt în bibliografie și nu sunt redate aici.</p>')
    corp.append('<div class="actions"><a class="btn btn-outline" href="index.html">Toate actele</a><a class="btn btn-primary" href="../index.html">Înapoi la teste</a></div>')
    return sablon(denumire, "".join(corp), "Legislația din bibliografie — text integral, consolidat"), doc, n_art, n_bib, stat

def index_html(rows):
    li = "".join('<li><span class="nr">%d.</span><a href="%s.html">%s<small>%s</small></a></li>'
                 % (i + 1, slug, html.escape(den), html.escape(sub)) for i, (slug, den, sub) in enumerate(rows))
    corp = ('<div class="hero"><h2>Legislația din bibliografie</h2><p>Cele nouă acte normative, în text integral consolidat. '
            'Implicit se văd doar articolele cerute în bibliografie (marcate <span class="badge bib">bibliografie</span>); '
            'comutatorul „Arată toată legea” descoperă și restul.</p></div>'
            '<div class="card"><ul class="tem-list">%s</ul></div>' % li)
    return sablon("Legislația din bibliografie", corp, "Legislația din bibliografie — text integral, consolidat")

def main():
    os.makedirs(OUT, exist_ok=True)
    bib = bib_tematica()
    rows, fisiere, erori = [], ["./legislatie/index.html"], 0
    # toate actele se parsează întâi, ca trimiterile către alt act să aibă indexul țintei
    docs = {fisier: parseaza(os.path.join(LEG, fisier), anexe_redate) for fisier, _, _, anexe_redate in ACTE}
    for fisier, doc in docs.items():
        INDEX[(fisier, "")] = indexeaza(doc["corp"], "")
        for ax in doc["anexe"]: INDEX[(fisier, ax["nume"])] = indexeaza(ax["blocuri"], ax["nume"])
    for fisier, slug, denumire, anexe_redate in ACTE:
        pag, doc, n_art, n_bib, stat = pagina(fisier, slug, denumire, anexe_redate, bib, docs[fisier])
        # asertări: fiecare articol cerut are ancoră; numărul de articole din corp = cel văzut de bibliografie.py
        for cheie, (f, anexa, cerute, _l, _a, arts) in bib.items():
            if f != fisier: continue
            for a in cerute:
                if 'id="%s"' % ancora(a, anexa) not in pag:
                    erori += 1; print("  EROARE %s: art. %s%s cerut în bibliografie, fără ancoră în pagină" % (fisier, a, " " + anexa if anexa else ""))
            if not anexa:
                n_corp = sum(1 for b in doc["corp"] if b["tip"] == "art")
                if n_corp != len(arts):
                    erori += 1; print("  EROARE %s: %d articole redate, %d în articole_din_text()" % (fisier, n_corp, len(arts)))
        nume = slug + ".html"
        open(os.path.join(OUT, nume), "w", encoding="utf-8").write(pag)
        fisiere.append("./legislatie/" + nume)
        consolidare = re.search(r"consolidarea din [\d.]+", doc["sursa"])
        rows.append((slug, denumire, "%d articole cerute din %d · %s" % (n_bib, n_art, consolidare.group(0) if consolidare else "")))
        print("%-46s %4d art., %3d în bibl., trimiteri: %4d legate (%3d către alt act), %3d nelegate, %3d alt act necunoscut, %5d KB"
              % (fisier[:46], n_art, n_bib, stat.get("legate", 0), stat.get("extern_legate", 0), stat.get("nelegate", 0), stat.get("extern", 0), len(pag) // 1024))
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(index_html(rows))
    sw = os.path.join(DIR, "..", "sw.js"); s = open(sw, encoding="utf-8").read()
    bloc = "/* LEGISLATIE-START */\n" + "".join('  "%s",\n' % f for f in fisiere) + "  /* LEGISLATIE-END */"
    s2 = re.sub(r"/\* LEGISLATIE-START \*/.*?/\* LEGISLATIE-END \*/", bloc, s, flags=re.S)
    if s2 != s: open(sw, "w", encoding="utf-8").write(s2); print("sw.js: %d fișiere de legislație în FISIERE" % len(fisiere))
    print("erori: %d" % erori)
    sys.exit(1 if erori else 0)

if __name__ == "__main__":
    main()
