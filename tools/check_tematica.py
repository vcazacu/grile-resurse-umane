#!/usr/bin/env python3
"""Verifică paginile de sinteză din tools/tematica/NN.json contra textului legii.

tematica_build.py confirmă deja că fiecare `citat` apare verbatim în sursă. Ce nu se
verifica: dacă ce SCRIE sinteza rezultă din temeiul citat. Aici fiecare frază din
paragrafe și fiecare capcană devine o afirmație judecată separat (susține / contrazice /
nu spune nimic), peste textul integral al articolelor invocate de secțiune, descompus pe
alineate, cu trimiterile rezolvate până la literă.

    python3 check_tematica.py 01              # verifică tema 1
    python3 check_tematica.py 01 02 03        # mai multe teme
    python3 check_tematica.py --din tematica/01-ts.json   # re-aplică politica

Cod de ieșire 1 dacă există afirmații contrazise. Cere TYPESAFE_API_KEY.
"""
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import alineate as _alin
import bibliografie
from normalizare import DIR_LEGISLATIE, eticheta_articol

DIR_TEMATICA = Path(__file__).resolve().parent / "tematica"
FIRE = 6
MAX_ART = 9000

# Calibrat pe tema 1 (20.09.2026): 12 afirmații mutate deliberat (cifre, clase de grad,
# ministere) ies la p >= 0.99 în 10 din 12 cazuri, în timp ce afirmațiile verificate manual
# ca fiind corecte nu trec de 0.76. La 0.50 ieșeau 3 alarme false pe o temă fără erori.
PRAGURI = {"contrazice": 0.90, "neverificabil": 0.85}

_FRAZA = re.compile(r"(?<=[.!?])\s+(?=[A-ZĂÂÎȘȚ„])")


def fraze(text, minim=30):
    """Textul împărțit în afirmații verificabile separat (paragrafele au 2-5 fiecare)."""
    return [f.strip() for f in _FRAZA.split(text or "") if len(f.strip()) >= minim] or \
           ([text.strip()] if (text or "").strip() else [])


def _articole_sectiune(temeiuri, cache):
    """Textul integral al fiecărui articol invocat de temeiurile secțiunii, pe alineate."""
    out = {}
    for t in temeiuri:
        fisier, anexa = t.get("fisier", ""), t.get("anexa", "")
        art = eticheta_articol(t.get("articol", ""))
        if not art:
            continue
        k = (fisier, anexa)
        if k not in cache:
            cale = DIR_LEGISLATIE / fisier
            cache[k] = bibliografie.articole_din_text(str(cale), anexa) if cale.is_file() else {}
        linii = (cache[k] or {}).get(art)
        if not linii:
            continue
        bucati = _alin.descompune(linii)
        eticheta = "Articolul %s%s" % (art, " (%s)" % anexa if anexa else "")
        out[eticheta] = {
            kk: (vv["text"] + (" " + " ".join("%s %s" % (a, b) for a, b in vv["litere"].items())
                               if vv["litere"] else "")).strip()[:MAX_ART]
            for kk, vv in bucati.items()}
    return out


def _stare(tema, eticheta_sec, temeiuri, cache, afirmatii):
    text_ref = " ".join([t.get("citat", "") for t in temeiuri] + list(afirmatii.values()))
    rezolvate = {}
    for t in temeiuri:
        rezolvate.update(_alin.rezolva(text_ref, t, cache))
    return {
        "tema": tema,
        "sectiune": eticheta_sec,
        # Capcanele vorbesc des despre ce intră sau nu în tematică („art. 96 nu e în
        # bibliografie"). Fără lista oficială în stare, asemenea afirmații ies contrazise.
        "articole_cerute_de_tematica": {f: spec for f, (anexa, spec) in bibliografie.BIB.items()},
        "temeiuri_citate": {t.get("articol", ""): t.get("citat", "") for t in temeiuri},
        "articole": _articole_sectiune(temeiuri, cache),
        "trimiteri_rezolvate": rezolvate,
        "afirmatii": afirmatii,
    }


def _intreaba(client, stare):
    from typesafe_sdk import Choice
    intrebari = {}
    for i in stare["afirmatii"]:
        intrebari["a_" + i] = Choice(
            instructions=("Cum se raportează textul normativ pus la dispoziție (`articole`, "
                          "`trimiteri_rezolvate`, `temeiuri_citate`) la afirmația "
                          "`afirmatii.%s` din pagina de sinteză?" % i),
            criteria={
                "sustine": "Textul confirmă afirmația: o spune sau o implică direct.",
                "contrazice": "Textul spune altceva — afirmația redă greșit un termen, un "
                              "cuantum, o categorie de personal, un organ competent, "
                              "numărul unui articol sau al unui alineat.",
                "absenta_corecta": "Afirmația susține că ceva NU este prevăzut, NU apare în "
                                   "enumerare sau NU se aplică, iar textul pus la dispoziție "
                                   "îi dă dreptate: lucrul acela chiar lipsește de acolo.",
                "nu_spune": "Afirmația nu se poate verifica din textul pus la dispoziție: "
                            "se sprijină pe alt articol, pe altă lege sau pe tematica "
                            "examenului, care nu sunt aici; ori este un sfat de învățare, "
                            "nu o afirmație despre conținutul legii.",
            })
    return client.system_one(state=stare, questions=intrebari)


def _bucati(tema_json):
    """[(eticheta, temeiuri, {idx: afirmație})] — o bucată per paragraf și una per capcană."""
    out = []
    for s in tema_json.get("sectiuni") or []:
        tem = s.get("temei") or []
        for ip, par in enumerate(s.get("paragrafe") or []):
            fr = fraze(par)
            out.append(("%s / paragraful %d" % (s.get("titlu", "")[:60], ip + 1), tem,
                        {str(i): f for i, f in enumerate(fr)}))
    toate = [t for s in (tema_json.get("sectiuni") or []) for t in (s.get("temei") or [])]
    for ic, cap in enumerate(tema_json.get("capcane") or []):
        out.append(("capcana %d" % (ic + 1), toate, {str(i): f for i, f in enumerate(fraze(cap))}))
    return out


def verifica_tema(client, nr):
    cale = DIR_TEMATICA / ("%s.json" % nr)
    d = json.loads(cale.read_text(encoding="utf-8"))
    cache = {}
    bucati = [b for b in _bucati(d) if b[2]]

    def una(b):
        eticheta, tem, afirmatii = b
        try:
            stare = _stare(d.get("titlu", ""), eticheta, tem, cache, afirmatii)
            r = _intreaba(client, stare)
            return {"loc": eticheta,
                    "afirmatii": {k: {"text": afirmatii[k],
                                      "alegere": r.choices["a_" + k].choice,
                                      "probabilitati": dict(r.choices["a_" + k].probabilities),
                                      "confidence": r.choices["a_" + k].confidence}
                                  for k in afirmatii},
                    "usage": r.usage.input_tokens + r.usage.output_tokens}
        except Exception as exc:                                   # noqa: BLE001
            return {"loc": eticheta, "eroare": "%s: %s" % (type(exc).__name__, exc)}

    with ThreadPoolExecutor(max_workers=FIRE) as pool:
        return list(pool.map(una, bucati))


def raport(rezultate, praguri=None):
    p = dict(PRAGURI, **(praguri or {}))
    rez = {"sustinute": 0, "absente_ok": 0, "neverificabile": 0, "contrazise": 0, "erori": 0}
    linii = []
    for b in rezultate:
        if b.get("eroare"):
            rez["erori"] += 1
            linii.append("  EROARE  %s: %s" % (b["loc"], b["eroare"]))
            continue
        for k, a in sorted(b["afirmatii"].items(), key=lambda kv: int(kv[0])):
            pr = a["probabilitati"]
            if pr.get("absenta_corecta", 0) >= max(pr.get("contrazice", 0),
                                                    pr.get("sustine", 0),
                                                    pr.get("nu_spune", 0)):
                rez["absente_ok"] += 1
            elif pr.get("contrazice", 0) >= p["contrazice"]:
                rez["contrazise"] += 1
                linii.append("  CONTRAZIS (p=%.2f)  %s\n      „%s”"
                             % (pr["contrazice"], b["loc"], a["text"][:220]))
            elif pr.get("nu_spune", 0) >= p["neverificabil"]:
                rez["neverificabile"] += 1
                linii.append("  NEVERIFICABIL (p=%.2f)  %s\n      „%s”"
                             % (pr["nu_spune"], b["loc"], a["text"][:160]))
            else:
                rez["sustinute"] += 1
    return rez, linii


def main(argv):
    praguri, teme, din = {}, [], None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--din":
            i += 1; din = argv[i]
        elif a.startswith("--prag-"):
            i += 1; praguri[a[len("--prag-"):]] = float(argv[i])
        else:
            teme.append(a)
        i += 1

    if din:
        rez, linii = raport(json.loads(Path(din).read_text(encoding="utf-8")), praguri)
        print("%s: %s" % (din, rez)); print("\n".join(linii))
        return 1 if rez["contrazise"] else 0
    if not teme:
        print(__doc__); return 2
    if not os.environ.get("TYPESAFE_API_KEY"):
        print("TYPESAFE_API_KEY nu e setat în mediu."); return 2

    from typesafe_sdk import TypeSafeClient
    cod = 0
    with TypeSafeClient() as client:
        for nr in teme:
            rezultate = verifica_tema(client, nr)
            iesire = DIR_TEMATICA / ("%s-ts.json" % nr)
            iesire.write_text(json.dumps(rezultate, ensure_ascii=False, indent=1), encoding="utf-8")
            rez, linii = raport(rezultate, praguri)
            tok = sum(b.get("usage") or 0 for b in rezultate)
            print("tema %s: %s  (%d tokens, %s)" % (nr, rez, tok, iesire.name))
            if linii:
                print("\n".join(linii))
            if rez["contrazise"] or rez["erori"]:
                cod = 1
    return cod


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
