"""Bibliografia oficială a examenului: pentru fiecare fișier-sursă, intervalele de
articole cerute (exact ca în „Tematică și bibliografie.docx"). Este singura
sursă de adevăr pentru „ce intră în tematică" — o folosesc clasifica.py,
check_articol.py și asambleaza.py.

Cheia = numele fișierului .txt din ../../legislatie/ (+ „#<anexa>" când
articolele sunt din anexă, care are numerotare proprie).
Valoarea = (numele anexei sau "", șirul de intervale).
Notație: „9^1" = art. 9 indice 1 (așa apare și în text: „Articolul 9^1").
"""
BIB = {
 "01_Legea_80-1995_statutul_cadrelor_militare.txt": ("", "1-9^1, 11-15, 17-18, 20^1-21, 23, 26, 28-30, 33-35, 36-41, 42-43, 45, 46, 48, 50-56, 63-64, 68-71, 73, 76, 81, 85-91, 94-95, 97, 109-110, 112"),
 "02_Legea_1-1998_organizarea_SIE.txt": ("", "1-3, 5-9, 13, 14-15, 18, 20"),
 "03_Legea_53-2003_Codul_muncii.txt": ("", "1-2, 10-12, 14, 16, 17, 27-34, 39-52, 54-61, 63-65, 75-77, 81-85, 103-106, 111-123, 125-127, 135-139, 141-142, 144-147^1, 149-155, 158, 247-252"),
 "04_Legea_223-2015_pensiile_militare.txt": ("", "1-3, 6, 9-21, 23-30, 32-35, 38, 42-43, 45, 47-52, 57-58, 81, 84"),
 "05_Legea_360-2023_sistemul_public_de_pensii.txt": ("", "1-3, 6, 9, 13-15, 25-26, 32, 39, 44-48, 51, 58-62, 66-69, 72-75, 79, 108, 111-116"),
 "06_Legea_153-2017_salarizarea_bugetara.txt": ("", "7, 10, 14, 15, 20, 21"),
 "06_Legea_153-2017_salarizarea_bugetara.txt#Anexa nr. VI": ("Anexa nr. VI", "1-3, 5-7, 8-9, 11, 14, 15, 15^1, 18-21, 28-29, 58-62, 73-76, 84, 86, 88, 90-93"),
 "07_OUG_111-2010_concediul_crestere_copil.txt": ("", "1-5, 7-9^1, 11-17, 22, 25, 31-33, 35-37"),
 "08_Norme_HG_52-2011_aplicare_OUG_111-2010.txt": ("", "1-2, 4-8, 9^1, 12-13, 21, 23-26, 32, 36"),
 "09_HG_1867-2005_compensatia_chirie.txt": ("", "1-15, 17^2"),
}

# Restricții pe alineate/litere din bibliografie (restul articolului NU e în tematică):
RESTRICTII = {
 ("01_Legea_80-1995_statutul_cadrelor_militare.txt", "45"): "doar lit. a)-f)",
 ("03_Legea_53-2003_Codul_muncii.txt", "16"): "doar alin. (1)-(3)",
 ("06_Legea_153-2017_salarizarea_bugetara.txt#Anexa nr. VI", "7"): "doar alin. (1)",
 ("06_Legea_153-2017_salarizarea_bugetara.txt#Anexa nr. VI", "9"): "doar alin. (1)",
 ("06_Legea_153-2017_salarizarea_bugetara.txt#Anexa nr. VI", "14"): "doar alin. (1)",
 ("06_Legea_153-2017_salarizarea_bugetara.txt#Anexa nr. VI", "86"): "doar alin. (1)-(6)",
}

import re

def cheie(a):
    m = re.match(r'^(\d+)(?:\^(\d+))?$', a)
    return (int(m.group(1)), int(m.group(2) or 0))

def articole_din_text(fisier, anexa=""):
    """{eticheta_articol: [linii normative]} pentru corpul legii (anexa="") sau pentru anexa dată."""
    lines = open(fisier, encoding="utf-8").read().split("\n")
    arts, cur, zona = {}, None, (anexa == "")
    for l in lines:
        if l.startswith("§ANEXA§"):
            zona = (anexa != "" and l == "§ANEXA§ " + anexa); cur = None; continue
        if not zona: continue
        m = re.match(r"^Articolul (\d+(?:\^\d+)?)$", l)
        if m: cur = m.group(1); arts.setdefault(cur, []); continue
        if cur and not l.startswith("§NOTA§") and not l.startswith("## "): arts[cur].append(l)
    return arts

def articole_cerute(spec, existente):
    """Extinde „1-3, 5, 9^1-11" în lista de etichete, folosind etichetele care există în text."""
    want = []
    for part in [p.strip() for p in spec.split(",")]:
        if "-" in part:
            a, b = part.split("-"); ka, kb = cheie(a), cheie(b)
            want += [x for x in existente if ka <= cheie(x) <= kb]
            for e in (a, b):
                if e not in existente: want.append(e)
        else:
            want.append(part)
    out, seen = [], set()
    for w in want:
        if w not in seen: seen.add(w); out.append(w)
    return out

def tematica():
    """Întoarce {cheie_bib: (fisier, anexa, [articole cerute existente], [lipsă], [abrogate])}."""
    import os
    baza = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "legislatie")
    rez = {}
    for k, (anexa, spec) in BIB.items():
        fis = os.path.join(baza, k.split("#")[0])
        arts = articole_din_text(fis, anexa)
        exist = sorted(arts, key=cheie)
        want = articole_cerute(spec, exist)
        lipsa = [w for w in want if w not in arts]
        abrog = [w for w in want if w in arts and (not arts[w] or re.match(r"^\s*(\(\d+\)\s*)?Abrogat", arts[w][0]))]
        rez[k] = (k.split("#")[0], anexa, [w for w in want if w in arts], lipsa, abrog, arts)
    return rez

if __name__ == "__main__":
    tot = 0
    for k, (fis, anexa, want, lipsa, abrog, arts) in tematica().items():
        nchar = sum(len(x) for w in want for x in arts[w])
        tot += nchar
        print("%-62s cerute=%3d lipsă=%s abrogate=%s caractere=%6d" % (k, len(want), lipsa, abrog, nchar))
    print("total caractere normative în tematică:", tot)
