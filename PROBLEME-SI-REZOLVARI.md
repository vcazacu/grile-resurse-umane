# Probleme găsite și cum au fost rezolvate

Sesiune din 20.09.2026, pe ramura `analiza_typekey`. Punctul de plecare: banca de 600 de
întrebări era deja verificată pe trei straturi automate plus o verificare adversarială
manuală, iar toate raportau „trec". Documentul de față adună tot ce a ieșit la iveală
dincolo de asta, inclusiv greșelile făcute pe parcurs, fiindcă ele au fost cele mai
instructive.

Raportul de calibrare cu cifrele brute: [`tools/CALIBRARE-typesafe.md`](tools/CALIBRARE-typesafe.md).

**Rezumat:** 5 defecte reale în banca publicată (reparate), 1 cauză-rădăcină în
documentație (reparată), 5 capcane în construcția stării și 6 greșeli de design al
judecăților (toate reparate), 3 probleme de infrastructură (reparate). Verificarea
independentă a celor 505 chei cu răspuns unic nu a găsit nicio cheie greșită — cu
rezervele din secțiunea J. Toate cele 18 pagini de sinteză au fost scrise și verificate:
953 de afirmații, 0 contrazise de textul legii; pe drum, cele două straturi de verificare
au prins **două erori reale în conținut proaspăt scris** (secțiunea G).

**Cost total, estimat din rulările înregistrate: aproximativ 20 de milioane de tokens** —
două treceri complete peste bancă (5,25M și 6,33M), calibrările pe loturile de 72 de
întrebări și pe chei mutate (~3,5M), rulările finale pe cele 18 teme (4,09M) și reluările
lor după corecturi (~1,5M).

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

Toate cinci sunt greșeli ale mele în `check_semantic.py` și `alineate.py`, dar fiecare a produs inițial ceea
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

### C5. Literele se suprascriau în articolele cu subgrupuri — **reparat**

Găsit la verificarea temei 1 din secțiunea „Tematica". `alineate.descompune()` ținea literele
unui alineat într-un dicționar plat. În articolele structurate pe subgrupuri majuscule —
`A. Subofițeri`, `B. Maiștri militari`, `C. Ofițeri` — literele grupului B le suprascriau pe
ale lui A, iar ale lui C pe ale lui B. La art. 2 din Legea 80/1995 modelul primea o listă
amestecată, în care „a)" era „ofițeri cu grade inferioare", iar „d)" și „e)" erau grade de
maistru militar.

**Consecința:** 10 alarme false pe o temă care era corectă, unele cu p=0.92. Fără verificarea
manuală în lege, aș fi „reparat" o pagină care nu avea nimic.

**Rezolvare:** literele se cheie acum cu grupul din care fac parte — `A. a)`, `A^1. b)`,
`C. c)`. Trimiterile la literă simplă (art. 85 lit. h)) funcționează în continuare, fiindcă
acolo nu există subgrupuri.

**Ecou asupra rezultatelor anterioare:** bug-ul exista și la rularea băncii de întrebări.
Nu a schimbat concluzia — judecata comparativă a fost de acord cu cheia la 505 din 505
întrebări `unic` — dar articolele cu subgrupuri majuscule au fost judecate pe o listă
amestecată. O rerulare a băncii ar costa ~6M tokens; merită făcută dacă se modifică oricum
întrebări pe astfel de articole.

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

### D6. Afirmațiile de absență nu aveau unde să meargă — **reparat**

Sintezele spun des „pentru maistru militar principal nu este prevăzut stagiu" sau „art. 96 nu
este în bibliografie". Astfel de afirmații sunt corecte — art. 94 lit. B chiar se oprește la
clasa I — dar întrebarea avea doar trei ieșiri: susține, contrazice, nu spune nimic. Modelul
nu putea alege „susține" (textul nu afirmă nimic despre maistrul principal), așa că alegea
**contrazice**.

**Rezolvare:** o a patra categorie, `absenta_corecta`, descrisă explicit: afirmația susține că
ceva NU este prevăzut, iar textul îi dă dreptate prin chiar lipsa acelui lucru. Plus lista
oficială de articole cerute de tematică în stare, pentru afirmațiile despre bibliografie.

**Efect secundar util:** cu o categorie „nu spune nimic" formulată să acopere și sfaturile de
învățare („citește întrebarea până la capăt"), propozițiile pedagogice se clasifică singure
acolo, în loc să polueze verdictul.

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

### E4. Lecția de la E1, aplicată de la început — **prag calibrat, nu ghicit**

La verificarea tematicii nu am mai raportat un prag înainte de a avea pozitivi. Tema 1 e
corectă, deci setul nu conținea nicio eroare reală. Am plantat 12: cifre schimbate (3 ani → 4
ani), clase de grad (a IV-a → a VI-a), ministere (Apărării → Afacerilor Interne).

| | p(contrazice) |
|---|---|
| afirmații mutate deliberat | **≥ 0.99** la 10 din 12 |
| afirmații verificate manual ca fiind corecte | **≤ 0.76** |

Pragul inițial de 0.50 producea 3 alarme false pe o temă fără erori. La 0.90 separarea e
curată în ambele direcții. Aceasta este singura cifră din tot documentul obținută înainte de
a fi avut nevoie de ea, nu după.

---

## F. Infrastructură

| Problemă | Rezolvare |
|---|---|
| `typesafe-sdk` lipsea, iar Python 3.10 de pe Mac n-are certificate SSL | venv la `tools/.venv-ts` (SDK-ul aduce `truststore`, deci HTTPS merge) |
| O cerere picată arunca tot lotul din `ThreadPoolExecutor.map` | fiecare întrebare e învelită în try/except; eroarea devine o judecată cu `eroare`, raportată ca REVIZUIT |
| `verifica_tot.sh --semantic` rula cu `python3` de sistem, fără SDK | scriptul alege `./.venv-ts/bin/python` dacă există |

---

## G. Verificarea paginilor de sinteză („Tematica")

Aceeași metodă, alt produs: fiecare frază din paragrafe și fiecare capcană devine o afirmație
judecată separat contra textului integral al articolelor invocate de secțiune, descompus pe
alineate, cu trimiterile rezolvate până la literă și cu lista de articole cerute de tematică
în stare. `tematica_build.py` confirma deja citatele verbatim; ce lipsea era verificarea că
sinteza **rezultă** din ele.

**Tema 1 („Gradele militare și stagiile minime în grad") era corectă.** 101 afirmații:

| | |
|---|---|
| confirmate de textul legii | 97 |
| afirmații de absență, corecte | 2 |
| sfaturi de învățare (nu afirmații despre lege) | 2 |
| **contrazise** | **0** |

Drumul până la acest verdict a trecut prin C5 (10 alarme false din cauza literelor
suprascrise), D6 (afirmațiile de absență) și E4 (pragul calibrat pe erori plantate). Niciuna
dintre cele 10 alarme inițiale nu era o problemă a paginii.

**Temele 2–18 au fost scrise în aceeași sesiune, cu poarta pornită la fiecare pas.** Bilanț
pe toate cele 18: **953 de afirmații judecate, 0 contrazise; 484 de citate confirmate
verbatim din 484.** Cele 7 „neverificabile" rămase sunt sfaturi pedagogice sau comparații
între două legi diferite — clasificate corect, fiindcă a doua lege nu era în stare.

### G1. Două erori reale, prinse înainte de publicare

Sunt cele mai importante două rânduri din document, fiindcă sunt singurele în care flagul
**a fost** dovada — și amândouă erau în text scris cu atenție, în aceeași zi.

| Unde | Ce am greșit | Cine a prins |
|---|---|---|
| tema 9, art. 17 alin. (5) din Codul muncii | am copiat citatul dintr-un afișaj trunchiat și i-am completat finalul din memorie („…contractul colectiv de muncă." în loc de „…aplicabil.") | `tematica_build.py`, verificarea verbatim |
| tema 13, art. 49 alin. (1) din Legea 223/2015 | am scris că pensia de urmaș pe tot timpul vieții cere 15 ani de căsătorie; legea cere **trei** condiții cumulative — a treia, venituri sub 35% din câștigul salarial mediu brut, lipsea | `check_tematica.py`, poarta semantică (p=0.90) |

Cele două straturi prind lucruri diferite: primul nu vede fondul, al doilea nu vede forma
citatului. Prima eroare era corectă ca fond și greșită ca literă; a doua, invers. Niciuna
n-ar fi fost prinsă de celălalt strat.

La a doua, semnalul a apărut abia după ce am adăugat art. 49 la temeiurile secțiunii: cât
timp articolul lipsea din stare, afirmația ieșea doar „neverificabilă". Este aceeași lecție
ca la C1–C5, dar de data asta cu final bun — diferența dintre „nu știu" și „e greșit" a
stat în dovada pusă la dispoziție.

**Morala repetată a treia oară:** flagul nu este dovada. De fiecare dată când poarta a arătat
cu degetul, primul pas util a fost să deschid legea, nu fișierul acuzat. Dar G1 arată și
reversul: când dovada e completă, flagul merită luat în serios.

---

## H. Stare finală

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

**Tematica:** 18 din 18 teme scrise, construite și verificate; `sw.js` la `grile-ru-v18`;
indexul nu mai are nicio temă „în pregătire". Fiecare temă are commit propriu.

**Ce rămâne de făcut:** un merge al ramurii `analiza_typekey` în `main` și un push —
`main` n-a fost atins și nimic nu a fost publicat.

---

## I. Ce merită reținut dincolo de proiect

1. **Aproape fiecare „eroare a modelului" a fost o dovadă lipsă sau stricată în stare.**
   Cinci capcane de construcție a stării, față de trei greșeli reale de judecată ale
   modelului. Înainte de a reformula o întrebare — și cu atât mai mult înainte de a
   „repara" conținutul acuzat — merită tipărit exact ce vede modelul.
2. **Forma întrebării contează mai mult decât pragul.** Aceeași materie, aceeași stare:
   judecăți independente → alarme false cu p≥0.9; o singură judecată comparativă → 505/505
   corect. Niciun prag n-ar fi salvat prima variantă.
3. **Codul găsește, modelul judecă.** Trimiterile rezolvate cu regex, notele de abrogare
   găsite determinist, referirile poziționale prinse cu un tipar de text — partea care a
   găsit cele mai multe defecte reale n-a costat niciun token.
4. **Un prag fără pozitivi nu e un prag.** De două ori am avut un set de validare fără
   nicio eroare reală în el. Prima dată am raportat „precizie 4/4" și nu s-a generalizat;
   a doua oară am plantat 12 erori înainte de a alege pragul. Erorile plantate sunt ieftine
   și schimbă complet ce știi despre propria poartă.
5. **Politica separată de judecăți se plătește.** Judecățile brute stau în
   `tools/verificari/*-ts.json`; toate re-etajările de mai sus s-au aplicat cu `--din`,
   fără să reruleze inferența.

---

## J. Limite cunoscute — unde să nu te bazezi pe verificare

Secțiunile de mai sus pot lăsa impresia unei plase fără găuri. Nu e. Acestea sunt găurile
pe care le știu; cele pe care nu le știu nu sunt aici.

1. **Cele 95 de întrebări `multiplu` nu au niciun semnal de încredere pentru cheie.**
   Judecata comparativă — singura care s-a separat curat — se pune doar la `unic`, unde o
   singură variantă concurează cu celelalte. La `multiplu` rămân judecățile per-variantă,
   care au produs 13 alarme false pe bancă. 16% din bancă e verificată doar de straturile
   deterministe și de verificarea adversarială umană de la 18.09.2026.

2. **„505/505" a fost obținut cu bug-ul C5 activ.** Articolele cu subgrupuri majuscule
   (A./B./C.) au fost judecate pe o listă de litere amestecată. Rezultatul nu s-a schimbat
   la temele verificate după reparație, dar banca n-a fost rerulată — costă ~6M tokens.

3. **Detecția cheilor greșite e validată doar pe cazul ușor.** Cele 24 de mutante au avut
   cheia mutată pe un distractor oarecare. O cheie *subtil* greșită — distractorul aproape
   corect, diferența într-un termen sau într-o excepție — nu a fost testată. Aceasta este
   exact clasa de erori din D3, unde modelul greșea cu p≥0.9, și nu există nicio dovadă că
   judecata comparativă o prinde.

4. **Orice afirmație despre o lege din afara secțiunii iese „neverificabilă".** Comparațiile
   între două acte (frecvente în temele 13–14 și 15) și trimiterile la legi din afara
   corpusului (Legea 263/2010, Codul fiscal) nu pot fi nici confirmate, nici contrazise.
   Cele 91 de INCERT din bancă sunt în bună parte de acest tip — nu erori, dar nici verificate.

5. **Pragurile sunt calibrate pe seturi mici, dintr-un singur domeniu.** 72 de întrebări,
   24 de mutante, 12 afirmații plantate într-o singură temă. Separarea a fost curată de
   fiecare dată, dar cifrele 0.80 / 0.90 nu au fost testate pe alt corpus juridic.

6. **Verificarea semantică nu înlocuiește citirea legii.** În toată sesiunea, fiecare
   verdict care a contat a fost confirmat manual în text înainte de a fi acționat — inclusiv
   cele două din G1. Poarta reduce ce trebuie citit; nu elimină cititul.
