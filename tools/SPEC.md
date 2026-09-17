# SPEC — generarea întrebărilor de grilă (examen Resurse Umane / SIE)

Acest document este contractul dintre coordonator și agenții care scriu întrebări.
Un agent primește: un act (fișier `.txt` din `legislatie/`), lista articolelor de
acoperit, numărul de întrebări cerut, cota de întrebări „multiplu" și un nume de
fișier de ieșire `tools/nou/<prefix>-<n>.json`. Scrie **incremental** (după fiecare
5 întrebări rescrie fișierul complet) ca să nu se piardă nimic dacă sesiunea se oprește.

## 1. Sursa de adevăr

- Se folosește **exclusiv** textul din `legislatie/<fisier>.txt` (forma consolidată
  la zi de pe legislatie.just.ro, descărcată cu `tools/descarca.py`). Nu se
  folosește nimic din memorie despre lege: dacă memoria și textul diferă, textul
  are dreptate. Dacă un articol nu spune ceva, întrebarea nu se pune.
- Liniile care încep cu `§NOTA§` sunt istoricul modificărilor și notele portalului
  — **nu sunt text normativ**. Nu se citează din ele. Pot fi folosite doar în
  explicație („alineatul a fost modificat prin Legea nr. 259/2019"), fără să
  schimbe ce e în vigoare.
- Liniile `## ...` sunt titluri de capitol/secțiune (orientare). `§ANEXA§ ...`
  marchează începutul unei anexe cu numerotare proprie de articole.
- Un articol al cărui text e „Abrogat." nu produce întrebări despre conținutul
  lui; cel mult o întrebare-capcană „care dintre articole este abrogat", dacă
  abrogarea e în tematică (art. 94^1 din Legea 80/1995, art. 3^1 din H.G. 1867/2005).

## 2. Ce se acoperă (tematica oficială → articole)

| Temă din tematică | Fișier | Articole cerute de bibliografie |
|---|---|---|
| Gradele militare și stagiile minime în grad | 01 Legea 80/1995 | art. 1–6 (grade: art. 2–3), art. 94–95, 97 (stagii minime) |
| Îndatoririle și drepturile cadrelor militare | 01 | art. 7–9^1, 11–15, 17–18, 20^1–21, 23, 26 |
| Interzicerea sau restrângerea exercițiului unor drepturi și libertăți | 01 | art. 28–30 |
| Disciplina militară | 01 | art. 33–35 |
| Proveniența ofițerilor, maiștrilor militari și subofițerilor | 01 | art. 36–41, 42–43 |
| Acordarea gradelor și înaintarea în gradele următoare | 01 | art. 45 **doar lit. a)–f)**, 46, 48, 50–56, 63–64, 68 |
| Degradarea/scoaterea din evidență, aprecierea și promovarea (parțial) | 01 | art. 69–71, 73, 76, 81 |
| Trecerea în rezervă sau direct în retragere | 01 | art. 85–91 |
| Dispoziții finale | 01 | art. 109–110, 112 |
| Organizarea și funcționarea SIE (rol, organizare, conducere, personal, control) | 02 Legea 1/1998 | art. 1–3, 5–9, 13, 14–15, 18, 20 |
| Contractul individual de muncă: încheiere, executare, modificare, suspendare, încetare | 03 Codul muncii | art. 1–2, 10–12, 14, 16 **doar alin. (1)–(3)**, 17, 27–34, 39–52, 54–61, 63–65, 75–77, 81 |
| Tipurile de contract individual de muncă | 03 | art. 82–85 (durată determinată), 103–106 (timp parțial) |
| Timpul de muncă și timpul de odihnă | 03 | art. 111–123, 125–127, 135–139, 141–142, 144–147^1, 149–155, 158 |
| Răspunderea disciplinară a salariaților | 03 | art. 247–252 |
| Sistemul pensiilor militare de stat | 04 Legea 223/2015 | art. 1–3, 6, 9–21, 23–30, 32–35, 38, 42–43, 45, 47–52, 57–58, 81, 84 |
| Sistemul public de pensii | 05 Legea 360/2023 | art. 1–3, 6, 9, 13–15, 25–26, 32, 39, 44–48, 51, 58–62, 66–69, 72–75, 79, 108, 111–116 |
| Salarizarea — reguli generale | 06 Legea-cadru 153/2017 (corp) | art. 7, 10, 14, 15, 20, 21 |
| Salarizarea — familia „apărare, ordine publică și securitate națională" | 06 **Anexa nr. VI** | art. 1–3, 5–6, 7 **doar alin. (1)**, 8, 9 **doar alin. (1)**, 11, 14 **doar alin. (1)**, 15, 15^1, 18–21, 28–29, 58–62, 73–76, 84, 86 **doar alin. (1)–(6)**, 88, 90–93 |
| Concediul și indemnizația pentru creșterea copiilor; stimulentul de inserție | 07 OUG 111/2010 | art. 1–5, 7–9^1, 11–17, 22, 25, 31–33, 35–37 |
| Idem — norme metodologice | 08 Norme H.G. 52/2011 | art. 1–2, 4–8, 9^1, 12–13, 21, 23–26, 32, 36 |
| Compensația lunară pentru chirie (condiții, documente, anchetă socială, încetare) | 09 H.G. 1867/2005 | art. 1–15, 17^2 |

Lista exactă, procesabilă, este în `tools/bibliografie.py` (`BIB`, `RESTRICTII`).
Întrebările din afara acestor articole sunt respinse automat de `check_articol.py`.

## 3. Schema unei întrebări (JSON, într-un array)

```json
{
  "id": "L80-017",
  "tip": "unic",
  "intrebare": "Potrivit Legii nr. 80/1995, ...?",
  "variante": ["...", "...", "...", "..."],
  "corecte": [2],
  "explicatie": "De ce e corect + de ce fiecare distractor e greșit, cu trimiteri la articole.",
  "sursa": {
    "act": "Legea nr. 80/1995 privind statutul cadrelor militare",
    "articol": "art. 20^1 alin. (1)",
    "citat": "fragment verbatim [...] alt fragment verbatim",
    "fisier": "01_Legea_80-1995_statutul_cadrelor_militare.txt"
  },
  "status": "ok"
}
```

- `id`: prefix pe act + număr din 3 cifre; prefixele: `L80`, `L1`, `CM`, `L223`,
  `L360`, `L153`, `A6` (anexa VI), `OUG111`, `HG52`, `HG1867`. Unic în tot proiectul.
- `tip`: `"unic"` (exact 4 variante, exact 1 corectă) sau `"multiplu"` (4 variante,
  2–3 corecte). Câmpul `test` NU se completează — îl pune `asambleaza.py`.
- `sursa.act` — exact una dintre valorile:
  - `Legea nr. 80/1995 privind statutul cadrelor militare`
  - `Legea nr. 1/1998 privind organizarea și funcționarea Serviciului de Informații Externe`
  - `Legea nr. 53/2003 – Codul muncii`
  - `Legea nr. 223/2015 privind pensiile militare de stat`
  - `Legea nr. 360/2023 privind sistemul public de pensii`
  - `Legea-cadru nr. 153/2017 privind salarizarea personalului plătit din fonduri publice`
  - `Legea-cadru nr. 153/2017 (anexa nr. VI – apărare, ordine publică și securitate națională)` — și `"anexa": "Anexa nr. VI"` în `sursa`
  - `O.U.G. nr. 111/2010 privind concediul și indemnizația lunară pentru creșterea copiilor`
  - `Normele metodologice de aplicare a O.U.G. nr. 111/2010 (H.G. nr. 52/2011)`
  - `H.G. nr. 1867/2005 privind compensația lunară pentru chirie a cadrelor militare în activitate`
- `sursa.articol`: începe obligatoriu cu `art. N` (N ca în text: `20^1`), apoi
  `alin. (2)`, `lit. c)` etc. Se scrie articolul **în care se află citatul**.
- `sursa.citat`: text **verbatim** din `.txt` (copiat, nu rescris), maximum ~600
  de caractere; fragmentele sărite se marchează cu ` [...] `; toate fragmentele
  din același articol. Fără citate din `§NOTA§`.
- `status`: `"ok"`; `"de verificat"` doar dacă textul e ambiguu/contradictoriu,
  caz în care explicația descrie problema în loc să inventeze un răspuns.

## 4. Reguli de calitate (verificate de un agent adversarial, care NU a scris întrebarea)

1. **Un singur răspuns corect** la `unic`: niciun distractor nu poate fi apărat
   ca fiind și el corect, nici printr-o excepție din alt alineat/articol vecin.
   Caută explicit excepțiile înainte de a scrie cheia.
2. **Distractori plauzibili**: valori, termene, procente, organe, categorii reale
   din **aceeași lege** (sau din legea „pereche": Legea 223/2015 vs. 360/2023,
   OUG 111/2010 vs. normele), dar cu alt rol. Nu distractori absurzi.
3. **Enunț autonom**: numește actul („Potrivit Legii nr. 223/2015, ...") și, dacă
   e cazul, categoria de personal (cadre militare în activitate / în rezervă /
   salariați / funcționari publici cu statut special). Regimul cadrelor militare
   diferă de cel al salariaților (Codul muncii) — întrebarea spune despre care
   vorbește.
4. **Explicația** (4–8 propoziții): de ce e corect răspunsul, cu articolul; de ce
   e greșit fiecare distractor, cu articolul de unde vine valoarea lui; capcana
   tipică de examen, dacă există (termen schimbat prin modificare recentă,
   excepție pe categorii).
5. **Fără întrebări triviale de lexic** („cum se numește legea...") și fără
   întrebări despre numere de Monitor Oficial, date de publicare sau istoricul
   modificărilor. Se testează norma în vigoare.
6. **Nivelul de examen**: termene, condiții cumulative (multiplu!), competențe
   (cine aprobă/decide), cuantumuri, limite, excepții, enumerări.
7. **Acoperire**: fiecare articol cerut primește cel puțin o întrebare; articolele
   lungi cu multe alineate (ex. art. 9 și 21 din Legea 80/1995, art. 39 din Codul
   muncii, art. 2 din OUG 111/2010) primesc mai multe. Nu se repetă aceeași idee
   cu formulare diferită.
8. **Restricțiile din bibliografie** (`RESTRICTII`): la art. 45 din Legea 80/1995
   doar lit. a)–f); la art. 16 din Codul muncii doar alin. (1)–(3); la art. 7, 9,
   14 din Anexa VI doar alin. (1); la art. 86 din Anexa VI doar alin. (1)–(6).
   Restul alineatelor NU sunt în tematică.

## 5. Capcane cunoscute ale materiei (de verificat în text înainte de a scrie)

- **Legea 80/1995**: gradele din art. 2 au fost reașezate (alin. (2) vs. (2^1) —
  se folosește lista în vigoare, nu cea veche); art. 20^1 (compensația pentru
  chirie) a fost modificat în 2019 și 2020; art. 94^1 este abrogat; stagiile
  minime în grad (art. 94–95) au excepții pe categorii; art. 45 are litere peste
  f) care nu sunt în tematică.
- **Legea 1/1998**: forma republicată (2000) — numerotarea e cea republicată;
  atenție la organele cu rol de conducere/coordonare/control (CSAT, Parlament,
  comisia comună) — cine face ce.
- **Codul muncii**: multe articole modificate prin Legea nr. 283/2022 (informarea
  salariatului art. 17, perioada de probă art. 31–33, preaviz art. 75, concedii
  art. 144–147^1 — art. 147^1 este concediul suplimentar pentru fertilizare
  in vitro); art. 35–38 și 62 NU sunt în bibliografie deși sunt în capitolele
  cerute — verifică lista exactă din `bibliografie.py`; termene (contestare,
  preaviz, perioadă de probă) au excepții pe categorii (funcții de conducere,
  persoane cu handicap, contracte pe durată determinată).
- **Legea 223/2015**: vechime în serviciu vs. vechime în muncă vs. vechime
  cumulată (art. 3); condițiile de pensionare (art. 16–21) au excepții pe
  condiții de muncă (art. 23–30); art. 28–30 (baza de calcul) au fost modificate
  masiv — se citește forma din text, nu din memorie.
- **Legea 360/2023**: în vigoare de la 1 septembrie 2024, a înlocuit Legea
  263/2010 — nu se folosesc valorile din legea veche (stagiu minim/complet,
  vârste standard, penalizări la anticipată) decât dacă apar în textul nou.
- **Derogări în vigoare care NU apar în textul consolidat** (verificate la 17.09.2026):
  OUG 7/2026 art. LIV — indemnizația pentru titlul de doctor (Legea 153/2017 art. 14
  alin. (1)) este 500 lei brut în 2026; Legea 141/2025 — pensiile militare nu se
  indexează în 2026 (art. 59 Legea 223/2015, în afara tematicii) și CASS 10 % pe
  indemnizația de creștere a copilului (prin Codul fiscal, nu prin OUG 111/2010).
  Întrebarea testează textul legii; explicația poate menționa derogarea, marcată
  ca atare („prin derogare, în 2026...").
- **Legea 153/2017 + Anexa VI**: corpul legii și anexa au numerotări separate —
  `sursa.anexa` obligatoriu pentru anexă; soldele de funcție sunt în tabele
  (citatele din tabele sunt greu de verificat: preferă articolele, nu rândurile
  de tabel); art. 15^1 din anexă e nou.
- **OUG 111/2010 / H.G. 52/2011**: indemnizația minimă/maximă, stimulentul de
  inserție (cuantum, condiții, până la ce vârstă a copilului), suspendarea vs.
  încetarea dreptului (art. 16–17 OUG), termene de depunere a cererii (art. 14
  OUG, art. 12–13 norme) — cifrele s-au schimbat în 2022–2023: numai textul.
- **H.G. 1867/2005**: art. 1 alin. (1): 50 % din solda de funcție (municipii,
  stațiuni, localități cu situații deosebite) vs. 40 % (alte localități), plafonat
  la chirie/rată — baza e **solda de funcție**, pe când Legea 80/1995 art. 20^1
  spune „până la 50% din solda lunară"; art. 3^1 abrogat; art. 17^2 e singurul
  dintre art. 16–17^x cerut.

## 6. Formatul livrării

- Fișier `tools/nou/<prefix>-<n>.json` = un array JSON valid (UTF-8, cu diacritice
  corecte ș/ț cu virgulă). Fără comentarii, fără virgule finale.
- La final agentul rulează din `quiz-app/tools/`:
  `python3 valideaza.py nou/<fisier>.json && python3 check_citat.py nou/<fisier>.json && python3 check_articol.py nou/<fisier>.json`
  și repară tot ce nu trece **înainte** de a raporta. Raportul final conține
  ieșirea celor trei comenzi, verbatim.
