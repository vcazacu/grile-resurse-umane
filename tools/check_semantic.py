#!/usr/bin/env python3
"""Stratul 4 (semantic) ca poartă automată: regulile de calitate din SPEC §4
devin judecăți tipizate TypeSafe peste textul legii, nu un agent care „verifică”.

Pentru fiecare întrebare se fac DOUĂ cereri, fiecare cu întrebările ei în paralel:

  A. fără cheie (state-ul NU conține `corecte` și NU conține explicația) —
     câte un Choice pe fiecare variantă: textul articolului o susține, o contrazice
     sau nu spune nimic, ca răspuns la enunț. Separarea e esențială: explicația
     argumentează de ce fiecare distractor e greșit, deci ar suprima exact
     semnalul „distractor apărabil” (SPEC §4.1) pe care îl căutăm.
  B. cu cheie — judecăți despre explicație și despre formă: distractor cvasi-sinonim,
     afirmații absolute nesusținute, alineat abrogat, enunț autonom, nivelul întrebării.

Judecățile brute se salvează în verificari/<lot>-ts.json. Politica (pragurile care
transformă probabilitățile în verdict) stă separat, în `verdict()`, și se poate
re-aplica fără să reruleze inferența:

    python3 check_semantic.py nou/L80-1.json          # rulează și salvează judecățile
    python3 check_semantic.py --din verificari/L80-1-ts.json   # doar re-aplică politica
    python3 check_semantic.py --prag-sustine 0.7 nou/A6-2.json
    python3 check_semantic.py --doar-pozitionale ../intrebari.js   # offline, fără cheie API

Cod de ieșire 1 dacă există întrebări REVIZUIT (0 pentru OK/INCERT).
Cere TYPESAFE_API_KEY în mediu.
"""
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import bibliografie
from normalizare import (DIR_LEGISLATIE, DIR_TOOLS, cheie_bib, eticheta_articol,
                         incarca_intrebari)

DIR_VERIFICARI = DIR_TOOLS / "verificari"
LITERE = "ABCDEFGH"
MAX_VECINE = 2500      # caractere per articol vecin (secțiunea proprie nu se taie)
MAX_INVOCAT = 9000     # articolele numite în explicație sunt DOVADA: aproape netrunchiate
                       # (la 2500 se tăia art. 20^1 alin. (4) → alarmă falsă cu p=0.95)
FIRE = 6               # cereri în paralel

# Abrogări asumate: SPEC §1 permite o întrebare-capcană „care articol este abrogat”
# exact pentru acestea. Semnalul `abrogat` e corect pe ele, dar întrebarea e intenționată.
_NOTA_ABROGARE = re.compile(r"\babrog", re.I)   # „a fost abrogat”, „se abrogă prevederile...”

ABROGARE_ASUMATA = {
    ("01_Legea_80-1995_statutul_cadrelor_militare.txt", "94^1"),
    ("09_HG_1867-2005_compensatia_chirie.txt", "3^1"),
}

# ---------- Politica: praguri (se pot schimba din linia de comandă) ----------
PRAGURI = {
    "sustine": 0.60,     # p(sustine) peste care considerăm varianta „susținută de text”
    "aparabil": 0.45,    # p(sustine) pe un distractor peste care e apărabil → REVIZUIT
    "noul": 0.70,        # praguri pentru judecățile yes/no
    "confidence": 0.55,  # sub această încredere pe o variantă → INCERT, nu OK
    "contrazice": 0.50,  # p(contrazice) pe o frază din explicație → REVIZUIT
    "neverificabil": 0.60,  # p(nu_spune) pe o frază din explicație → INCERT
}


# ---------- Verificare deterministă (fără apel de rețea) ----------
# asambleaza.py amestecă variantele, deci orice trimitere la poziția unei variante
# din explicație devine falsă în aplicație. Clasă întreagă de defecte, gratuit.
_ORD = r"(?:prima|a\s+doua|a\s+treia|a\s+patra|ultima|primele\s+\w+|ultimele\s+\w+)"
_POZITIE = re.compile(
    r"\bvariant(?:a|ele)\s+" + _ORD                       # „varianta a patra”
    + r"|\b" + _ORD + r"\s+variant(?:ă|a|e)"              # „a doua variantă”, „primele trei variante”
    + r"|\b" + _ORD + r"\s+op[țt]iun(?:e|i)"
    + r"|\bvarianta\s+(?:de\s+la\s+)?litera\s+[A-D]\b"
    + r"|\br[ăa]spunsul\s+(?:de\s+la\s+)?litera\s+[A-D]\b", re.I)


def referiri_pozitionale(q):
    """Fragmentele din explicație care trimit la poziția unei variante."""
    return [m.group(0) for m in _POZITIE.finditer(q.get("explicatie") or "")]


# ---------- Starea: textul normativ relevant ----------
def _note_articol(fisier, anexa, art):
    """Liniile §NOTA§ care cad în interiorul articolului dat (note ale portalului:
    abrogări, modificări). NU sunt text normativ, dar sunt singura dovadă că un
    alineat a fost abrogat — articole_din_text() le elimină, deci le citim separat."""
    cale = DIR_LEGISLATIE / fisier
    if not art or not cale.is_file():
        return ""
    in_zona, in_art, note = (anexa == ""), False, []
    for l in cale.read_text(encoding="utf-8").split("\n"):
        if l.startswith("§ANEXA§"):
            in_zona, in_art = (anexa != "" and l == "§ANEXA§ " + anexa), False
            continue
        if not in_zona:
            continue
        m = re.match(r"^Articolul (\d+(?:\^\d+)?)$", l)
        if m:
            in_art = (m.group(1) == art)
        elif l.startswith("## "):
            in_art = False          # titlu de capitol/secțiune: notele de după el sunt
                                    # ale capitolului următor, nu ale articolului („Cap. V
                                    # a fost abrogat” ajungea în notele art. 13 din HG 52)
        elif in_art and l.startswith("§NOTA§"):
            note.append(l[6:].strip())
    return "\n".join(note)[:MAX_VECINE * 2]


def _sectiune(sursa, cache):
    """(textul articolului citat, textul articolelor vecine) din forma consolidată."""
    fisier, anexa = sursa.get("fisier", ""), sursa.get("anexa", "")
    art = eticheta_articol(sursa.get("articol", ""))
    cheie = (fisier, anexa)
    if cheie not in cache:
        cale = DIR_LEGISLATIE / fisier
        cache[cheie] = bibliografie.articole_din_text(str(cale), anexa) if cale.is_file() else {}
    arts = cache[cheie]
    if not art or art not in arts:
        return None, ""
    propriu = "Articolul %s\n%s" % (art, "\n".join(arts[art]))
    etichete = sorted(arts, key=bibliografie.cheie)
    i = etichete.index(art)
    vecine = []
    for j in (i - 1, i + 1):
        if 0 <= j < len(etichete):
            e = etichete[j]
            vecine.append("Articolul %s\n%s" % (e, "\n".join(arts[e])[:MAX_VECINE]))
    return propriu, "\n\n".join(vecine)


def _variante(q):
    return {LITERE[i]: v for i, v in enumerate(q.get("variante") or [])}


def _litere_cheie(q):
    return [LITERE[i] for i in (q.get("corecte") or []) if isinstance(i, int) and i < len(LITERE)]


# ---------- Întrebările ----------
def _cerere_variante(client, q, sectiune, vecine):
    """Cererea A — fără cheie, fără explicație: fiecare variantă judecată independent."""
    from typesafe_sdk import Choice
    var = _variante(q)
    stare = {
        "enunt": q["intrebare"],
        "variante": var,
        "sectiune": sectiune,
        "articole_vecine": vecine,
    }
    intrebari = {}
    for lit in var:
        intrebari["var_" + lit] = Choice(
            instructions=(
                "Cum se raportează textul normativ din `sectiune` și `articole_vecine` "
                "la varianta `variante.%s`, luată ca răspuns la `enunt`?" % lit),
            criteria={
                "sustine": "Textul afirmă sau implică direct că această variantă este un "
                           "răspuns corect la enunț.",
                "contrazice": "Textul afirmă altceva: varianta este incompatibilă cu ce "
                              "spune textul, sau redă greșit un termen, cuantum, organ "
                              "competent ori condiție.",
                "nu_spune": "Textul nu tratează ce afirmă varianta; pe baza lui nu se "
                            "poate decide dacă varianta răspunde la enunț.",
            },
        )
    return client.system_one(state=stare, questions=intrebari)


_FRAZA = re.compile(r"(?<=[.!?])\s+(?=[A-ZĂÂÎȘȚ„])")
_ART_CITAT = re.compile(r"\bart\.\s*(\d+(?:\^\d+)?)", re.I)


def articole_invocate(explicatie, sursa, cache, fara=(), maxim=6):
    """Articolele pe care le NUMEȘTE explicația, aduse din textul legii.

    SPEC §4.4 cere ca explicația să arate din ce articol vine valoarea fiecărui
    distractor. Fără acele articole în stare, orice afirmație corectă despre ele
    iese „neverificabilă” — codul le găsește (regex pe explicație), modelul le judecă.
    Se caută în zona declarată, apoi în corpul legii (explicațiile din anexa VI
    trimit des la corpul Legii 153/2017)."""
    fisier, anexa = sursa.get("fisier", ""), sursa.get("anexa", "")
    gasite, out = [], []
    for m in _ART_CITAT.finditer(explicatie or ""):
        a = m.group(1)
        if a not in gasite and a not in fara:
            gasite.append(a)
    for a in gasite[:maxim]:
        for zona in ([anexa, ""] if anexa else [""]):
            k = (fisier, zona)
            if k not in cache:
                cale = DIR_LEGISLATIE / fisier
                cache[k] = bibliografie.articole_din_text(str(cale), zona) if cale.is_file() else {}
            if a in cache[k] and cache[k][a]:
                eticheta = "Articolul %s%s" % (a, " (din anexă)" if zona else " (din corpul legii)")
                out.append("%s\n%s" % (eticheta, "\n".join(cache[k][a])[:MAX_INVOCAT]))
                break
    return "\n\n".join(out)


def fraze_explicatie(explicatie, maxim=8):
    """Explicația, împărțită în afirmații verificabile separat."""
    return [f.strip() for f in _FRAZA.split(explicatie or "") if len(f.strip()) > 25][:maxim]


def _cerere_calitate(client, q, sectiune, note, vecine, invocate):
    """Cererea B — cu cheie: explicația (frază cu frază) și forma întrebării."""
    from typesafe_sdk import Choice, Noul, Score
    stare = {
        "enunt": q["intrebare"],
        "variante": _variante(q),
        "variante_corecte": _litere_cheie(q),
        "explicatie": q.get("explicatie", ""),
        "temei": {"act": q["sursa"].get("act", ""),
                  "articol": q["sursa"].get("articol", ""),
                  "citat": q["sursa"].get("citat", "")},
        "sectiune": sectiune,
        "note_portal": note,
        "articole_vecine": vecine,
        "articole_invocate": invocate,
        "afirmatii": {str(i): f for i, f in enumerate(fraze_explicatie(q.get("explicatie", "")))},
    }
    intrebari = {
        "sinonim": Noul(instructions=(
            "Există vreo variantă din `variante` care NU este în `variante_corecte` și care "
            "diferă de o variantă corectă doar prin formulare (sinonim, topică, parafrază), "
            "fără o diferență de conținut juridic?")),
        "absolut": Noul(instructions=(
            "Conține `explicatie` o afirmație absolută — de exemplu „legea nu prevede”, "
            "„nu apare în text”, „doar”, „în toate cazurile”, „niciodată” — care NU este "
            "susținută de textul din `sectiune`?")),
        "abrogat": Noul(instructions=(
            "Textul din `sectiune` pe care se sprijină `temei.articol` este marcat ca abrogat "
            "sau ca nemaifiind în vigoare pentru situația din `enunt`?")),
        "numeste_actul": Noul(instructions=(
            "Numește `enunt` actul normativ la care se referă întrebarea (de exemplu „Potrivit "
            "Legii nr. 80/1995...”), astfel încât întrebarea să poată fi citită singură?")),
        "categorie_ambigua": Noul(instructions=(
            "Ar putea răspunsul corect la `enunt` să difere după categoria de personal vizată "
            "(cadru militar în activitate / în rezervă / în retragere / salariat / funcționar "
            "public cu statut special), fără ca `enunt` să precizeze despre care categorie e vorba?")),
        "citat_acopera": Noul(instructions=(
            "Fragmentul `temei.citat` conține efectiv norma pe care se sprijină răspunsul "
            "corect, nu doar o parte tangențială a articolului?")),
        "nivel": Score(instructions="Ce nivel de dificultate are `enunt` pentru un examen?",
                       criteria=["lexic trivial: cere doar denumirea unui act sau a unei instituții",
                                 "reproducere simplă: redă o definiție sau o enumerare scurtă",
                                 "termen, cuantum sau procent exact din text",
                                 "condiții cumulative ori organ competent (cine aprobă, cine decide)",
                                 "excepție pe categorii sau coroborarea a două articole"]),
    }
    for i in stare["afirmatii"]:
        intrebari["afirmatie_" + i] = Choice(
            instructions=("Cum se raportează textul normativ pus la dispoziție (`sectiune`, "
                          "`note_portal`, `articole_vecine`, `articole_invocate`) la afirmația "
                          "`afirmatii.%s` din explicație?" % i),
            criteria={
                "sustine": "Textul pus la dispoziție confirmă afirmația.",
                "contrazice": "Textul pus la dispoziție spune altceva: afirmația e greșită, "
                              "trimite la alt articol decât cel care conține norma, sau redă "
                              "greșit un termen, un cuantum ori o condiție.",
                "nu_spune": "Afirmația nu poate fi verificată cu textul pus la dispoziție — "
                            "se sprijină pe alt articol sau pe altă lege, care nu sunt aici.",
            })
    return client.system_one(state=stare, questions=intrebari)


# ---------- Judecata brută pentru o întrebare ----------
def judeca(client, q, cache):
    sectiune, vecine = _sectiune(q.get("sursa") or {}, cache)
    if sectiune is None:
        return {"id": q.get("id"), "eroare": "articolul din sursa nu a fost găsit în textul legii"}
    note = _note_articol((q.get("sursa") or {}).get("fisier", ""),
                         (q.get("sursa") or {}).get("anexa", ""),
                         eticheta_articol((q.get("sursa") or {}).get("articol", "")))
    ra = _cerere_variante(client, q, sectiune, vecine)
    invocate = articole_invocate(q.get("explicatie", ""), q.get("sursa") or {}, cache,
                                 fara=(eticheta_articol((q.get("sursa") or {}).get("articol", "")),))
    rb = _cerere_calitate(client, q, sectiune, note, vecine, invocate)
    variante = {}
    for lit in _variante(q):
        c = ra.choices["var_" + lit]
        variante[lit] = {"alegere": c.choice,
                         "probabilitati": dict(c.probabilities),
                         "confidence": c.confidence}
    nivel = rb.scores["nivel"]
    return {
        "id": q.get("id"),
        "cheie": _litere_cheie(q),
        "temei": [(q.get("sursa") or {}).get("fisier", ""),
                  eticheta_articol((q.get("sursa") or {}).get("articol", "")) or ""],
        # semnalul `abrogat` singur nu separă abrogarea de modificare (0.78-0.81 pe articole
        # doar modificate, 0.85-0.98 pe cele abrogate). Codul găsește nota, modelul o judecă:
        # poarta cere ambele.
        "nota_abrogare": bool(_NOTA_ABROGARE.search(note)),
        "tip": q.get("tip"),
        "variante": variante,
        "nouls": {k: rb.nouls[k].noul for k in
                  ("sinonim", "absolut", "abrogat", "numeste_actul",
                   "categorie_ambigua", "citat_acopera")},
        "afirmatii": {k[len("afirmatie_"):]: {"alegere": c.choice,
                                              "probabilitati": dict(c.probabilities),
                                              "confidence": c.confidence}
                      for k, c in rb.choices.items() if k.startswith("afirmatie_")},
        "fraze": fraze_explicatie(q.get("explicatie", "")),
        "pozitionale": referiri_pozitionale(q),
        "nivel": {"score": nivel.score, "confidence": nivel.confidence},
        "usage": {"a": ra.usage.input_tokens + ra.usage.output_tokens,
                  "b": rb.usage.input_tokens + rb.usage.output_tokens},
    }


# ---------- Politica: judecăți brute → verdict ----------
def verdict(j, praguri=None):
    """(verdict, [motive]) — REVIZUIT / INCERT / OK. Nu face niciun apel de rețea."""
    p = dict(PRAGURI, **(praguri or {}))
    if j.get("eroare"):
        return "REVIZUIT", [j["eroare"]]
    grave, incerte = [], []
    # Verificat pe toată banca (600 întrebări): judecățile pe variante și pe frazele
    # explicației produc alarme false cu încredere mare — modelul inversează perechile
    # (prescripție/decădere la L80-203, care H.G. pentru care categorie la L223-113) și
    # ratează trimiterile la litere (L80-328, lit. h) „prin demisie”). Toate trei cheile
    # verificate în lege erau corecte. Rămân ca semnal, dar în coada de revizuire.
    suspect = []
    for lit, v in sorted((j.get("variante") or {}).items()):
        pr = v["probabilitati"]
        p_sus = pr.get("sustine", 0.0)
        e_cheie = lit in j.get("cheie", [])
        if e_cheie and p_sus < p["sustine"]:
            suspect.append("cheia %s nu e susținută de text (p_sustine=%.2f, alegere=%s)"
                           % (lit, p_sus, v["alegere"]))
        if not e_cheie and p_sus >= p["aparabil"]:
            suspect.append("distractorul %s e apărabil ca răspuns corect (p_sustine=%.2f)"
                           % (lit, p_sus))
        if v["confidence"] < p["confidence"]:
            incerte.append("varianta %s: încredere mică (%.2f)" % (lit, v["confidence"]))
    for i, a in sorted((j.get("afirmatii") or {}).items()):
        pr = a["probabilitati"]
        fraza = (j.get("fraze") or [""] * 9)[int(i)] if int(i) < len(j.get("fraze") or []) else ""
        if pr.get("contrazice", 0) >= p["contrazice"]:
            suspect.append("explicație, fraza %s contrazisă de text (p=%.2f): „%s”"
                           % (i, pr["contrazice"], fraza[:90]))
        elif pr.get("nu_spune", 0) >= p["neverificabil"]:
            incerte.append("explicație, fraza %s nu se poate verifica din temeiul citat "
                           "(p=%.2f): „%s”" % (i, pr["nu_spune"], fraza[:90]))
    for frag in j.get("pozitionale") or []:
        grave.append("explicația trimite la poziția variantei („%s”) — asambleaza.py "
                     "amestecă variantele" % frag)
    n = j.get("nouls") or {}
    if n.get("abrogat", 0) >= p["noul"] and tuple(j.get("temei") or ("", "")) not in ABROGARE_ASUMATA:
        if j.get("nota_abrogare"):
            grave.append("temeiul pare abrogat (p=%.2f, confirmat de o notă de abrogare)"
                         % n["abrogat"])
        else:
            suspect.append("temeiul pare abrogat (p=%.2f), dar articolul nu are notă de "
                           "abrogare — probabil doar modificat" % n["abrogat"])
    if n.get("sinonim", 0) >= p["noul"]:
        suspect.append("distractor cvasi-sinonim cu cheia (p=%.2f)" % n["sinonim"])
    if n.get("absolut", 0) >= p["noul"]:
        incerte.append("explicația conține o afirmație absolută nesusținută (p=%.2f)" % n["absolut"])
    if n.get("numeste_actul", 1) <= 1 - p["noul"]:
        incerte.append("enunțul nu numește actul (p=%.2f)" % n["numeste_actul"])
    if n.get("categorie_ambigua", 0) >= p["noul"]:
        incerte.append("categoria de personal e ambiguă în enunț (p=%.2f)" % n["categorie_ambigua"])
    if n.get("citat_acopera", 1) <= 1 - p["noul"]:
        incerte.append("citatul nu acoperă norma pe care stă răspunsul (p=%.2f)" % n["citat_acopera"])
    if grave:
        return "REVIZUIT", grave + suspect + incerte
    if suspect or incerte:
        return "INCERT", suspect + incerte
    return "OK", []


# ---------- Raport ----------
def raport(judecati, praguri=None):
    rezumat = {"OK": 0, "INCERT": 0, "REVIZUIT": 0}
    linii = []
    for j in judecati:
        v, motive = verdict(j, praguri)
        rezumat[v] += 1
        if v != "OK":
            linii.append("  %-10s %-9s %s" % (j.get("id"), v, ("; ".join(motive))[:240]))
    return rezumat, linii


def main(argv):
    praguri, fisiere, din, doar_poz = {}, [], None, False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--doar-pozitionale":
            doar_poz = True
        elif a == "--din":
            i += 1; din = argv[i]
        elif a.startswith("--prag-"):
            nume = a[len("--prag-"):]
            i += 1; praguri[nume] = float(argv[i])
        else:
            fisiere.append(a)
        i += 1

    if doar_poz:
        gasite = 0
        for f in fisiere:
            for q in incarca_intrebari(f):
                r = referiri_pozitionale(q)
                if r:
                    gasite += 1
                    print("  %-28s %-10s %s" % (f, q.get("id"), r))
        print("referiri poziționale: %d (explicațiile trimit la poziția variantei, "
              "iar asambleaza.py amestecă variantele)" % gasite)
        return 1 if gasite else 0

    if din:
        judecati = json.loads(Path(din).read_text(encoding="utf-8"))
        rezumat, linii = raport(judecati, praguri)
        print("%s: %s" % (din, rezumat))
        print("\n".join(linii))
        return 1 if rezumat["REVIZUIT"] else 0

    if not fisiere:
        print(__doc__); return 2
    if not os.environ.get("TYPESAFE_API_KEY"):
        print("TYPESAFE_API_KEY nu e setat în mediu."); return 2

    from typesafe_sdk import TypeSafeClient
    DIR_VERIFICARI.mkdir(exist_ok=True)
    cod = 0
    with TypeSafeClient() as client:
        for f in fisiere:
            lista = incarca_intrebari(f)
            cache = {}
            def sigur(q):
                """O cerere picată nu trebuie să arunce tot lotul: devine o judecată
                cu eroare, pe care verdict() o raportează ca REVIZUIT."""
                try:
                    return judeca(client, q, cache)
                except Exception as exc:                      # noqa: BLE001
                    return {"id": q.get("id"), "eroare": "%s: %s" % (type(exc).__name__, exc)}

            with ThreadPoolExecutor(max_workers=FIRE) as pool:
                judecati = list(pool.map(sigur, lista))
            iesire = DIR_VERIFICARI / (Path(f).stem + "-ts.json")
            iesire.write_text(json.dumps(judecati, ensure_ascii=False, indent=1), encoding="utf-8")
            rezumat, linii = raport(judecati, praguri)
            tok = sum((j.get("usage") or {}).get("a") or 0 for j in judecati) + \
                  sum((j.get("usage") or {}).get("b") or 0 for j in judecati)
            print("%s: %s  (%d întrebări, %d tokens, judecăți în %s)"
                  % (f, rezumat, len(lista), tok, iesire.name))
            if linii:
                print("\n".join(linii))
            if rezumat["REVIZUIT"]:
                cod = 1
    return cod


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
