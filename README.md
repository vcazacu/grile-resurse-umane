# Grile — Resurse Umane (SIE)

Aplicație de tip quiz pentru pregătirea examenului de Resurse Umane, construită
pe legislația în formă consolidată la zi, descărcată direct de pe portalul
legislatie.just.ro (nu din PDF-uri).

Bateria are **30 de teste a câte 20 de întrebări** (600 în total, dintre care
maximum 4 cu răspunsuri multiple pe test). Scorul cel mai bun al fiecărui test
se salvează local în browser (localStorage) și apare pe grila de teste.

Tematica oficială a examenului are 18 teme, acoperite din 9 acte normative
(Legea 80/1995, Legea 1/1998, Codul muncii, Legea 223/2015, Legea 360/2023,
Legea-cadru 153/2017 + Anexa VI, OUG 111/2010, Normele HG 52/2011,
HG 1867/2005). Lista exactă de articole cerute e în `tools/bibliografie.py`
(`BIB`, `RESTRICTII`).

### Sursele legislative

Fiecare fișier din `../legislatie/*.txt` a fost descărcat cu `tools/descarca.py`
și are pe prima linie un antet `§SURSA§` cu id-ul din portal și data
consolidării folosite. Notele de modificare ale portalului sunt marcate
`§NOTA§` în text și nu sunt folosite ca text normativ, doar ca istoric în
explicații.

| Act normativ | Consolidarea folosită |
|---|---|
| Legea nr. 80/1995 — statutul cadrelor militare | 28.03.2024 |
| Legea nr. 1/1998 — organizarea și funcționarea SIE (republicată) | 22.04.2017 |
| Legea nr. 53/2003 — Codul muncii | 27.04.2026 |
| Legea nr. 223/2015 — pensiile militare de stat | 01.01.2024 |
| Legea nr. 360/2023 — sistemul public de pensii | 28.07.2025 |
| Legea-cadru nr. 153/2017 — salarizarea bugetară (+ Anexa nr. VI) | 01.01.2026 |
| O.U.G. nr. 111/2010 — concediul pentru creșterea copilului | 19.09.2023 |
| Norme metodologice H.G. nr. 52/2011 (aplicare O.U.G. 111/2010) | 19.09.2023 |
| H.G. nr. 1867/2005 — compensația de chirie | 06.05.2020 |

## Cum o folosești

Deschide `index.html` cu dublu-click — merge în orice browser, pe telefon,
tabletă sau calculator, **complet offline**, fără server și fără instalare.

Pe telefon: copiază folderul `quiz-app` (AirDrop / e-mail / cloud), deschide
`index.html` din aplicația de fișiere, apoi „Adaugă la ecranul principal”
din meniul browserului dacă vrei acces rapid.

## Cum adaugi întrebări

Spre deosebire de un fișier de date editat manual, **`intrebari.js` este
generat** de `tools/asambleaza.py` din `tools/nou/*.json` (neversionate) — nu
se editează direct.

Fluxul de lucru:

1. Întrebările noi se scriu în `tools/nou/<prefix>-<n>.json`, respectând schema
   din `tools/SPEC.md`: `id`, `tip` (`"unic"` sau `"multiplu"`), `intrebare`,
   `variante`, `corecte`, `explicatie`, `sursa` (`act`, `articol`, `citat`,
   `fisier`, opțional `anexa`), `status` (`"ok"` sau `"de verificat"`). Câmpul
   `test` **nu** se completează manual — îl atribuie asamblarea.
2. `tools/asambleaza.py --scrie` validează, aplică cotele pe act (`COTE`),
   selectează uniform pe articole, intercalează proporțional pe cele 30 de
   teste (max. 4 „multiplu”/test) și **amestecă variantele determinist**
   (`random.Random("grile-ru:" + id)`, per întrebare — aplicația însăși nu
   amestecă nimic) — apoi scrie `../intrebari.js`.
3. `tools/verifica_tot.sh` rulează toate verificările automate (vezi mai jos).

**Validare automată:** la fiecare deschidere, `app.js` verifică structura
tuturor întrebărilor (exact 20 pe test, cel mult 4 „multiplu”, câmpuri
complete). Dacă ceva e greșit, pe ecranul principal apare un banner roșu cu
problemele exacte, iar testul nu pornește până nu sunt corectate.

## Tematica — sinteze pe teme

Pe lângă teste, aplicația are o secțiune **Tematica** (`tematica/index.html`, link în
antet): câte o pagină de sinteză pentru fiecare dintre cele 18 teme din tematica
oficială, în același stil ca explicațiile din teste — reguli, termene, excepții și
capcane, fiecare cu temeiul legal citat verbatim din forma consolidată la zi.

Conținutul unei teme stă în `tools/tematica/NN.json` (rezumat, secțiuni cu paragrafe
și temeiuri `{act, articol, citat, fisier}`, capcane, id-urile întrebărilor legate).
`tools/tematica_build.py` verifică fiecare citat contra `../legislatie/*.txt`, generează
paginile HTML și indexul, și actualizează lista de fișiere din `sw.js` pentru offline.
Temele fără fișier de conținut apar în index ca „în pregătire". Fiecare temă trece,
înainte de publicare, și printr-o verificare adversarială independentă a sensului
(nu doar a citatelor).

## Legislația — textele de lege, de citit

Secțiunea **Legislația** (`legislatie/index.html`, link în antet lângă Tematica) redă cele
9 acte normative în text integral consolidat, formatat pentru citit pe telefon: cuprins pe
capitole, câte un bloc pe articol (cu ancoră `#art-N`, `#art-9-1` pentru art. 9^1), alineate,
litere și liniuțe indentate, titlurile marginale ale articolelor, iar notele portalului
(modificări, abrogări, decizii) strânse sub fiecare articol. Implicit se văd doar articolele
cerute în bibliografie (marcate „bibliografie", cu restricția afișată acolo unde există);
comutatorul „Arată toată legea" descoperă restul, iar un salt la un articol ascuns îl
activează singur. Cardurile „Temei legal" din tematica trimit la articolul din lege.

**Trimiterile din text sunt apăsabile.** „prevăzute la art. 36 alin. 1 lit. a)", „potrivit
alin. 1 și 2", „celor prevăzute la lit. a) și b)", intervalele („lit. b)-f)") și grupurile
(„alin. 2^1 paragraful B lit. c)") sunt recunoscute la construire de `tools/trimiteri.py`
(gramatică deterministă, testată în `tools/test_trimiteri.py`); fiecare element trimite la
propriul nivel — articolul, alineatul, litera. La apăsare, sub paragraf se deschide un chenar
cu textul țintei, copiat din aceeași pagină (merge offline, paginile nu cresc), cu „mergi la
text" și „×"; a doua apăsare îl închide, iar trimiterile din chenar sunt la rândul lor
apăsabile. Trimiterile către unul dintre cele 9 acte („art. 12 alin. (5) din ordonanța de urgență" în
Norme, „art. 20^1 din Legea nr. 80/1995", „art. 57 din anexa nr. VI la Legea-cadru nr.
153/2017") trimit la pagina actului respectiv, iar chenarul ia textul din acea pagină cu
`fetch` (e în cache-ul offline); actul se recunoaște din fraza de după trimitere
(`ALIASURI`, plus `ALIASURI_LOCALE` pentru prescurtările valabile doar într-un act). Rămân
text simplu: trimiterile către acte din afara bibliografiei, către ținte inexistente și
literele ambigue (aceeași literă în două grupuri fără grupul numit). Build-ul raportează pe
act câte trimiteri a legat (și câte dintre ele către alt act) / a lăsat / sunt către acte necunoscute.

`tools/legislatie_build.py` parsează `../legislatie/*.txt` (care **nu se modifică** — sunt
sursa de adevăr pentru toate uneltele) pe marcajele existente (`## `, `Articolul N`, `(n)`,
`x)`, `§NOTA§`, `§ANEXA§`), generează paginile și indexul, actualizează lista din `sw.js`
și se oprește cu eroare dacă vreun articol cerut în bibliografie n-are ancoră. La Legea
153/2017 se redă doar Anexa nr. VI (celelalte anexe sunt grile de salarizare). Limitare
cunoscută: tabelele din Legea 360/2023 (art. 48, 51) sunt sparte pe rânduri în sursă și apar
ca bloc monospațiat, nu ca tabel.

## Fișiere

- `index.html` — pagina aplicației (deschide-o pe aceasta)
- `app.js` — logica quiz-ului (nu trebuie atinsă când adaugi întrebări)
- `style.css` — stilurile (design inspirat din shadcn/ui, temă light/dark automată)
- `intrebari.js` — **banca de întrebări** (generată, nu se editează manual)
- `sw.js` — service worker (offline + versiunea cache-ului)
- `tools/tematica_build.py`, `tools/tematica/` — construirea paginilor de tematică
- `tools/legislatie_build.py`, `legislatie/` — paginile de citit ale legislației
- `tools/` — lanțul de generare și verificare:
  - `descarca.py` — descarcă formele consolidate de pe legislatie.just.ro în `../legislatie/`
  - `bibliografie.py` — tematica oficială → articole cerute (`BIB`, `RESTRICTII`)
  - `asambleaza.py` — asamblează `nou/*.json` în `intrebari.js` (cote, teste, amestecare)
  - `valideaza.py` — schema aplicației, unicitate, id-uri și texte nedublate
  - `check_semantic.py --doar-pozitionale` — explicațiile nu trimit la poziția
    variantei („a doua variantă”), fiindcă `asambleaza.py` le amestecă; determinist,
    fără cheie API
  - `check_citat.py` — citatul din `sursa.citat` apare verbatim în sursă (după normalizare)
  - `check_articol.py` — articolul declarat = locul real al citatului + în tematică + restricții pe alineate
  - `acoperire.py` — fiecare articol cerut de bibliografie are cel puțin o întrebare
  - `verifica_tot.sh` — rulează toate verificările de mai sus într-un singur pas;
    cu `--semantic` adaugă poarta semantică de mai jos (cere `TYPESAFE_API_KEY`)
  - `check_semantic.py`, `alineate.py` — poarta semantică (TypeSafe): verifică
    independent cheia fiecărei întrebări cu răspuns unic, temeiurile abrogate și
    explicațiile, frază cu frază, față de textul legii. Rezultate și limite în
    `tools/CALIBRARE-typesafe.md`
  - `SPEC.md` — contractul complet privind schema și sursele
  - `nou/` — întrebările brute înainte de asamblare (neversionate)

## Publicare și actualizare

Aplicația e publicată pe GitHub Pages, din depozitul `vcazacu/grile-resurse-umane`:

**https://vcazacu.github.io/grile-resurse-umane/**

Pe telefon sau tabletă: deschide adresa în browser, lasă pagina să se încarce
complet, apoi „Adaugă la ecranul principal”. Service worker-ul (`sw.js`) salvează
local toate fișierele, așa că de la a doua deschidere aplicația funcționează
**complet fără internet**.

### Când modifici întrebările

La orice modificare a întrebărilor din `tools/nou/*.json`:

1. `python3 tools/asambleaza.py --scrie` — regenerează `intrebari.js`;
2. `bash tools/verifica_tot.sh` — rulează toate verificările automate;
3. incrementează `VERSIUNE` în `sw.js` (`grile-ru-v1` → `v2` etc.).

Fără al treilea pas, dispozitivele care au deja aplicația salvată rămân cu
versiunea veche în memorie, pentru că service worker-ul servește din cache
înaintea rețelei.

Apoi:

```bash
git add -A && git commit -m "Actualizare întrebări" && git push
```

GitHub Pages republică automat în 1–2 minute.

## Acoperirea materiei

Cele 600 de întrebări sunt distribuite pe acte conform cotelor din
`tools/asambleaza.py` (`COTE`), proporțional cu ponderea lor în tematică:

| Act normativ | Întrebări |
|---|---:|
| Legea nr. 80/1995 — statutul cadrelor militare | 115 |
| Legea nr. 53/2003 — Codul muncii | 115 |
| O.U.G. nr. 111/2010 — concediul pentru creșterea copilului | 65 |
| Norme metodologice H.G. nr. 52/2011 | 60 |
| Legea nr. 223/2015 — pensiile militare de stat | 55 |
| Legea nr. 360/2023 — sistemul public de pensii | 55 |
| Legea-cadru nr. 153/2017, Anexa nr. VI (apărare, ordine publică și securitate națională) | 55 |
| H.G. nr. 1867/2005 — compensația de chirie | 45 |
| Legea nr. 1/1998 — organizarea și funcționarea SIE | 20 |
| Legea-cadru nr. 153/2017 — corp (reguli generale de salarizare) | 15 |

Din cele 600: 95 sunt de tip `"multiplu"` (max. 4 per test) și restul 505 de
tip `"unic"`; niciuna nu are `status: "de verificat"` (600/600 „ok”).

Fiecare articol cerut de bibliografie are cel puțin o întrebare — verificat cu
`tools/acoperire.py` (rulează cu exit 0, „ACOPERIRE COMPLETĂ” pe toate cele
10 grupe act/anexă).

## Cum au fost verificate întrebările

Procesul de generare a produs 683 de întrebări brute, verificate în trei
straturi automate, apoi filtrate/selectate la cele 600 finale prin cotele din
`asambleaza.py`:

1. **`tools/check_citat.py`** — citatul din `sursa.citat` apare verbatim în
   fișierul sursă indicat, după normalizarea despărțirilor de rând și a
   diacriticelor.
2. **`tools/check_articol.py`** — articolul declarat în `sursa.articol`
   corespunde locului real al citatului, articolul e în tematica oficială, iar
   restricțiile pe alineate/litere din `RESTRICTII` sunt respectate.
3. **`tools/valideaza.py`** — schema câmpurilor cerută de aplicație, unicitatea
   id-urilor, fără referiri în text la poziția variantelor.
4. **`tools/acoperire.py`** — fiecare articol cerut are cel puțin o întrebare.

Peste acestea, un **al treilea strat de verificare semantică adversarială**:
fiecare din cele 683 de întrebări, grupate în 20 de loturi, a fost dată unui
agent independent (care nu a scris-o), cu sarcina explicită de a *dobori*
cheia — să caute excepții în articolele vecine, distractori apărabili și
afirmații false în explicații. Rezultatul (`raport-adversarial.txt`, prima
trecere): 0 greșeli de cheie confirmate pe loc, dar 2 cazuri notate inițial
„GREȘIT” (un alineat abrogat aplicat greșit la pensii, respectiv un distractor
dintr-un alineat vecin apărabil) și ~60 „SUSPECT” (afirmații secundare absolute
neverificate, trimiteri greșite, distractori cvasi-sinonimi, referiri la
poziția variantelor). Toate au fost reparate de autorul lotului și
re-verificate de același verificator (două loturi au necesitat a doua rundă);
verdictul final: **683/683 OK**. Problemele au fost mereu în explicații sau în
enunțuri, niciodată în cheia de răspuns din forma finală.

În plus, aplicația a fost parcursă automat în browser pe toate cele 30 de
teste publicate: **30/30 cu scor 100%**.
