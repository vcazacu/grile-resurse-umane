# Calibrarea stratului 4 (semantic) — `check_semantic.py`

Rulat pe 20.09.2026, model Jev (TypeSafe System One), SDK `typesafe-sdk` 0.7.0.

## Cum s-a măsurat

Rapoartele de pe 18.09.2026 spun că verificarea adversarială a găsit 2 chei greșite
și ~60 de întrebări „SUSPECT" din 683, toate reparate ulterior. Fișierele finale
sunt deci curate — rulate singure, ar fi măsurat doar rata de alarme false.

Adevărul de referință s-a reconstituit din arhiva pre-reparație `nou-20260918-0109.tgz`:
orice întrebare care diferă între arhivă și fișierul final a fost semnalată și reparată
de verificatorul adversarial. Pe loturile cerute:

| Lot | întrebări | reparate după verificare (= defecte) |
|---|---|---|
| L80-1 | 42 | 6 (L80-114, 120, 128, 129, **131**, 134) |
| A6-2  | 30 | 3 (A6-215, 218, 225) |

Poarta a fost rulată de două ori: pe versiunile **pre-reparație** (trebuie să semnaleze)
și pe cele **finale** (trebuie să tacă).

## Rezultat

| | pre-reparație | final (control) |
|---|---|---|
| REVIZUIT | **4** (L80-120, 128, 129, 131) | **0** |
| INCERT | 6 | 7 |
| OK | 62 | 65 |

- **Precizie 4/4.** Toate cele 4 semnalări sunt defecte reale din setul de referință;
  zero alarme false pe cele 144 de treceri (72 bune + 72 defecte).
- **Acoperire 4/9** din defectele pe care le-a găsit verificarea adversarială umană.
- Pe corpusul reparat poarta tace complet — semnalul urmărește defectul, nu întrebarea.
- 72 de întrebări în ~9 secunde (6 fire), ~530.000 tokens.

## Ce prinde și ce nu

Prinse:
- **referiri la poziția variantei** în explicație (L80-120, 128, 129) — determinist, regex,
  fără apel de rețea. `asambleaza.py` amestecă variantele, deci „a doua variantă" devine
  falsă în aplicație.
- **temei abrogat** (L80-131, p=0.85) — dar numai după ce liniile `§NOTA§` au ajuns în stare
  (vezi mai jos).

Nescăpate, dar neprinse: A6-215, 218, 225 și, după corecturi, L80-114 și 134. Sunt defecte
de nuanță în explicație, la nivel de **alineat** (ex. „termenul de 3 ani apare la art. 21
alin. (11) și (13)"), în timp ce starea se construiește la nivel de **articol**. Verificarea
lor ar cere alineatul ca unitate de dovadă.

## Trei capcane găsite la calibrare (toate în construcția stării, nu în model)

1. `bibliografie.articole_din_text()` elimină liniile `§NOTA§` — exact acolo scrie că un
   alineat a fost abrogat. Cât timp lipseau, `abrogat` dădea ~0.09 pe L80-131. Cu ele: 0.85.
2. Explicațiile bune citează, cum cere SPEC §4.4, articolul din care vine fiecare distractor.
   Fără acele articole în stare, fiecare astfel de frază ieșea „neverificabilă" — 39 din 72
   de întrebări marcate INCERT degeaba. Codul le extrage acum cu regex din explicație și le
   aduce în stare (`articole_invocate`).
3. Articolele-dovadă trunchiate la 2500 de caractere au produs o **alarmă falsă cu p=0.95**
   (L80-114: art. 20^1 alin. (4) — „50% ... nu mai mult de 9 luni" — căzuse după tăietură).
   Modelul răspunsese corect pe ce i se arătase. Plafonul e acum 9000 pentru ele.

Concluzia practică: fiecare eșec al porții a fost o dovadă lipsă din stare, nu o judecată
greșită. Merită verificat întâi ce vede modelul, abia apoi reformulată întrebarea.

## Cum se folosește

```bash
python3 check_semantic.py nou/L80-1.json              # rulează (cere TYPESAFE_API_KEY)
python3 check_semantic.py --din verificari/L80-1-ts.json   # re-aplică politica, fără inferență
python3 check_semantic.py --doar-pozitionale ../intrebari.js  # offline, fără cheie API
```

Judecățile brute se salvează în `verificari/<lot>-ts.json`; pragurile stau separat, în
`verdict()`, și se pot schimba cu `--prag-<nume>` fără să reruleze inferența.

## De reparat în banca publicată

`--doar-pozitionale ../intrebari.js` găsește **5 întrebări** ale căror explicații trimit la
poziția variantei: L360-102, L360-113, L360-132, L223-C01, CM-310. Exemplu verificat:
la L360-102 explicația spune „Varianta a patra contrazice principiul obligativității", dar
după amestec a patra variantă este „Principiul imprescriptibilității" — una dintre cele
corecte (`corecte: [0, 2, 3]`). Cursantul primește exact informația inversă.

Până la rescrierea lor, verificarea nu a fost legată în `verifica_tot.sh`, ca să nu pice
build-ul existent.
