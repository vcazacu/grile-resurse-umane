/* Logica aplicației de quiz — fără dependențe externe */
(function () {
  "use strict";

  var root = document.getElementById("app");
  var NR_TESTE = 30;
  var STORAGE_KEY = "grile-ru-scoruri";
  var CHEIE_IN_LUCRU = "grile-ru-in-lucru-v1";   // testul început și neterminat
  var CHEIE_ISTORIC = "grile-ru-istoric-v1";     // id întrebare -> 1 (ultima dată corect) / 0
  var CHEIE_MARCATE = "grile-ru-marcate-v1";     // id întrebare -> 1
  var PRAG_BUN = 70, PRAG_MEDIU = 50;
  var PE_SERVER = location.protocol.indexOf("http") === 0; // de pe disc (file://) nu se pot citi alte fișiere

  /* Actele din bibliografie, după prefixul fișierului sursă (01..09). Anexa nr. VI a Legii-cadru 153/2017
     (familia „apărare, ordine publică și securitate națională”) are grupa ei: e cerută separat în tematică. */
  var ACTE = {
    "01": { scurt: "Legea nr. 80/1995", pagina: "01-legea-80-1995-statutul-cadrelor-militare.html", consolidare: "28.03.2024", grupa: "01" },
    "02": { scurt: "Legea nr. 1/1998", pagina: "02-legea-1-1998-organizarea-sie.html", consolidare: "22.04.2017", grupa: "02" },
    "03": { scurt: "Codul muncii", pagina: "03-legea-53-2003-codul-muncii.html", consolidare: "27.04.2026", grupa: "03" },
    "04": { scurt: "Legea nr. 223/2015", pagina: "04-legea-223-2015-pensiile-militare.html", consolidare: "01.01.2024", grupa: "04" },
    "05": { scurt: "Legea nr. 360/2023", pagina: "05-legea-360-2023-sistemul-public-de-pensii.html", consolidare: "28.07.2025", grupa: "05" },
    "06": { scurt: "Legea-cadru nr. 153/2017", pagina: "06-legea-153-2017-salarizarea-bugetara.html", consolidare: "01.01.2026", grupa: "06" },
    "07": { scurt: "O.U.G. nr. 111/2010", pagina: "07-oug-111-2010-concediul-crestere-copil.html", consolidare: "19.09.2023", grupa: "07" },
    "08": { scurt: "Normele H.G. nr. 52/2011", pagina: "08-norme-hg-52-2011-aplicare-oug-111-2010.html", consolidare: "19.09.2023", grupa: "08" },
    "09": { scurt: "H.G. nr. 1867/2005", pagina: "09-hg-1867-2005-compensatia-chirie.html", consolidare: "06.05.2020", grupa: "09" }
  };
  var ANEXE = {
    "06#Anexa nr. VI": { scurt: "Anexa VI · Legea 153/2017", grupa: "06-VI" }
  };
  var GRUPE = {
    "01": { nume: "Legea nr. 80/1995", sub: "Statutul cadrelor militare" },
    "02": { nume: "Legea nr. 1/1998", sub: "Organizarea și funcționarea SIE" },
    "03": { nume: "Codul muncii", sub: "Legea nr. 53/2003" },
    "04": { nume: "Legea nr. 223/2015", sub: "Pensiile militare de stat" },
    "05": { nume: "Legea nr. 360/2023", sub: "Sistemul public de pensii" },
    "06": { nume: "Legea-cadru nr. 153/2017", sub: "Salarizarea personalului plătit din fonduri publice" },
    "06-VI": { nume: "Anexa VI la Legea nr. 153/2017", sub: "Apărare, ordine publică și securitate națională" },
    "07": { nume: "O.U.G. nr. 111/2010", sub: "Concediul pentru creșterea copiilor" },
    "08": { nume: "H.G. nr. 52/2011", sub: "Normele O.U.G. nr. 111/2010" },
    "09": { nume: "H.G. nr. 1867/2005", sub: "Compensația lunară pentru chirie" }
  };

  var state = {
    test: null,      // numărul testului curent (1..NR_TESTE); null la exerciții pe subset
    titlu: "",       // ce apare în bara de sus: „Testul 7”, „Exersare · Legea nr. 101/2016” …
    ordine: [],      // indecșii întrebărilor în ordinea de joc
    curent: 0,       // poziția în ordine
    raspunsuri: {},  // idxIntrebare -> [indecși selectați]
    corecte: 0,
    esteTestComplet: false, // true dacă rulăm un test întreg (scorul se salvează)
    amesteca: false,
    filtru: "toate"
  };
  var tasteEcran = null; // handler-ul de tastatură al ecranului curent

  /* ---------- Stocare locală ---------- */
  function citeste(cheie, implicit) {
    try { var v = JSON.parse(localStorage.getItem(cheie)); return v === null || v === undefined ? implicit : v; }
    catch (e) { return implicit; }
  }
  function scrie(cheie, valoare) {
    try {
      if (valoare === null) localStorage.removeItem(cheie);
      else localStorage.setItem(cheie, JSON.stringify(valoare));
    } catch (e) { /* localStorage indisponibil — ignorăm */ }
  }
  function scoruri() { return citeste(STORAGE_KEY, {}); }
  function salveazaScor(test, pct, corecte, total) {
    var s = scoruri();
    var vechi = s[test];
    s[test] = {
      pct: pct, corecte: corecte, total: total,
      best: Math.max(pct, vechi && vechi.best ? vechi.best : 0)
    };
    scrie(STORAGE_KEY, s);
  }

  var indexDupaId = {};
  function idx(id) { return Object.prototype.hasOwnProperty.call(indexDupaId, id) ? indexDupaId[id] : -1; }

  /* Testul în lucru se păstrează pe id-uri, nu pe poziții: banca se poate regenera între două deschideri.
     Se păstrează doar testele întregi; un set scurt de exersare nu înlocuiește un test lăsat la jumătate. */
  function salveazaInLucru(curent) {
    if (!state.esteTestComplet) return;
    var r = {};
    Object.keys(state.raspunsuri).forEach(function (k) { r[INTREBARI[k].id] = state.raspunsuri[k]; });
    scrie(CHEIE_IN_LUCRU, {
      test: state.test, titlu: state.titlu, esteTestComplet: state.esteTestComplet,
      curent: curent, corecte: state.corecte,
      ordine: state.ordine.map(function (i) { return INTREBARI[i].id; }),
      raspunsuri: r
    });
  }
  function testInLucru() {
    var p = citeste(CHEIE_IN_LUCRU, null);
    if (!p || !Array.isArray(p.ordine) || !p.ordine.length) return null;
    var ordine = p.ordine.map(idx);
    if (ordine.indexOf(-1) >= 0) { scrie(CHEIE_IN_LUCRU, null); return null; }
    var raspunsuri = {};
    Object.keys(p.raspunsuri || {}).forEach(function (id) {
      var i = idx(id);
      if (i >= 0) raspunsuri[i] = p.raspunsuri[id];
    });
    return {
      test: p.test || null, titlu: p.titlu || "", esteTestComplet: !!p.esteTestComplet,
      curent: Math.min(Math.max(p.curent | 0, 0), ordine.length), corecte: p.corecte | 0,
      ordine: ordine, raspunsuri: raspunsuri
    };
  }

  function istoric() { return citeste(CHEIE_ISTORIC, {}); }
  function inregistreaza(q, corect) {
    var h = istoric();
    h[q.id] = corect ? 1 : 0;
    scrie(CHEIE_ISTORIC, h);
  }
  function marcate() { return citeste(CHEIE_MARCATE, {}); }
  function comutaMarcata(q) {
    var m = marcate();
    if (m[q.id]) delete m[q.id]; else m[q.id] = 1;
    scrie(CHEIE_MARCATE, m);
    return !!m[q.id];
  }

  /* ---------- Validarea băncii de întrebări ---------- */
  function valideazaIntrebari(lista) {
    var erori = [];
    if (!Array.isArray(lista) || lista.length === 0) {
      erori.push("Fișierul intrebari.js nu conține un array INTREBARI valid.");
      return erori;
    }
    var ids = {};
    var perTest = {}; // test -> {total, multi}
    lista.forEach(function (q, i) {
      var loc = "Întrebarea #" + (i + 1) + (q && q.id ? " (" + q.id + ")" : "");
      if (!q || typeof q !== "object") { erori.push(loc + ": nu este un obiect."); return; }
      if (!q.id) erori.push(loc + ": lipsește câmpul id.");
      else if (ids[q.id]) erori.push(loc + ": id duplicat.");
      else ids[q.id] = true;
      if (q.tip !== "unic" && q.tip !== "multiplu") erori.push(loc + ": tip trebuie să fie \"unic\" sau \"multiplu\".");
      if (!q.intrebare || typeof q.intrebare !== "string") erori.push(loc + ": lipsește textul întrebării.");
      if (!Array.isArray(q.variante) || q.variante.length < 2) erori.push(loc + ": variante trebuie să aibă cel puțin 2 elemente.");
      if (q.tip === "unic" && Array.isArray(q.variante) && q.variante.length !== 4) erori.push(loc + ": întrebările cu răspuns unic trebuie să aibă exact 4 variante.");
      if (!Array.isArray(q.corecte) || q.corecte.length === 0) erori.push(loc + ": corecte trebuie să fie un array nevid de indecși.");
      else {
        if (q.tip === "unic" && q.corecte.length !== 1) erori.push(loc + ": tip \"unic\" cere exact un index în corecte.");
        if (q.tip === "multiplu" && q.corecte.length < 2) erori.push(loc + ": tip \"multiplu\" cere cel puțin 2 indecși în corecte.");
        q.corecte.forEach(function (c) {
          if (!Number.isInteger(c) || c < 0 || !q.variante || c >= q.variante.length)
            erori.push(loc + ": indexul corect " + c + " nu există în variante.");
        });
      }
      if (!q.explicatie) erori.push(loc + ": lipsește explicația.");
      if (!q.sursa || !q.sursa.act || !q.sursa.articol || !q.sursa.citat)
        erori.push(loc + ": sursa trebuie să conțină act, articol și citat.");
      if (q.status !== "ok" && q.status !== "de verificat") erori.push(loc + ": status trebuie să fie \"ok\" sau \"de verificat\".");
      if (!Number.isInteger(q.test) || q.test < 1 || q.test > NR_TESTE)
        erori.push(loc + ": test trebuie să fie un număr întreg între 1 și " + NR_TESTE + ".");
      else {
        if (!perTest[q.test]) perTest[q.test] = { total: 0, multi: 0 };
        perTest[q.test].total++;
        if (q.tip === "multiplu") perTest[q.test].multi++;
      }
    });
    for (var t = 1; t <= NR_TESTE; t++) {
      var info = perTest[t];
      if (!info) { erori.push("Testul " + t + ": nu are nicio întrebare."); continue; }
      if (info.total !== 20) erori.push("Testul " + t + ": are " + info.total + " întrebări în loc de 20.");
      if (info.multi > 4) erori.push("Testul " + t + ": are " + info.multi + " întrebări cu răspunsuri multiple (maxim 4).");
    }
    return erori;
  }

  /* ---------- Utilitare ---------- */
  function el(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html !== undefined) e.innerHTML = html;
    return e;
  }
  function esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  function amestecat(n) {
    var a = [];
    for (var i = 0; i < n; i++) a.push(i);
    for (var j = a.length - 1; j > 0; j--) {
      var k = Math.floor(Math.random() * (j + 1));
      var t = a[j]; a[j] = a[k]; a[k] = t;
    }
    return a;
  }
  function amestecaLista(lista) {
    return amestecat(lista.length).map(function (p) { return lista[p]; });
  }
  function litera(i) { return String.fromCharCode(65 + i); }
  /* „3 întrebări”, „20 de întrebări”, „110 întrebări” */
  function nrCu(n, cuvant) { return n + " " + ((n % 100 === 0 && n) || n % 100 >= 20 ? "de " : "") + cuvant; }
  function ton(pct) { return pct >= PRAG_BUN ? "ok" : pct >= PRAG_MEDIU ? "mid" : "slab"; }

  function icon(nume, marime) {
    var m = marime || 20;
    var trase = {
      chevron: '<polyline points="6 9 12 15 18 9"></polyline>',
      dreapta: '<polyline points="9 6 15 12 9 18"></polyline>',
      stanga: '<polyline points="15 6 9 12 15 18"></polyline>',
      sageata: '<line x1="5" y1="12" x2="19" y2="12"></line><polyline points="13 6 19 12 13 18"></polyline>',
      x: '<line x1="6" y1="6" x2="18" y2="18"></line><line x1="18" y1="6" x2="6" y2="18"></line>',
      bifa: '<polyline points="5 12.5 10 17 19 7"></polyline>',
      cercBifa: '<circle cx="12" cy="12" r="9"></circle><polyline points="8 12.5 11 15.5 16 9.5"></polyline>',
      cercX: '<circle cx="12" cy="12" r="9"></circle><line x1="9" y1="9" x2="15" y2="15"></line><line x1="15" y1="9" x2="9" y2="15"></line>',
      semn: '<path d="M6 4h12v17l-6-4-6 4z"></path>'
    };
    return '<svg width="' + m + '" height="' + m + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + trase[nume] + "</svg>";
  }

  function seturiEgale(a, b) {
    if (a.length !== b.length) return false;
    var s = {};
    a.forEach(function (x) { s[x] = true; });
    return b.every(function (x) { return s[x]; });
  }
  function intrebariTest(t) {
    var r = [];
    INTREBARI.forEach(function (q, i) { if (q.test === t) r.push(i); });
    return r;
  }
  function textVariante(q, indecsi) {
    return indecsi.map(function (i) { return litera(i) + ") " + q.variante[i]; }).join("; ");
  }
  function scrollSus() { window.scrollTo(0, 0); }

  /* ---------- Trimiteri către textul de lege ---------- */
  function actul(q) {
    var pref = String(q.sursa.fisier || "").slice(0, 2);
    var a = ACTE[pref] || { scurt: q.sursa.act, pagina: null, consolidare: null, grupa: pref || "?" };
    var ax = q.sursa.anexa && ANEXE[pref + "#" + q.sursa.anexa];
    if (!ax) return a;
    return { scurt: ax.scurt, pagina: a.pagina, consolidare: a.consolidare, grupa: ax.grupa };
  }
  /* „art. 5 alin. (3) lit. b)” -> {articol: "art-5", tinte: ["art-5-al-3-lit-b", "art-5-al-3"]}
     după convenția de id-uri din tools/legislatie_build.py (^ devine -); în anexe, id-urile au prefixul
     „anexa-<anexa>-” (ex. „anexa-anexa-nr-vi-art-1”). */
  function ancore(articol, anexa) {
    var r = ancoreFaraAnexa(articol);
    if (!r || !anexa) return r;
    var pref = "anexa-" + anexa.replace(/[^A-Za-z0-9]+/g, "-").replace(/^-+|-+$/g, "").toLowerCase() + "-";
    return { articol: pref + r.articol, tinte: r.tinte.map(function (t) { return pref + t; }) };
  }
  function ancoreFaraAnexa(articol) {
    var s = String(articol).trim();
    if (/^(preambul|formula)/i.test(s)) return { articol: "preambul", tinte: [] };
    var m = /^(art|pct)\.\s*([0-9]+(?:\^[0-9]+)?|[IVXLC]+)\b/i.exec(s);
    if (!m) return null;
    var baza = m[1].toLowerCase() + "-" + m[2].replace("^", "-");
    var rest = s.slice(m[0].length);
    var tinte = [];
    var al = /^\s*alin\.\s*\((\d+(?:\^\d+)?)\)/.exec(rest);
    var lit = /lit\.\s*([a-zșț](?:\^\d+)?)\)/.exec(rest);
    if (al) {
      var cuAl = baza + "-al-" + al[1].replace("^", "-");
      if (lit) tinte.push(cuAl + "-lit-" + lit[1].replace("^", "-"));
      tinte.push(cuAl);
    } else if (lit) {
      // „art. 4 lit. b)” citat fără alineat: în pagină litera poate sta sub singurul alineat, (1)
      tinte.push(baza + "-lit-" + lit[1].replace("^", "-"), baza + "-al-1-lit-" + lit[1].replace("^", "-"));
    }
    return { articol: baza, tinte: tinte };
  }
  function linkLege(q) {
    var a = actul(q), anc = ancore(q.sursa.articol, q.sursa.anexa);
    if (!a.pagina) return null;
    return "legislatie/" + a.pagina + (anc ? "#" + anc.articol : "");
  }

  var paginiLege = {}; // pagină -> Promise<Document>
  function incarcaPagina(pagina) {
    if (!paginiLege[pagina]) {
      paginiLege[pagina] = fetch("legislatie/" + pagina)
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.text(); })
        .then(function (t) { return new DOMParser().parseFromString(t, "text/html"); });
      paginiLege[pagina].catch(function () { delete paginiLege[pagina]; });
    }
    return paginiLege[pagina];
  }
  /* Aduce articolul întreg din pagina de legislație și evidențiază alineatul/litera citată. */
  function arataArticolul(q, cutie) {
    var a = actul(q), anc = ancore(q.sursa.articol, q.sursa.anexa);
    cutie.innerHTML = '<p class="stare">Se încarcă articolul…</p>';
    incarcaPagina(a.pagina).then(function (doc) {
      var art = anc && doc.getElementById(anc.articol);
      if (!art) { cutie.innerHTML = '<p class="stare">Articolul nu apare separat în pagina legii; folosește linkul de mai sus.</p>'; return; }
      var copie = document.importNode(art, true);
      copie.removeAttribute("id");
      Array.prototype.forEach.call(copie.querySelectorAll("a[href^='#']"), function (l) {
        l.setAttribute("href", "legislatie/" + a.pagina + l.getAttribute("href"));
      });
      var tinta = null;
      anc.tinte.some(function (t) { tinta = copie.querySelector('[id="' + t + '"]'); return !!tinta; });
      Array.prototype.forEach.call(copie.querySelectorAll("[id]"), function (n) { n.removeAttribute("id"); });
      cutie.innerHTML = "";
      cutie.appendChild(copie);
      if (tinta) {
        tinta.classList.add("tinta");
        var panou = cutie.closest(".panou-lege");
        if (panou && panou.scrollHeight > panou.clientHeight) {
          panou.scrollTop = tinta.getBoundingClientRect().top - panou.getBoundingClientRect().top + panou.scrollTop - 80;
        }
      }
    }).catch(function () {
      cutie.innerHTML = '<p class="stare">Textul legii nu s-a putut încărca acum; folosește linkul de mai sus.</p>';
    });
  }

  /* ---------- Componente ---------- */
  function cardTemei(q) {
    var legal = el("div", "legal-card");
    legal.appendChild(el("div", "act", esc(q.sursa.act)));
    legal.appendChild(el("span", "articol", esc(q.sursa.articol)));
    legal.appendChild(el("blockquote", null, "„" + esc(q.sursa.citat) + "”"));
    var href = linkLege(q);
    if (href) legal.appendChild(el("div", "fisier", '<a href="' + esc(href) + '">Citește articolul în lege</a>'));
    return legal;
  }

  function corpExplicatie(q, alTau) {
    var corp = el("div", "recap-corp");
    if (alTau) {
      corp.appendChild(el("div", "raspunsuri",
        '<div class="al-tau">Răspunsul tău: ' + (alTau.length ? esc(textVariante(q, alTau)) : "—") + "</div>" +
        '<div class="bun">Corect: ' + esc(textVariante(q, q.corecte)) + "</div>"));
    }
    corp.appendChild(el("div", "explic-section-title", "De ce"));
    corp.appendChild(el("p", "explic-text", esc(q.explicatie)));
    corp.appendChild(cardTemei(q));
    return corp;
  }

  /* ---------- Statistici ---------- */
  function statisticiPeGrupe() {
    var h = istoric(), g = {};
    INTREBARI.forEach(function (q) {
      if (!Object.prototype.hasOwnProperty.call(h, q.id)) return;
      var k = actul(q).grupa;
      if (!g[k]) g[k] = { grupa: k, date: 0, corecte: 0 };
      g[k].date++;
      if (h[q.id]) g[k].corecte++;
    });
    return Object.keys(g).map(function (k) {
      g[k].pct = Math.round(g[k].corecte / g[k].date * 100);
      return g[k];
    });
  }
  /* Un set de exersare de cel mult 20: întâi cele greșite ultima dată, apoi cele nedate, apoi restul. */
  function alegePentruExersare(indecsi) {
    var h = istoric(), gresite = [], nedate = [], stiute = [];
    indecsi.forEach(function (i) {
      var id = INTREBARI[i].id;
      if (!Object.prototype.hasOwnProperty.call(h, id)) nedate.push(i);
      else if (h[id]) stiute.push(i);
      else gresite.push(i);
    });
    return amestecaLista(gresite).concat(amestecaLista(nedate), amestecaLista(stiute)).slice(0, 20);
  }
  function setExersare(grupa) {
    var lista = [];
    INTREBARI.forEach(function (q, i) { if (actul(q).grupa === grupa) lista.push(i); });
    return alegePentruExersare(lista);
  }

  /* ---------- Ecranul de start ---------- */
  function ecranStart(eroriValidare) {
    document.body.classList.remove("in-test");
    tasteEcran = null;
    root.innerHTML = "";
    var wrap = el("div", "acasa");

    if (eroriValidare.length) {
      var maxAfisate = 15;
      var listate = eroriValidare.slice(0, maxAfisate);
      var rest = eroriValidare.length - listate.length;
      wrap.appendChild(el("div", "validation-error",
        "<strong>Banca de întrebări conține erori — corectează intrebari.js:</strong>" +
        "<ul>" + listate.map(function (e) { return "<li>" + esc(e) + "</li>"; }).join("") + "</ul>" +
        (rest > 0 ? "<div>… și încă " + rest + " erori (vezi consola browserului).</div>" : "")));
    }

    var nrMulti = INTREBARI.filter(function (q) { return q.tip === "multiplu"; }).length;
    var nrVerif = INTREBARI.filter(function (q) { return q.status === "de verificat"; }).length;
    wrap.appendChild(el("div", "acasa-cap",
      '<span class="eyebrow">Examen resurse umane</span>' +
      "<h1>Grile Resurse Umane</h1>" +
      "<p>" + NR_TESTE + " de teste a câte 20 de întrebări (" + INTREBARI.length + " în total, " + nrMulti +
      " cu răspunsuri multiple), pe legislația în formă consolidată la zi." +
      (nrVerif ? " " + nrVerif + " întrebări sunt marcate „de verificat”." : "") + "</p>"));

    var s = scoruri();
    var inLucru = testInLucru();
    var blocat = eroriValidare.length > 0;

    /* progresul general + continuarea */
    var sus = el("div", "acasa-sus" + (inLucru ? " cu-continuare" : ""));
    var progres = el("section", "panou");
    progres.setAttribute("aria-label", "Progresul tău");
    var facute = [], suma = 0;
    for (var t = 1; t <= NR_TESTE; t++) if (s[t]) { facute.push(t); suma += s[t].best; }
    progres.appendChild(el("div", "cap-sectiune", '<span class="titlu-sectiune" style="font-size:14px">Progresul tău</span>'));
    if (facute.length) {
      progres.appendChild(el("div", "cifre",
        '<div class="cifra"><b>' + facute.length + "<small> / " + NR_TESTE + "</small></b><span>teste terminate</span></div>" +
        '<div class="cifra"><b>' + Math.round(suma / facute.length) + "%</b><span>media celor mai bune scoruri</span></div>"));
    } else {
      progres.appendChild(el("p", "gol", "Niciun test terminat încă. Scorul cel mai bun al fiecărui test apare aici și pe grila de mai jos."));
    }
    var banda = el("div", "banda");
    banda.style.gridTemplateColumns = "repeat(" + NR_TESTE + ", minmax(0, 1fr))";
    banda.setAttribute("role", "img");
    banda.setAttribute("aria-label", facute.length + " din " + NR_TESTE + " teste terminate");
    for (var b = 1; b <= NR_TESTE; b++) {
      var celula = el("i");
      if (inLucru && inLucru.esteTestComplet && inLucru.test === b) celula.className = "lucru";
      else if (s[b]) celula.className = ton(s[b].best);
      banda.appendChild(celula);
    }
    progres.appendChild(banda);
    progres.appendChild(el("div", "legenda",
      '<span><i class="ok"></i>≥ 70%</span><span><i class="mid"></i>50–69%</span><span><i class="slab"></i>sub 50%</span>' +
      (inLucru ? '<span><i class="lucru"></i>în lucru</span>' : "")));
    sus.appendChild(progres);

    if (inLucru) {
      var bloc = el("div", "continua-bloc");
      var btnCont = el("button", "continua");
      btnCont.type = "button";
      var nrDate = Object.keys(inLucru.raspunsuri).length;
      btnCont.innerHTML =
        '<span class="text"><span class="eyebrow">Continuă de unde ai rămas</span>' +
        '<span class="titlu">' + esc(inLucru.titlu || ("Testul " + inLucru.test)) + "</span>" +
        '<span class="detalii">' + (inLucru.curent >= inLucru.ordine.length
          ? "Toate întrebările au răspuns · vezi rezultatul"
          : "Întrebarea " + (inLucru.curent + 1) + " din " + inLucru.ordine.length +
            (nrDate ? " · " + inLucru.corecte + " corecte până acum" : "")) + "</span></span>" +
        '<span class="sageata">' + icon("dreapta", 22) + "</span>";
      btnCont.disabled = blocat;
      btnCont.addEventListener("click", function () { reia(inLucru); });
      bloc.appendChild(btnCont);
      var renunta = el("button", "link-mic", "Renunță la acest test");
      renunta.type = "button";
      renunta.addEventListener("click", function () { scrie(CHEIE_IN_LUCRU, null); ecranStart(eroriValidare); });
      bloc.appendChild(renunta);
      sus.appendChild(bloc);
    }
    wrap.appendChild(sus);

    /* de recapitulat: actele cu cel mai slab procent + întrebările marcate */
    var recap = el("section", "sectiune");
    recap.appendChild(el("div", "cap-sectiune", '<h2 class="titlu-sectiune">De recapitulat</h2><span class="nota">după ultimul răspuns la fiecare întrebare</span>'));
    var stat = statisticiPeGrupe().filter(function (g) { return g.date >= 5 && GRUPE[g.grupa]; })
      .sort(function (a, b) { return a.pct - b.pct; }).slice(0, 3);
    var nrMarcate = Object.keys(marcate()).filter(function (id) { return idx(id) >= 0; }).length;
    var lista = el("div", "lista-recap");
    stat.forEach(function (g) {
      var info = GRUPE[g.grupa];
      var r = el("div", "rand-recap");
      r.innerHTML =
        '<div class="text"><div class="linie"><span class="nume">' + esc(info.nume) + '</span><span class="pct ton-' + ton(g.pct) + '">' + g.pct + "%</span></div>" +
        '<div class="sub">' + esc(info.sub) + " · " + (g.date === 1 ? "1 întrebare dată" : nrCu(g.date, "întrebări date")) + "</div>" +
        '<div class="bara"><i class="ton-' + ton(g.pct) + '" style="width:' + g.pct + '%"></i></div></div>';
      var ex = el("button", "btn-mic", "Exersează");
      ex.type = "button";
      ex.setAttribute("aria-label", "Exersează " + info.nume);
      ex.disabled = blocat;
      ex.addEventListener("click", function () { porneste(null, setExersare(g.grupa), false, "Exersare · " + info.nume); });
      r.appendChild(ex);
      lista.appendChild(r);
    });
    if (nrMarcate) {
      var rm = el("div", "rand-recap");
      rm.innerHTML = '<div class="text"><span class="nume">Întrebări marcate</span><div class="sub">' +
        (nrMarcate === 1 ? "1 întrebare pusă" : nrCu(nrMarcate, "întrebări puse")) + " deoparte în timpul testelor</div></div>";
      var exM = el("button", "btn-mic", "Exersează");
      exM.type = "button";
      exM.setAttribute("aria-label", "Exersează întrebările marcate");
      exM.disabled = blocat;
      exM.addEventListener("click", function () {
        var ids = Object.keys(marcate()).map(idx).filter(function (i) { return i >= 0; });
        porneste(null, amestecaLista(ids), false, "Întrebări marcate");
      });
      rm.appendChild(exM);
      lista.appendChild(rm);
    }
    if (!stat.length && !nrMarcate) {
      lista.appendChild(el("div", "rand-recap", '<p class="sub" style="font-size:14px;color:var(--muted-foreground)">După primele teste, aici apar actele normative la care greșești cel mai des, cu un set de exersare pentru fiecare.</p>'));
    }
    recap.appendChild(lista);
    wrap.appendChild(recap);

    /* toate testele */
    var teste = el("section", "sectiune");
    teste.appendChild(el("h2", "titlu-sectiune", "Toate testele"));
    var stari = {};
    var nrNefacute = 0, nrSub = 0;
    for (var n = 1; n <= NR_TESTE; n++) {
      if (inLucru && inLucru.esteTestComplet && inLucru.test === n) { stari[n] = "lucru"; nrNefacute++; }
      else if (!s[n]) { stari[n] = "nou"; nrNefacute++; }
      else { stari[n] = ton(s[n].best); if (s[n].best < PRAG_BUN) nrSub++; }
    }
    var filtre = el("div", "filtre");
    filtre.setAttribute("role", "group");
    filtre.setAttribute("aria-label", "Filtrează testele");
    [["toate", "Toate · " + NR_TESTE], ["nefacute", "Nefăcute · " + nrNefacute], ["sub", "Sub 70% · " + nrSub]].forEach(function (f) {
      var c = el("button", "chip", f[1]);
      c.type = "button";
      c.setAttribute("aria-pressed", state.filtru === f[0] ? "true" : "false");
      c.addEventListener("click", function () { state.filtru = f[0]; ecranStart(eroriValidare); });
      filtre.appendChild(c);
    });
    teste.appendChild(filtre);

    var grid = el("div", "test-grid");
    for (var k = 1; k <= NR_TESTE; k++) {
      (function (t) {
        var st = stari[t];
        if (state.filtru === "nefacute" && st !== "nou" && st !== "lucru") return;
        if (state.filtru === "sub" && st !== "mid" && st !== "slab") return;
        var idxT = intrebariTest(t);
        var btn = el("button", "test-btn " + st);
        btn.type = "button";
        var eticheta = st === "nou" ? "nou" : st === "lucru" ? (inLucru.curent + "/" + inLucru.ordine.length) : s[t].best + "%";
        btn.innerHTML = '<span class="nr">' + t + '</span><span class="scor">' + eticheta + "</span>";
        btn.setAttribute("aria-label", "Testul " + t + ", " +
          (st === "nou" ? "neînceput" : st === "lucru" ? "în lucru" : "cel mai bun scor " + s[t].best + "%"));
        btn.disabled = blocat || idxT.length === 0;
        btn.addEventListener("click", function () {
          if (st === "lucru") reia(inLucru);
          else porneste(t, idxT, true, "Testul " + t);
        });
        grid.appendChild(btn);
      })(k);
    }
    if (!grid.children.length) teste.appendChild(el("p", "gol", state.filtru === "sub" ? "Niciun test sub 70%." : "Ai făcut toate testele."));
    else teste.appendChild(grid);

    var lbl = el("label", "comutator");
    var chk = el("input");
    chk.type = "checkbox";
    chk.id = "chk-shuffle";
    chk.checked = state.amesteca;
    chk.addEventListener("change", function () { state.amesteca = chk.checked; });
    lbl.appendChild(chk);
    lbl.appendChild(document.createTextNode("Amestecă ordinea întrebărilor în test"));
    teste.appendChild(lbl);
    wrap.appendChild(teste);

    wrap.appendChild(el("footer", null,
      "Surse: formele consolidate la zi de pe legislatie.just.ro (Portal Legislativ), descărcate în folderul legislatie/.<br>" +
      "Legea 80/1995 · Legea 1/1998 · Codul muncii · Legea 223/2015 · Legea 360/2023 · Legea-cadru 153/2017 (+ anexa VI) · O.U.G. 111/2010 · H.G. 52/2011 · H.G. 1867/2005"));
    root.appendChild(wrap);
    scrollSus();
  }

  /* ---------- Pornirea unui test / subset ---------- */
  function porneste(test, subset, esteComplet, titlu) {
    var ordine = subset.slice();
    if (state.amesteca) ordine = amestecaLista(ordine);
    state.test = test;
    state.titlu = titlu || (test ? "Testul " + test : "Exersare");
    state.ordine = ordine;
    state.curent = 0;
    state.raspunsuri = {};
    state.corecte = 0;
    state.esteTestComplet = !!esteComplet;
    salveazaInLucru(0);
    arataIntrebare();
  }
  function reia(p) {
    state.test = p.test;
    state.titlu = p.titlu;
    state.ordine = p.ordine;
    state.curent = p.curent;
    state.raspunsuri = p.raspunsuri;
    state.corecte = p.corecte;
    state.esteTestComplet = p.esteTestComplet;
    if (state.curent >= state.ordine.length) ecranScor();
    else arataIntrebare();
  }

  /* ---------- Ecranul unei întrebări ---------- */
  function arataIntrebare() {
    document.body.classList.add("in-test");
    var qIdx = state.ordine[state.curent];
    var q = INTREBARI[qIdx];
    var a = actul(q);
    var selectate = [];
    var verificat = false;
    var total = state.ordine.length;

    root.innerHTML = "";
    var wrap = el("div", "ecran-test");

    /* bara de sus: ieșire, titlu, progres pe segmente */
    var bara = el("div", "bara-test");
    var rand = el("div", "rand");
    var iesi = el("button", "btn-iesi", icon("x", 22) + "<span>Ieși</span>");
    iesi.type = "button";
    iesi.setAttribute("aria-label", "Ieși din test; progresul rămâne salvat");
    iesi.addEventListener("click", function () { ecranStart([]); });
    rand.appendChild(iesi);
    rand.appendChild(el("div", "titlu", esc(state.titlu)));
    rand.appendChild(el("div", "contor", (state.curent + 1) + "/" + total));
    bara.appendChild(rand);
    var seg = el("div", "segmente");
    seg.style.gridTemplateColumns = "repeat(" + total + ", minmax(0, 1fr))";
    var nrCorecte = 0, nrGresite = 0;
    state.ordine.forEach(function (qi, i) {
      var cls = "";
      if (i < state.curent && state.raspunsuri[qi]) {
        var ok = seturiEgale(state.raspunsuri[qi], INTREBARI[qi].corecte);
        cls = ok ? "ok" : "bad";
        if (ok) nrCorecte++; else nrGresite++;
      } else if (i === state.curent) cls = "acum";
      seg.appendChild(el("i", cls));
    });
    seg.setAttribute("role", "img");
    seg.setAttribute("aria-label", "Întrebarea " + (state.curent + 1) + " din " + total + "; " + nrCorecte + " corecte, " + nrGresite + " greșite");
    bara.appendChild(seg);
    wrap.appendChild(bara);

    var grila = el("div", "test-grila");

    /* întrebarea */
    var principal = el("section", "test-principal");
    var card = el("div", "card card-intrebare");
    var etichete = el("div", "etichete");
    etichete.appendChild(el("span", "badge", esc(a.scurt)));
    etichete.appendChild(el("span", "badge multi", q.tip === "multiplu" ? "Alege toate răspunsurile corecte" : "Un singur răspuns"));
    if (q.status === "de verificat") etichete.appendChild(el("span", "badge warn", "De verificat"));
    card.appendChild(etichete);
    card.appendChild(el("p", "question-text", esc(q.intrebare)));

    var optiuni = el("div", "options");
    optiuni.setAttribute("role", "group");
    optiuni.setAttribute("aria-label", "Variante de răspuns");
    var butoane = [];
    q.variante.forEach(function (v, i) {
      var b = el("button", "option");
      b.type = "button";
      b.dataset.mode = q.tip;
      b.setAttribute("aria-pressed", "false");
      b.innerHTML = '<span class="cheie">' + litera(i) + '</span><span class="text-var">' + esc(v) + "</span>";
      b.addEventListener("click", function () { alege(i); });
      butoane.push(b);
      optiuni.appendChild(b);
    });
    card.appendChild(optiuni);
    var zonaFeedback = el("div");
    zonaFeedback.style.display = "contents";
    card.appendChild(zonaFeedback);
    principal.appendChild(card);
    grila.appendChild(principal);

    /* textul de lege: pe desktop e coloana din dreapta, pe telefon apare sub întrebare după verificare */
    var panou = el("aside", "panou-lege gol");
    panou.setAttribute("aria-label", "Temeiul legal");
    panou.innerHTML = '<div class="lege-cap"><span class="eyebrow">Temei legal</span></div>' +
      '<p class="asteapta">Articolul din lege apare aici după ce verifici răspunsul.</p>';
    grila.appendChild(panou);

    /* acțiunile de jos */
    var actiuni = el("div", "bara-actiuni");
    var btnMarcheaza = el("button", "btn-icon", icon("semn", 20));
    btnMarcheaza.type = "button";
    btnMarcheaza.setAttribute("aria-label", "Pune întrebarea deoparte, pentru recapitulare");
    btnMarcheaza.setAttribute("aria-pressed", marcate()[q.id] ? "true" : "false");
    btnMarcheaza.title = "Pune deoparte pentru recapitulare";
    btnMarcheaza.addEventListener("click", function () {
      btnMarcheaza.setAttribute("aria-pressed", comutaMarcata(q) ? "true" : "false");
    });
    actiuni.appendChild(btnMarcheaza);
    var btnPrincipal = el("button", "btn btn-primary", "Verifică răspunsul");
    btnPrincipal.type = "button";
    btnPrincipal.disabled = true;
    btnPrincipal.addEventListener("click", function () {
      if (!verificat) verifica();
      else urmatoarea();
    });
    actiuni.appendChild(btnPrincipal);
    var indiciu = el("div", "indiciu", "<kbd>1</kbd>–<kbd>" + q.variante.length + "</kbd> alegi · <kbd>Enter</kbd> verifici");
    actiuni.appendChild(indiciu);
    grila.appendChild(actiuni);

    wrap.appendChild(grila);
    root.appendChild(wrap);

    function alege(i) {
      if (verificat) return;
      if (q.tip === "unic") selectate = [i];
      else {
        var poz = selectate.indexOf(i);
        if (poz >= 0) selectate.splice(poz, 1); else selectate.push(i);
      }
      butoane.forEach(function (b, j) {
        var on = selectate.indexOf(j) >= 0;
        b.classList.toggle("selected", on);
        b.setAttribute("aria-pressed", on ? "true" : "false");
      });
      btnPrincipal.disabled = selectate.length === 0;
    }

    function verifica() {
      if (verificat || !selectate.length) return;
      verificat = true;
      state.raspunsuri[qIdx] = selectate.slice();
      var esteCorect = seturiEgale(selectate, q.corecte);
      if (esteCorect) state.corecte++;
      inregistreaza(q, esteCorect);
      salveazaInLucru(state.curent + 1);

      butoane.forEach(function (b, i) {
        b.disabled = true;
        b.classList.remove("selected");
        b.removeAttribute("aria-pressed");
        var eCorecta = q.corecte.indexOf(i) >= 0;
        var eAleasa = selectate.indexOf(i) >= 0;
        var cheie = b.querySelector(".cheie"), text = b.querySelector(".text-var");
        var eticheta = null;
        if (eCorecta && eAleasa) {
          b.classList.add("correct"); cheie.innerHTML = icon("bifa", 16);
          eticheta = q.tip === "unic" ? "Alegerea ta, corectă" : "Corect";
        } else if (!eCorecta && eAleasa) {
          b.classList.add("incorrect"); cheie.innerHTML = icon("x", 16);
          eticheta = q.tip === "unic" ? "Alegerea ta (" + litera(i) + ")" : "Greșit";
        } else if (eCorecta && !eAleasa) {
          b.classList.add("missed");
          eticheta = q.tip === "unic" ? "Răspunsul corect (" + litera(i) + ")" : "Ai omis-o";
        } else {
          b.classList.add("estompat");
        }
        if (eticheta) text.appendChild(el("span", "tag", eticheta));
      });

      var corecteLitere = q.corecte.map(litera).join(", ");
      zonaFeedback.appendChild(el("div", "verdict " + (esteCorect ? "ok" : "bad"),
        icon(esteCorect ? "cercBifa" : "cercX", 22) + "<span>" + (esteCorect ? "Corect" :
          "Greșit · corect " + (q.corecte.length > 1 ? "erau " : "era ") + corecteLitere) + "</span>"));
      var expl = el("div", "explicatie");
      expl.appendChild(el("div", "explic-section-title", "De ce"));
      expl.appendChild(el("p", null, esc(q.explicatie)));
      zonaFeedback.appendChild(expl);

      umplePanou();

      btnPrincipal.textContent = state.curent + 1 < total ? "Întrebarea următoare" : "Vezi rezultatul";
      if (state.curent + 1 < total) btnPrincipal.insertAdjacentHTML("beforeend", icon("sageata", 18));
      indiciu.innerHTML = "<kbd>Enter</kbd> continui";
      btnPrincipal.focus({ preventScroll: true });
    }

    function umplePanou() {
      panou.classList.remove("gol");
      panou.innerHTML = "";
      panou.appendChild(el("div", "lege-cap",
        '<span class="eyebrow">Temei legal</span>' +
        (a.consolidare ? '<span class="consolidare">consolidat ' + esc(a.consolidare) + "</span>" : "")));
      panou.appendChild(el("div", "lege-act",
        '<span class="nume">' + esc(q.sursa.act) + '</span><span class="ref">' + esc(q.sursa.articol) + "</span>"));
      panou.appendChild(el("blockquote", "citat", "„" + esc(q.sursa.citat) + "”"));
      var href = linkLege(q);
      if (href) {
        var linkuri = el("div", "lege-linkuri");
        linkuri.appendChild(el("a", "link-sageata", "Deschide în lege " + icon("sageata", 16)));
        linkuri.firstChild.href = href;
        var cutie = el("div", "articol-intreg");
        if (PE_SERVER) {
          if (window.matchMedia("(min-width: 1024px)").matches) {
            panou.appendChild(linkuri);
            panou.appendChild(cutie);
            arataArticolul(q, cutie);
            return;
          }
          var arata = el("button", "btn-text", "Arată tot articolul");
          arata.type = "button";
          arata.addEventListener("click", function () {
            arata.remove();
            panou.appendChild(cutie);
            arataArticolul(q, cutie);
          });
          linkuri.appendChild(arata);
        }
        panou.appendChild(linkuri);
      }
    }

    function urmatoarea() {
      state.curent++;
      if (state.curent < total) arataIntrebare();
      else ecranScor();
    }

    tasteEcran = function (e) {
      var n = -1;
      if (/^[1-9]$/.test(e.key)) n = +e.key - 1;
      else if (/^[a-z]$/i.test(e.key)) n = e.key.toUpperCase().charCodeAt(0) - 65;
      if (n >= 0 && n < q.variante.length && !verificat) { e.preventDefault(); alege(n); return; }
      if (e.key === "Enter" && !btnPrincipal.disabled) { e.preventDefault(); btnPrincipal.click(); }
    };
    scrollSus();
  }

  /* ---------- Ecranul de scor ---------- */
  function ecranScor() {
    document.body.classList.remove("in-test");
    tasteEcran = null;
    if (state.esteTestComplet) scrie(CHEIE_IN_LUCRU, null);
    root.innerHTML = "";
    var wrap = el("div", "rezultat");
    var total = state.ordine.length;
    var pct = Math.round((state.corecte / total) * 100);

    var vechi = state.esteTestComplet && state.test ? scoruri()[state.test] : null;
    if (state.esteTestComplet && state.test) salveazaScor(state.test, pct, state.corecte, total);

    var corectaLa = {};
    state.ordine.forEach(function (qi) { corectaLa[qi] = seturiEgale(state.raspunsuri[qi] || [], INTREBARI[qi].corecte); });

    var cap = el("section", "rezultat-cap");
    var mesaj = pct === 100 ? "Fără nicio greșeală." :
      pct >= PRAG_BUN ? "Scor bun, peste pragul de 70%." :
      pct >= PRAG_MEDIU ? "Mai e de lucru: citește explicațiile greșelilor de mai jos." :
      "Reia materia pornind de la articolele de mai jos.";
    var record = "";
    if (vechi && vechi.best) record = pct > vechi.best ? "Record nou · înainte " + vechi.best + "%" : "Cel mai bun: " + vechi.best + "%";
    cap.innerHTML =
      '<span class="eyebrow">' + esc(state.titlu) + " · rezultat</span>" +
      '<div class="scor-rand"><div><div class="scor-mare">' + state.corecte + "<small>/" + total + "</small></div>" +
      '<p class="mesaj"><span class="rezultat-pct">' + pct + "%</span> · " + mesaj + "</p></div>" +
      (record ? '<div class="record">' + esc(record) + "</div>" : "") + "</div>";
    var grilaQ = el("div", "grila-q");
    if (total < 10) grilaQ.style.gridTemplateColumns = "repeat(" + total + ", minmax(0, 1fr))";
    grilaQ.setAttribute("aria-label", "Rezultatul pe fiecare întrebare");
    state.ordine.forEach(function (qi, i) {
      if (corectaLa[qi]) grilaQ.appendChild(el("span", null, String(i + 1)));
      else {
        var l = el("a", null, String(i + 1));
        l.href = "#gresala-" + (i + 1);
        l.setAttribute("aria-label", "Întrebarea " + (i + 1) + ", greșită");
        l.addEventListener("click", function () {
          var d = document.getElementById("gresala-" + (i + 1));
          if (d) d.open = true;
        });
        grilaQ.appendChild(l);
      }
    });
    cap.appendChild(grilaQ);
    wrap.appendChild(cap);

    /* pe acte normative */
    var grupe = {}, ordineGrupe = [];
    state.ordine.forEach(function (qi) {
      var g = actul(INTREBARI[qi]).grupa;
      if (!grupe[g]) { grupe[g] = { total: 0, corecte: 0 }; ordineGrupe.push(g); }
      grupe[g].total++;
      if (corectaLa[qi]) grupe[g].corecte++;
    });
    if (ordineGrupe.length > 1) {
      var sAct = el("section", "sectiune");
      sAct.appendChild(el("h2", "titlu-sectiune", "Pe acte normative"));
      var tabel = el("div", "tabel-acte");
      ordineGrupe.sort(function (x, y) { return grupe[y].total - grupe[x].total; }).forEach(function (g) {
        var d = grupe[g], r = el("div", "rand-act");
        var puncte = el("div", "puncte");
        puncte.style.gridTemplateColumns = "repeat(" + Math.max(d.total, 8) + ", minmax(0, 1fr))";
        for (var i = 0; i < d.total; i++) puncte.appendChild(el("i", i < d.corecte ? "ok" : ""));
        r.appendChild(el("span", "nume", esc(GRUPE[g] ? GRUPE[g].nume : g)));
        r.appendChild(puncte);
        r.appendChild(el("span", "scor ton-" + ton(d.corecte / d.total * 100), d.corecte + "/" + d.total));
        tabel.appendChild(r);
      });
      sAct.appendChild(tabel);
      wrap.appendChild(sAct);
    }

    function itemRecap(qi, i, gresit) {
      var q = INTREBARI[qi], a = actul(q);
      var d = el("details", "recap-item" + (gresit ? "" : " bun"));
      if (gresit) d.id = "gresala-" + (i + 1);
      var sum = el("summary");
      sum.innerHTML = '<span class="nr">' + (i + 1) + '</span><span class="cap"><span class="q">' + esc(q.intrebare) +
        '</span><span class="ref">' + esc(a.scurt) + " · " + esc(q.sursa.articol) + "</span></span>" +
        '<span class="chevron">' + icon("chevron", 18) + "</span>";
      d.appendChild(sum);
      d.appendChild(corpExplicatie(q, gresit ? (state.raspunsuri[qi] || []) : null));
      return d;
    }

    var gresite = [];
    state.ordine.forEach(function (qi) { if (!corectaLa[qi]) gresite.push(qi); });
    if (gresite.length) {
      var sG = el("section", "sectiune");
      sG.appendChild(el("div", "cap-sectiune", '<h2 class="titlu-sectiune">Greșeli (' + gresite.length + ')</h2><span class="nota">atinge pentru explicație</span>'));
      var lg = el("div", "lista-gresite");
      state.ordine.forEach(function (qi, i) { if (!corectaLa[qi]) lg.appendChild(itemRecap(qi, i, true)); });
      sG.appendChild(lg);
      wrap.appendChild(sG);
    }
    var nrBune = total - gresite.length;
    if (nrBune) {
      var alte = el("details", "alte");
      alte.appendChild(el("summary", null, "Răspunsuri corecte (" + nrBune + ")"));
      var lb = el("div", "lista-gresite");
      state.ordine.forEach(function (qi, i) { if (corectaLa[qi]) lb.appendChild(itemRecap(qi, i, false)); });
      alte.appendChild(lb);
      wrap.appendChild(alte);
    }

    var acts = el("div", "actions");
    var titluAnterior = state.titlu, testAnterior = state.test;
    if (gresite.length) {
      var btnGresite = el("button", "btn btn-primary", "Repetă " + (gresite.length === 1 ? "greșeala" : "cele " + gresite.length + " greșeli"));
      btnGresite.type = "button";
      btnGresite.addEventListener("click", function () {
        porneste(testAnterior, gresite, false, titluAnterior.split(" · greșelile")[0] + " · greșelile");
      });
      acts.appendChild(btnGresite);
    }
    if (testAnterior) {
      var btnRestart = el("button", gresite.length ? "btn btn-outline" : "btn btn-primary", "Reia testul " + testAnterior);
      btnRestart.type = "button";
      btnRestart.addEventListener("click", function () { porneste(testAnterior, intrebariTest(testAnterior), true, "Testul " + testAnterior); });
      acts.appendChild(btnRestart);
      if (state.esteTestComplet && testAnterior < NR_TESTE) {
        var btnUrm = el("button", "btn btn-outline", "Testul " + (testAnterior + 1));
        btnUrm.type = "button";
        btnUrm.addEventListener("click", function () { porneste(testAnterior + 1, intrebariTest(testAnterior + 1), true, "Testul " + (testAnterior + 1)); });
        acts.appendChild(btnUrm);
      }
    }
    var btnHome = el("button", "btn btn-outline", "Toate testele");
    btnHome.type = "button";
    btnHome.addEventListener("click", function () { ecranStart([]); });
    acts.appendChild(btnHome);
    wrap.appendChild(acts);

    root.appendChild(wrap);
    scrollSus();
  }

  /* ---------- Tastatura ---------- */
  document.addEventListener("keydown", function (e) {
    if (!tasteEcran || e.ctrlKey || e.metaKey || e.altKey) return;
    var t = e.target;
    if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable)) return;
    // Enter pe un buton sau link cu focus îl apasă deja browserul — mai puțin pe variante,
    // unde focusul rămâne după click și Enter trebuie să verifice, nu să comute varianta.
    var peVarianta = t && t.classList && t.classList.contains("option");
    if (e.key === "Enter" && t && !peVarianta && (t.tagName === "BUTTON" || t.tagName === "A" || t.tagName === "SUMMARY")) return;
    tasteEcran(e);
  });

  /* ---------- Init ---------- */
  var erori = typeof INTREBARI === "undefined"
    ? ["Fișierul intrebari.js nu a putut fi încărcat (INTREBARI nu există)."]
    : valideazaIntrebari(INTREBARI);
  if (erori.length) erori.forEach(function (e) { console.warn("[validare]", e); });
  if (typeof INTREBARI !== "undefined") INTREBARI.forEach(function (q, i) { if (q && q.id) indexDupaId[q.id] = i; });
  ecranStart(erori);

  /* index.html?titlu=Tema%207&intrebari=ID1,ID2,… — butonul „Exersează tema” din paginile de tematică */
  var parametri = new URLSearchParams(location.search);
  var dinTema = (parametri.get("intrebari") || "").split(",").map(idx).filter(function (i) { return i >= 0; });
  if (dinTema.length) {
    history.replaceState(null, "", location.pathname);   // o reîncărcare nu mai repornește exersarea
    if (!erori.length) porneste(null, alegePentruExersare(dinTema), false, parametri.get("titlu") || "Exersare");
  }
})();
