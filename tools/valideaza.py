#!/usr/bin/env python3
"""Validează banca de întrebări (intrebari.js sau fișierele nou/*.json) cu
EXACT regulile din app.js (valideazaIntrebari) plus câteva verificări în plus:
id-uri și texte duplicate între toate fișierele încărcate, fișierul-sursă există
în ../../legislatie/, grupul (fisier[#anexa]) există în bibliografie.BIB,
variante/corecte fără duplicate, „multiplu" cu cel mult 4 variante.

Utilizare:
    python3 valideaza.py [--teste [N]] [fisiere...]
Implicit: ../intrebari.js dacă există, altfel toate nou/*.json.
Regulile pe teste (20/test, max 4 multiple, test în 1..N) se aplică doar pentru
.js sau când se dă --teste (fără număr: N se citește din ../app.js, implicit 30).
Ieșire 1 dacă există erori. Importabil: incarca(path), valideaza(lista, nr_teste).
"""
import glob, json, os, re, sys

DIR = os.path.dirname(os.path.abspath(__file__))
LEGISLATIE = os.path.join(DIR, "..", "..", "legislatie")
APP_JS = os.path.join(DIR, "..", "app.js")
sys.path.insert(0, DIR)
from bibliografie import BIB


def nr_teste_din_app(implicit=30):
    """Citește `var NR_TESTE = N;` din app.js; implicit 30 dacă nu se găsește."""
    try:
        m = re.search(r"\bNR_TESTE\s*=\s*(\d+)", open(APP_JS, encoding="utf-8").read())
        return int(m.group(1)) if m else implicit
    except OSError:
        return implicit


def incarca(path):
    """Întoarce lista de întrebări dintr-un .json (array) sau .js (const INTREBARI = [...];)."""
    text = open(path, encoding="utf-8").read()
    if path.endswith(".js"):
        m = re.search(r"INTREBARI\s*=\s*", text)
        if not m:
            raise ValueError("%s: nu găsesc „INTREBARI =”" % path)
        start = text.find("[", m.end())
        stop = text.rfind("]")
        if start < 0 or stop < start:
            raise ValueError("%s: nu găsesc array-ul INTREBARI" % path)
        text = text[start:stop + 1]
    lista = json.loads(text)
    if not isinstance(lista, list):
        raise ValueError("%s: conținutul nu este un array JSON" % path)
    return lista


def grup(q):
    """Cheia de grup a unei întrebări: fisier[#anexa] — exact cheile din BIB."""
    s = q.get("sursa") or {}
    return str(s.get("fisier", "")) + ("#" + str(s["anexa"]) if s.get("anexa") else "")


def norm(s):
    return " ".join(str(s).casefold().split())


def e_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def valideaza(lista, nr_teste=None):
    """Întoarce lista de erori (goală = valid). nr_teste=None → fără regulile pe teste."""
    erori = []
    if not isinstance(lista, list) or not lista:
        return ["Lista nu conține un array de întrebări nevid."]
    ids, texte, per_test = {}, {}, {}
    for i, q in enumerate(lista):
        loc = "Întrebarea #%d%s" % (i + 1, " (%s)" % q["id"] if isinstance(q, dict) and q.get("id") else "")
        if not isinstance(q, dict):
            erori.append(loc + ": nu este un obiect."); continue
        e = lambda msg: erori.append(loc + ": " + msg)
        # --- regulile din app.js ---
        if not q.get("id"): e("lipsește câmpul id.")
        elif str(q["id"]) in ids: e("id duplicat (prima apariție: #%d)." % ids[str(q["id"])])
        else: ids[str(q["id"])] = i + 1
        tip = q.get("tip")
        if tip not in ("unic", "multiplu"): e('tip trebuie să fie "unic" sau "multiplu".')
        intr = q.get("intrebare")
        if not intr or not isinstance(intr, str): e("lipsește textul întrebării.")
        var = q.get("variante")
        if not isinstance(var, list) or len(var) < 2: e("variante trebuie să aibă cel puțin 2 elemente.")
        if tip == "unic" and isinstance(var, list) and len(var) != 4: e("întrebările cu răspuns unic trebuie să aibă exact 4 variante.")
        cor = q.get("corecte")
        if not isinstance(cor, list) or not cor: e("corecte trebuie să fie un array nevid de indecși.")
        else:
            if tip == "unic" and len(cor) != 1: e('tip "unic" cere exact un index în corecte.')
            if tip == "multiplu" and len(cor) < 2: e('tip "multiplu" cere cel puțin 2 indecși în corecte.')
            for c in cor:
                if not e_int(c) or c < 0 or not isinstance(var, list) or c >= len(var):
                    e("indexul corect %r nu există în variante." % (c,))
            if len(set(map(str, cor))) != len(cor): e("corecte conține indecși duplicați.")
        if not q.get("explicatie"): e("lipsește explicația.")
        s = q.get("sursa")
        if not isinstance(s, dict) or not s.get("act") or not s.get("articol") or not s.get("citat"):
            e("sursa trebuie să conțină act, articol și citat.")
        if q.get("status") not in ("ok", "de verificat"): e('status trebuie să fie "ok" sau "de verificat".')
        if nr_teste is not None:
            t = q.get("test")
            if not e_int(t) or t < 1 or t > nr_teste:
                e("test trebuie să fie un număr întreg între 1 și %d." % nr_teste)
            else:
                info = per_test.setdefault(t, {"total": 0, "multi": 0})
                info["total"] += 1
                if tip == "multiplu": info["multi"] += 1
        # --- verificări suplimentare ---
        if isinstance(intr, str) and intr:
            k = norm(intr)
            if k in texte: e("text duplicat cu întrebarea #%d." % texte[k])
            else: texte[k] = i + 1
        if isinstance(var, list):
            if len(set(norm(v) for v in var)) != len(var): e("variante conține elemente duplicate.")
            if tip == "multiplu" and len(var) > 4: e('tip "multiplu" cere cel mult 4 variante.')
        if isinstance(s, dict):
            fis = s.get("fisier")
            if not fis or not isinstance(fis, str): e("sursa.fisier lipsește.")
            elif not os.path.isfile(os.path.join(LEGISLATIE, fis)): e("sursa.fisier nu există în legislatie/: %s" % fis)
            if grup(q) not in BIB: e("grupul „%s” nu există în bibliografie.BIB." % grup(q))
    if nr_teste is not None:
        for t in range(1, nr_teste + 1):
            info = per_test.get(t)
            if not info: erori.append("Testul %d: nu are nicio întrebare." % t); continue
            if info["total"] != 20: erori.append("Testul %d: are %d întrebări în loc de 20." % (t, info["total"]))
            if info["multi"] > 4: erori.append("Testul %d: are %d întrebări cu răspunsuri multiple (maxim 4)." % (t, info["multi"]))
    return erori


def duplicate_intre_fisiere(seturi):
    """seturi = [(nume_fisier, lista)]; întoarce erorile de id/text duplicat ÎNTRE fișiere."""
    erori, ids, texte = [], {}, {}
    for nume, lista in seturi:
        for q in lista:
            if not isinstance(q, dict): continue
            qid = str(q.get("id") or "")
            if qid:
                if qid in ids and ids[qid] != nume: erori.append("%s: id „%s” apare și în %s." % (nume, qid, ids[qid]))
                ids.setdefault(qid, nume)
            if isinstance(q.get("intrebare"), str):
                k = norm(q["intrebare"])
                if k in texte and texte[k][0] != nume:
                    erori.append("%s (%s): text duplicat cu %s (%s)." % (nume, qid, texte[k][0], texte[k][1]))
                texte.setdefault(k, (nume, qid))
    return erori


def main(argv):
    nr_teste, fisiere = None, []
    i = 0
    while i < len(argv):
        if argv[i] == "--teste":
            nr_teste = 0  # 0 = se citește din app.js
            if i + 1 < len(argv) and argv[i + 1].isdigit(): nr_teste = int(argv[i + 1]); i += 1
        else:
            fisiere.append(argv[i])
        i += 1
    if not fisiere:
        implicit = os.path.join(DIR, "..", "intrebari.js")
        fisiere = [implicit] if os.path.isfile(implicit) else sorted(glob.glob(os.path.join(DIR, "nou", "*.json")))
    if not fisiere:
        print("Nimic de validat: nu există ../intrebari.js și nici nou/*.json."); return 1
    if nr_teste == 0: nr_teste = nr_teste_din_app()
    total_erori, seturi = 0, []
    for f in fisiere:
        try:
            lista = incarca(f)
        except (OSError, ValueError, json.JSONDecodeError) as ex:
            print("%s: EROARE la încărcare: %s" % (f, ex)); total_erori += 1; continue
        cu_teste = nr_teste if (nr_teste is not None or f.endswith(".js")) else None
        if cu_teste is None and f.endswith(".js"): cu_teste = nr_teste_din_app()
        erori = valideaza(lista, cu_teste)
        nmulti = sum(1 for q in lista if isinstance(q, dict) and q.get("tip") == "multiplu")
        print("%s: %d întrebări (%d multiple)%s, %d erori" % (
            os.path.relpath(f), len(lista), nmulti, ", %d teste" % cu_teste if cu_teste else "", len(erori)))
        for er in erori: print("  - " + er)
        total_erori += len(erori)
        seturi.append((os.path.basename(f), lista))
    if len(seturi) > 1:
        erori = duplicate_intre_fisiere(seturi)
        for er in erori: print("  - " + er)
        total_erori += len(erori)
    print("TOTAL: %d întrebări, %d erori — %s" % (sum(len(l) for _, l in seturi), total_erori, "VALID" if not total_erori else "INVALID"))
    return 1 if total_erori else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
