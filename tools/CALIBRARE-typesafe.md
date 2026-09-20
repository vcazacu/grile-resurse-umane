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

---

# Rularea pe toată banca (600 de întrebări)

20.09.2026, `check_semantic.py ../intrebari.js`. **600 de întrebări în 68 de secunde,
5,25 milioane de tokens, 0 cereri picate.** Judecățile brute: `verificari/intrebari-ts.json`.

## Precizia de la calibrare NU s-a generalizat

Cu politica de la calibrare, rularea a dat 27 REVIZUIT. Am verificat în textul legii
toate cele 3 cazuri cu semnal dublu (cheia contrazisă *și* un distractor susținut) —
adică exact cazurile care susțineau că răspunsul publicat e greșit:

| Întrebare | ce spunea poarta | ce spune legea |
|---|---|---|
| L80-203 | distractorul C susținut (p=0.93), cheia D contrazisă (p=0.08) | art. 35 alin. (3): „termenul de 6 luni este termen de prescripție, iar cel de 2 ani este termen de decădere" — **cheia D e corectă**, C spune invers |
| L223-113 | cheia C contrazisă (p=0.11), distractorul A apărabil | art. 11 alin. (1): H.G. 1.294/2001 = cadre militare, H.G. 1.822/2004 = polițiști — **cheia C e corectă**, A e inversarea |
| L80-328 | cheia C nesusținută (p=0.07) | art. 85 lit. h) = „prin demisie", inclusă în lista de excepții din art. 90 alin. (2) — **cheia C e corectă** (art. 85 era în stare) |

**Trei din trei verificate sunt alarme false.** Tiparul e consistent: modelul inversează
perechile (care termen merge cu care regim, care act pentru care categorie) și nu
rezolvă trimiterile la litere, chiar cu articolul-țintă în stare.

Cele 72 de întrebări de la calibrare au dat precizie 4/4 pentru că acolo semnalele
câștigătoare au fost deterministe (referiri poziționale) plus o abrogare — nu judecățile
pe variante, care n-au contribuit cu niciun adevărat pozitiv nici la calibrare.

## Politica re-etajată după dovezi

Judecățile pe variante și pe frazele explicației au coborât din poartă în **coada de
revizuire** (INCERT). Rămân utile ca semnal de triaj, dar nu opresc un build și nu
justifică rescrierea unei chei.

Semnalul `abrogat` nu separă singur abrogarea de modificare (0.78-0.81 pe articole doar
modificate, 0.84-0.98 pe cele abrogate). Poarta cere acum **și** o notă de abrogare găsită
determinist în `§NOTA§` (`nota_abrogare`) — codul găsește dovada, modelul o interpretează.
Cele două întrebări-capcană permise de SPEC §1 (art. 94^1 din L80/1995, art. 3^1 din
H.G. 1867/2005) sunt pe lista `ABROGARE_ASUMATA`.

Rezultat, **fără inferență nouă** (`--din`): **5 REVIZUIT, 97 INCERT, 498 OK.**
Cele 5 sunt exact referirile poziționale verificate manual. Detecția de la calibrare
rămâne intactă (4/4 pe versiunile defecte, 0 pe cele reparate).

## A patra capcană de stare

`_note_articol()` colecta notele peste granița de capitol: „Cap. V a fost abrogat" ajungea
în notele art. 13 din H.G. 52/2011. Reparat (se oprește și la titlurile `## `). Semnalul a
rămas totuși 0.78/0.81 după reparație — deci acolo greșea modelul, nu dovada.

## Bilanț onest

Ce merită legat în `verifica_tot.sh`: **verificarea deterministă a referirilor poziționale**
(gratuită, fără cheie API, 5 defecte reale găsite în banca publicată) și, cu rezerve,
`abrogat` + notă confirmată.

Ce nu merită încă: judecățile pe variante ca poartă. Pe 600 de întrebări produc alarme
false cu p≥0.9 pe distincții juridice fine. Ca listă de triaj pentru un om sau pentru un
verificator adversarial, cele 97 de INCERT rămân utile — dar trebuie citite ca „merită o
privire", nu ca „e greșit".
