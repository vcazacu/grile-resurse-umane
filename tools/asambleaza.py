#!/usr/bin/env python3
"""Asamblează banca de întrebări din nou/*.json în ../intrebari.js:
validare (valideaza.py), cote pe act (COTE), selecție uniformă pe articole,
intercalare proporțională pe teste, reparare „max 4 multiple/test", raport.

Utilizare:
    python3 asambleaza.py [--teste 30] [--marime 20] [--permite-deficit] [--scrie]
    python3 asambleaza.py --raport-din ../intrebari.js     (doar raportul de distribuție al unui fișier existent)
    --scaleaza-cote: COTE se scalează proporțional la teste × mărime (ex. un singur test de calibrare)
Fără --scrie doar afișează raportul (dry run).
"""
import glob, json, os, re, sys

DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DIR)
from bibliografie import cheie
from valideaza import incarca, valideaza, grup, nr_teste_din_app

# Cote-țintă pe grup (fisier[#anexa]); suma trebuie să fie teste × marime.
COTE = {
 "01_Legea_80-1995_statutul_cadrelor_militare.txt": 115,
 "02_Legea_1-1998_organizarea_SIE.txt": 20,
 "03_Legea_53-2003_Codul_muncii.txt": 115,
 "04_Legea_223-2015_pensiile_militare.txt": 55,
 "05_Legea_360-2023_sistemul_public_de_pensii.txt": 55,
 "06_Legea_153-2017_salarizarea_bugetara.txt": 15,
 "06_Legea_153-2017_salarizarea_bugetara.txt#Anexa nr. VI": 55,
 "07_OUG_111-2010_concediul_crestere_copil.txt": 65,
 "08_Norme_HG_52-2011_aplicare_OUG_111-2010.txt": 60,
 "09_HG_1867-2005_compensatia_chirie.txt": 45,
}
ETICHETE = {
 "01_Legea_80-1995_statutul_cadrelor_militare.txt": "L80",
 "02_Legea_1-1998_organizarea_SIE.txt": "L1",
 "03_Legea_53-2003_Codul_muncii.txt": "CM",
 "04_Legea_223-2015_pensiile_militare.txt": "L223",
 "05_Legea_360-2023_sistemul_public_de_pensii.txt": "L360",
 "06_Legea_153-2017_salarizarea_bugetara.txt": "L153",
 "06_Legea_153-2017_salarizarea_bugetara.txt#Anexa nr. VI": "A6",
 "07_OUG_111-2010_concediul_crestere_copil.txt": "OUG111",
 "08_Norme_HG_52-2011_aplicare_OUG_111-2010.txt": "HG52",
 "09_HG_1867-2005_compensatia_chirie.txt": "HG1867",
}
MAX_MULTI = 4
ORDINE_CHEI = ["id", "tip", "test", "intrebare", "variante", "corecte", "explicatie", "sursa", "status"]


def et(g):
    return ETICHETE.get(g, g)


def cheie_articol(q):
    """Ordinea articolului din sursa.articol („art. 9^1 alin. (2)" → (9, 1)); necunoscut → la coadă."""
    m = re.match(r"^art\.\s*(\d+(?:\^\d+)?)", str(q["sursa"].get("articol", "")).strip(), re.I)
    return cheie(m.group(1)) if m else (10 ** 9, 0)


def repartizeaza(ponderi, total):
    """Împarte `total` proporțional cu ponderile (rotunjire cu restul cel mai mare)."""
    baza = sum(ponderi.values())
    brut = {g: (ponderi[g] * total / baza if baza else 0) for g in ponderi}
    rez = {g: int(v) for g, v in brut.items()}
    for g in sorted(brut, key=lambda g: brut[g] - rez[g], reverse=True)[:total - sum(rez.values())]:
        rez[g] += 1
    return rez


def ajusteaza_cote(cote, disp, total):
    """--permite-deficit: grupurile deficitare dau tot ce au; restul se împarte
    proporțional cu cotele originale între grupurile cu surplus (plafonat la disponibil)."""
    fix = {g: disp[g] for g in cote if disp[g] < cote[g]}
    while True:
        libere = {g: cote[g] for g in cote if g not in fix}
        noi = repartizeaza(libere, total - sum(fix.values())) if libere else {}
        depasite = [g for g in noi if noi[g] > disp[g]]
        if not depasite:
            return {g: (fix if g in fix else noi)[g] for g in cote}  # păstrează ordinea din COTE
        for g in depasite: fix[g] = disp[g]


def selecteaza(intrebari, cota):
    """Sortează pe articol (status „ok" înaintea „de verificat" în același articol)
    și alege `cota` întrebări răspândite uniform pe parcursul actului."""
    lst = sorted(intrebari, key=lambda q: 0 if q.get("status") == "ok" else 1)
    lst.sort(key=cheie_articol)  # stabil: în același articol rămân „ok" primele
    n = len(lst)
    if cota >= n:
        return lst
    # 1) acoperirea tematicii: prima întrebare („ok" dacă există) din fiecare articol e garantată
    garantate, vazute = [], set()
    for q in lst:
        k = cheie_articol(q)
        if k not in vazute:
            vazute.add(k); garantate.append(q)
    if len(garantate) >= cota:
        idx = sorted({min(len(garantate) - 1, int(round((i + 0.5) * len(garantate) / cota))) for i in range(cota)})
        return [garantate[i] for i in idx]
    # 2) restul cotei se umple uniform din întrebările rămase, păstrând ordinea pe articole
    rest = [q for q in lst if not any(q is g for g in garantate)]
    lipsa = cota - len(garantate)
    idx = sorted({min(len(rest) - 1, int(round((i + 0.5) * len(rest) / lipsa))) for i in range(lipsa)}) if lipsa else []
    ales = garantate + [rest[i] for i in idx]
    ales.sort(key=cheie_articol)
    return ales


def repara_multiple(teste, marime):
    """Schimbă întrebări între teste până când niciun test nu are > MAX_MULTI multiple."""
    nmulti = lambda t: sum(1 for q in t if q["tip"] == "multiplu")
    schimburi = 0
    while True:
        a = max(range(len(teste)), key=lambda i: nmulti(teste[i]))
        if nmulti(teste[a]) <= MAX_MULTI:
            return schimburi
        b = min(range(len(teste)), key=lambda i: nmulti(teste[i]))
        if nmulti(teste[b]) >= MAX_MULTI:
            sys.exit("EROARE: prea multe întrebări „multiplu” în total (%d > %d = %d teste × %d)." % (
                sum(nmulti(t) for t in teste), MAX_MULTI * len(teste), len(teste), MAX_MULTI))
        multi_a = [i for i, q in enumerate(teste[a]) if q["tip"] == "multiplu"]
        unic_b = [j for j, q in enumerate(teste[b]) if q["tip"] != "multiplu"]
        pereche = next(((i, j) for i in multi_a for j in unic_b if grup(teste[a][i]) == grup(teste[b][j])), None)
        i, j = pereche or (multi_a[0], unic_b[0])
        teste[a][i], teste[b][j] = teste[b][j], teste[a][i]
        schimburi += 1


def raport(teste, cote, total_grup):
    grupuri = list(cote)
    print("\nRaport pe teste (număr de întrebări pe grup | multiple):")
    for t, lst in enumerate(teste, 1):
        nr = {g: 0 for g in grupuri}
        for q in lst: nr[grup(q)] = nr.get(grup(q), 0) + 1
        parti = ["%s=%d" % (et(g), nr[g]) for g in grupuri if nr[g]]
        nm = sum(1 for q in lst if q["tip"] == "multiplu")
        print("  Test %2d: %-3d %s | multiple=%d%s" % (t, len(lst), " ".join(parti), nm, "  <-- PESTE LIMITĂ" if nm > MAX_MULTI else ""))
    print("\nTotal pe grup (selectat / cotă / disponibil):")
    sel = {g: 0 for g in grupuri}
    for lst in teste:
        for q in lst: sel[grup(q)] = sel.get(grup(q), 0) + 1
    for g in grupuri:
        print("  %-8s %3d / %3d / %3d   %s" % (et(g), sel[g], cote[g], total_grup.get(g, 0), g))
    print("  %-8s %3d / %3d / %3d" % ("TOTAL", sum(sel.values()), sum(cote.values()), sum(total_grup.values())))


def scrie_js(cale, lista, teste, marime):
    """Scrie intrebari.js cu antet + `const INTREBARI = [...];`, cheile în ordinea standard."""
    ordonat = [{k: q[k] for k in ORDINE_CHEI if k in q} | {k: v for k, v in q.items() if k not in ORDINE_CHEI} for q in lista]
    antet = ("/* Banca de întrebări: %d întrebări în %d teste × %d.\n"
             "   Generat de tools/asambleaza.py din tools/nou/*.json — regenerează, nu edita manual.\n"
             "   Câmpuri: id, tip (\"unic\" | \"multiplu\"), test (1..%d), intrebare, variante,\n"
             "   corecte (indecși de la 0), explicatie, sursa {act, articol, citat, fisier[, anexa]},\n"
             "   status (\"ok\" | \"de verificat\").\n"
             "   Surse: formele consolidate la zi de pe legislatie.just.ro (Portal Legislativ),\n"
             "   descărcate în folderul legislatie/.\n"
             "   După orice editare deschide index.html: validatorul semnalează erorile. */\n"
             % (len(lista), teste, marime, teste))
    with open(cale, "w", encoding="utf-8") as f:
        f.write(antet + "const INTREBARI = " + json.dumps(ordonat, ensure_ascii=False, indent=2) + ";\n")


def raport_din(cale, marime=20):
    """Raportul de distribuție + verificarea regulilor per test pentru un intrebari.js deja scris."""
    lista = incarca(cale)
    teste = max((q.get("test", 0) for q in lista), default=0)
    teste_lst = [[q for q in lista if q.get("test") == t] for t in range(1, teste + 1)]
    disp = {}
    for q in lista: disp[grup(q)] = disp.get(grup(q), 0) + 1
    raport(teste_lst, COTE, disp)
    erori = valideaza(lista, teste)
    if erori:
        for e in erori: print("  - " + e)
        print("%d×%d, max %d multiple: NECONFORM (%d erori)" % (teste, marime, MAX_MULTI, len(erori)))
        return 1
    print("%d×%d, max %d multiple: CONFORM" % (teste, marime, MAX_MULTI))
    return 0


def main(argv):
    teste, marime, scrie, permite, scaleaza = nr_teste_din_app(), 20, False, False, False
    if "--raport-din" in argv:
        return raport_din(argv[argv.index("--raport-din") + 1])
    i = 0
    while i < len(argv):
        if argv[i] == "--teste": teste = int(argv[i + 1]); i += 1
        elif argv[i] == "--marime": marime = int(argv[i + 1]); i += 1
        elif argv[i] == "--scrie": scrie = True
        elif argv[i] == "--permite-deficit": permite = True
        elif argv[i] == "--scaleaza-cote": scaleaza = True
        else: sys.exit("Argument necunoscut: %s\n%s" % (argv[i], __doc__))
        i += 1
    if teste != nr_teste_din_app():
        print("ATENȚIE: --teste %d diferă de NR_TESTE=%d din app.js — aplicația va raporta erori." % (teste, nr_teste_din_app()))
    total = teste * marime
    if scaleaza and sum(COTE.values()) != total:
        noi = repartizeaza(COTE, total)
        print("Cote scalate la %d: %s" % (total, ", ".join("%s=%d" % (et(g), noi[g]) for g in COTE)))
        COTE.clear(); COTE.update(noi)
    if sum(COTE.values()) != total:
        sys.exit("EROARE: suma cotelor (%d) diferă de teste × mărime (%d × %d = %d). Editează COTE." % (sum(COTE.values()), teste, marime, total))

    # 1. încărcare + validare
    fisiere = sorted(glob.glob(os.path.join(DIR, "nou", "*.json")))
    if not fisiere: sys.exit("EROARE: nu există fișiere în %s." % os.path.join(DIR, "nou"))
    lista = []
    for f in fisiere:
        parte = incarca(f); lista += parte
        print("%s: %d întrebări" % (os.path.relpath(f), len(parte)))
    erori = valideaza(lista)
    if erori:
        for e in erori: print("  - " + e)
        sys.exit("EROARE: %d erori de validare — corectează fișierele din nou/ mai întâi." % len(erori))
    grupuri = {}
    for q in lista: grupuri.setdefault(grup(q), []).append(q)
    straine = [g for g in grupuri if g not in COTE]
    if straine: sys.exit("EROARE: grupuri fără cotă în COTE: %s" % straine)

    # 2. cote vs disponibil
    disp = {g: len(grupuri.get(g, [])) for g in COTE}
    deficit = {g: COTE[g] - disp[g] for g in COTE if disp[g] < COTE[g]}
    cote = dict(COTE)
    if deficit:
        print("\nDeficit pe grup (lipsesc / cotă):")
        for g in deficit: print("  %-8s lipsesc %3d (există %3d din %3d)" % (et(g), deficit[g], disp[g], COTE[g]))
        if not permite: sys.exit("EROARE: întrebări insuficiente — generează mai multe sau rulează cu --permite-deficit.")
        if sum(disp.values()) < total:
            teste = sum(disp.values()) // marime; total = teste * marime
            print("  Disponibil %d < %d: se reduce la %d teste." % (sum(disp.values()), teste * marime if teste else 0, teste))
            if not teste: sys.exit("EROARE: nu se poate umple niciun test.")
            cote = repartizeaza(COTE, total)
        cote = ajusteaza_cote(cote, disp, total)
        print("  Cote ajustate proporțional: " + ", ".join("%s=%d" % (et(g), cote[g]) for g in cote))

    # 3. selecție uniformă pe articole + intercalare pe poziție virtuală
    pozitii = []
    for g in COTE:
        sel = selecteaza(grupuri.get(g, []), cote[g])
        for i, q in enumerate(sel):
            pozitii.append(((i + 0.5) * total / len(sel), g, q))
    pozitii.sort(key=lambda p: (p[0], p[1]))
    ordonate = [q for _, _, q in pozitii]
    assert len(ordonate) == total, "selecție incompletă: %d ≠ %d" % (len(ordonate), total)
    teste_lst = [ordonate[t * marime:(t + 1) * marime] for t in range(teste)]

    # 4. reparare max 4 multiple / test
    schimburi = repara_multiple(teste_lst, marime)
    assert all(sum(1 for q in t if q["tip"] == "multiplu") <= MAX_MULTI for t in teste_lst)
    final = []
    for t, lst in enumerate(teste_lst, 1):
        for q in lst:
            final.append({**q, "test": t})

    # 5. raport + scriere
    raport(teste_lst, cote, disp)
    print("\nSchimburi pentru max %d multiple/test: %d" % (MAX_MULTI, schimburi))
    erori = valideaza(final, teste)
    if erori:
        for e in erori: print("  - " + e)
        print("%d×%d, max %d multiple: NECONFORM (%d erori)" % (teste, marime, MAX_MULTI, len(erori)))
        return 1
    print("%d×%d, max %d multiple: CONFORM" % (teste, marime, MAX_MULTI))
    if scrie:
        cale = os.path.join(DIR, "..", "intrebari.js")
        scrie_js(cale, final, teste, marime)
        print("Scris: %s (%d întrebări)" % (os.path.relpath(cale), len(final)))
    else:
        print("(dry run — rulează cu --scrie pentru a scrie ../intrebari.js)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
