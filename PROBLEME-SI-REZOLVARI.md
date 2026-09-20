# Probleme găsite și cum au fost rezolvate

Sesiune din 20.09.2026, pe ramura `analiza_typekey`. Punctul de plecare: banca de 600 de
întrebări era deja verificată pe trei straturi automate plus o verificare adversarială
manuală, iar toate raportau „trec". Documentul de față adună tot ce a ieșit la iveală
dincolo de asta, inclusiv greșelile făcute pe parcurs, fiindcă ele au fost cele mai
instructive.

Raportul de calibrare cu cifrele brute: [`tools/CALIBRARE-typesafe.md`](tools/CALIBRARE-typesafe.md).

**Rezumat:** 5 defecte reale în banca publicată (reparate), 1 cauză-rădăcină în
documentație (reparată), 4 capcane în construcția stării și 4 greșeli de design al
judecăților (toate reparate), 3 probleme de infrastructură (reparate). Verificarea
independentă a celor 505 chei cu răspuns unic nu a găsit nicio cheie greșită.

---

## A. Defecte în produs

### A1. Cinci explicații trimiteau la varianta greșită — **reparat**

**Simptom.** Explicațiile descriau distractorul prin poziție: „Varianta a doua inversează
regula cu excepția", „Primele trei variante reproduc lit. a), c) și h)".

**De ce e o eroare.** `asambleaza.py` amestecă variantele determinist la asamblare, dar nu
rescrie explicațiile. Poziția din explicație rămâne cea dinainte de amestec.

**Dovadă concretă (L360-102).** Explicația spunea „Varianta a patra contrazice principiul
obligativității". În banca publicată, a patra variantă este „Principiul imprescriptibilității",
care se află în `corecte: [0, 2, 3]`. Cursantul citea că una dintre variantele **corecte**
este cea greșită.

**Afectate.** L360-102, L360-113, L360-132, L223-C01, CM-310.

**Rezolvare.** Toate cinci descriu acum varianta prin conținut. Varianta vizată a fost
determinată din ordinea pre-amestec din `tools/nou/*.json`, iar corectura s-a aplicat
identic în `intrebari.js` și în fișierele sursă, ca să rămână consistente. `sw.js` a trecut
la `grile-ru-v3`, altfel service worker-ul ar fi servit explicațiile vechi din cache.

**Verificare.** `verifica_tot.sh` trece pe toate cele 5 straturi; tiparul pozițional e zero
în toată banca; poarta semantică pe cele 5 reparate dă 0 REVIZUIT.

---

## B. Cauza-rădăcină

### B1. README-ul documenta o verificare care nu exista — **reparat**

**Simptom.** README descria `valideaza.py` ca verificând „schema aplicației, unicitate,
**fără referiri la poziția variantelor**". Ultima parte nu era implementată nicăieri.

**Consecință.** Exact acest contract nescris în cod a lăsat să treacă cele cinci defecte de
la A1 — prin toate straturile automate *și* prin verificarea adversarială umană, fiindcă
toată lumea presupunea că altcineva verifică.

**Rezolvare.** Verificarea e implementată (`check_semantic.py --doar-pozitionale`, regex
determinist, fără cheie API), rulează ca pasul 4 din `verifica_tot.sh`, iar README descrie
acum ce se întâmplă efectiv.

**Lecție.** Un contract scris doar în documentație nu prinde nimic. Merită căutate și
celelalte afirmații din README/SPEC care descriu verificări — și confruntate cu codul.

---

## C. Capcane în construcția stării

Toate patru sunt greșeli ale mele în `check_semantic.py`, dar fiecare a produs inițial ceea
ce părea o eroare a modelului. **În toate cazurile modelul răspunsese corect la ce i se
arătase; dovada lipsea din stare.**

### C1. Liniile `§NOTA§` erau eliminate — **reparat**

`bibliografie.articole_din_text()` filtrează notele portalului. Acolo scrie însă că un
alineat a fost abrogat („se abrogă prevederile referitoare la pensii cuprinse în…").
Cât timp lipseau, judecata „temeiul e abrogat" dădea **0.09** pe L80-131, un defect real.
Cu notele în stare: **0.85**, prins. Adăugat `_note_articol()`, care le citește separat și
le marchează explicit drept note, nu text normativ.

### C2. Articolele invocate de explicație lipseau — **reparat**

SPEC §4.4 **cere** ca explicația să arate din ce articol vine valoarea fiecărui distractor.
Fără acele articole în stare, fiecare astfel de frază corectă ieșea „neverificabilă":
**39 din 72** de întrebări marcate degeaba. Codul extrage acum articolele numite în
explicație (regex) și le aduce în stare.

### C3. Articolele-dovadă erau trunchiate — **reparat**

Plafon de 2500 de caractere aplicat și articolelor invocate. La L80-114, art. 20^1 alin. (4)
— „50% … nu mai mult de 9 luni" — cădea după tăietură, ceea ce a produs o **alarmă falsă cu
p=0.95**. Plafonul pentru articolele-dovadă e acum 9000.

### C4. Notele erau colectate peste granița de capitol — **reparat**

`_note_articol()` se oprea doar la următorul „Articolul N", deci nota „Cap. V a fost
abrogat" ajungea în notele art. 13 din H.G. 52/2011. Se oprește acum și la titlurile `## `.
(Semnalul a rămas totuși 0.78 după reparație — vezi D4: acolo greșea modelul.)

---

## D. Greșeli de design al judecăților

### D1. Întrebare compusă — **reparat**

`enunt_autonom` întreba două lucruri deodată: „numește actul **și**, dacă e cazul,
precizează categoria de personal?". Dădea 0.30 pe un enunț care începe literal cu „Potrivit
Legii nr. 80/1995". Spart în `numeste_actul` și `categorie_ambigua`, fiecare o singură
judecată coerentă.

### D2. Judecată agregată pe un text lung — **reparat**

`absolut` întreba dacă explicația conține *vreo* afirmație absolută nesusținută — o singură
judecată peste 4–8 fraze. Media pe întrebările defecte era 0.28, pe cele bune 0.29: zero
putere discriminativă. Explicația se verifică acum **frază cu frază**, fiecare cu propriul
Choice (susține / contrazice / nu spune nimic).

### D3. Judecăți independente pe variante, în loc de comparative — **reparat**

Cea mai importantă. Patru întrebări separate de forma „textul susține varianta asta?" sunt
nesigure pe distincții juridice fine, și greșesc **cu încredere mare**:

| Întrebare | judecăți per-variantă | adevărul din lege |
|---|---|---|
| L80-203 | distractorul C susținut **p=0.93**, cheia D contrazisă p=0.08 | art. 35 alin. (3), verbatim: „6 luni … prescripție, … 2 ani … decădere" — cheia D e corectă |
| L223-113 | cheia C contrazisă p=0.11, distractorul A apărabil | art. 11 alin. (1): H.G. 1.294/2001 = cadre militare, 1.822/2004 = polițiști — cheia C e corectă |

Tiparul: modelul **inversează perechile** (care termen merge cu care regim, care act pentru
care categorie). Rezolvarea nu a fost un prag, ci o altă formă de întrebare: un singur
`Choice` ale cărui criterii sunt chiar variantele, tot fără cheie în stare, unde variantele
**concurează între ele**. Pe ambele cazuri alege cheia corectă cu încredere 1.00.

Validare: **124 de întrebări `unic`** din loturile de calibrare, pre- și post-reparație →
124 acorduri, 0 dezacorduri; **24 de chei mutate deliberat** pe un distractor → 24/24 prinse,
încredere medie 0.99. Judecățile per-variantă au rămas doar ca semnal de triaj.

### D4. Semnal folosit peste ce poate susține — **reparat**

`abrogat` nu separă singur abrogarea de modificare: 0.78–0.81 pe articole doar modificate,
0.84–0.98 pe cele abrogate. Poarta cere acum **și** o notă de abrogare găsită determinist în
`§NOTA§`. Codul găsește dovada, modelul o interpretează. Cele două întrebări-capcană permise
de SPEC §1 (art. 94^1 din L80/1995, art. 3^1 din H.G. 1867/2005) sunt pe o listă de excepții.

### D5. Granularitate prea mare pentru trimiteri — **reparat**

La L80-328, cheia „prin demisie" cerea să știi că lit. h) din art. 85 înseamnă demisie.
Cu articolul 85 întreg în stare, modelul tot rata: p_sustine=0.07. `alineate.py` descompune
articolul pe alineate și litere și **rezolvă trimiterile până la literă** — „art. 85 alin. 1
lit. g), h), j)…" devine câmpuri numite cu textul exact. Cheia a urcat la **0.98**.
Pe banca întreagă se rezolvă 1.850 de astfel de trimiteri.

---

## E. Greșeli de metodă (ale mele)

### E1. Calibrare pe un set prea mic — **corectat prin rerulare**

Primele 72 de întrebări au dat „precizie 4/4" și am raportat-o ca atare. Pe 600 nu s-a
generalizat: 27 de semnalări, din care toate cele 3 verificate în lege erau false. Motivul
retroactiv: pe cele 72, semnalele câștigătoare fuseseră deterministe (referiri poziționale)
plus o abrogare — judecățile per-variantă nu produseseră **niciun** adevărat pozitiv nici
acolo. Nu se vedea, fiindcă nu exista nicio cheie greșită în setul de calibrare.

**Lecție.** Un set de validare fără pozitivi nu validează detecția. De aceea s-au adăugat
cheile mutate deliberat.

### E2. Contaminarea judecății prin stare — **evitat prin design**

Explicația argumentează de ce fiecare distractor e greșit. Dacă ar sta în aceeași stare cu
întrebările despre variante, ar suprima exact semnalul „distractor apărabil". De aceea se
fac **două cereri** per întrebare: una fără cheie și fără explicație, una cu ele.

### E3. Cheia API tipărită în transcript — **de rotit**

La prima verificare am folosit un fallback de shell care a tipărit valoarea cheii, nu doar
lungimea ei. Nu a plecat nicăieri din sesiune, dar cheia a rămas în transcript. Recomandare:
rotire din console.typesafe.ai.

---

## F. Infrastructură

| Problemă | Rezolvare |
|---|---|
| `typesafe-sdk` lipsea, iar Python 3.10 de pe Mac n-are certificate SSL | venv la `tools/.venv-ts` (SDK-ul aduce `truststore`, deci HTTPS merge) |
| O cerere picată arunca tot lotul din `ThreadPoolExecutor.map` | fiecare întrebare e învelită în try/except; eroarea devine o judecată cu `eroare`, raportată ca REVIZUIT |
| `verifica_tot.sh --semantic` rula cu `python3` de sistem, fără SDK | scriptul alege `./.venv-ts/bin/python` dacă există |

---

## G. Stare finală

**Banca publicată, după reparații** (600 de întrebări; rularea completă a durat 69 s,
6,33M tokens, 0 cereri picate; judecățile celor 5 întrebări reparate au fost reluate după
corectură):

| | |
|---|---|
| REVIZUIT | **0** |
| INCERT (coadă de triaj) | 91 |
| OK | 509 |
| chei `unic` verificate independent | **505 / 505 acord, 0 dezacorduri** |

Coada de 91 e dominată de încredere scăzută pe câte o variantă și de fraze din explicație
care nu se pot verifica din temeiul citat — în mare parte explicații corecte care trimit la
legi din afara corpusului. E o listă de triaj, nu o listă de erori.

**Ce rulează automat, gratuit, la fiecare `verifica_tot.sh`:** schema, citatele verbatim,
articolul din tematică, **referirile poziționale**, distribuția pe teste.

**Ce rulează la cerere, cu `--semantic`:** poarta completă (~70 s pe banca întreagă, cere
`TYPESAFE_API_KEY`). Nu pornește niciodată singură.

**Ce rămâne de făcut:** un merge al ramurii `analiza_typekey` în `main` și un push —
`main` n-a fost atins și nimic nu a fost publicat.

---

## H. Ce merită reținut dincolo de proiect

1. **Aproape fiecare „eroare a modelului" a fost o dovadă lipsă din stare.** Patru din cinci
   cazuri investigate s-au dovedit a fi construcția stării, nu judecata. Înainte de a
   reformula o întrebare, merită verificat ce vede efectiv modelul.
2. **Forma întrebării contează mai mult decât pragul.** Aceeași materie, aceeași stare:
   judecăți independente → alarme false cu p≥0.9; o singură judecată comparativă → 505/505
   corect. Niciun prag n-ar fi salvat prima variantă.
3. **Codul găsește, modelul judecă.** Trimiterile rezolvate cu regex, notele de abrogare
   găsite determinist, referirile poziționale prinse cu un tipar de text — partea care a
   găsit cele mai multe defecte reale n-a costat niciun token.
4. **Politica separată de judecăți se plătește.** Judecățile brute stau în
   `tools/verificari/*-ts.json`; toate re-etajările de mai sus s-au aplicat cu `--din`,
   fără să reruleze inferența.
