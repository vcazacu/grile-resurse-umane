/* Logica aplicației de quiz — fără dependențe externe */
(function () {
  "use strict";

  var root = document.getElementById("app");
  var NR_TESTE = 30;
  var STORAGE_KEY = "grile-ru-scoruri";

  var state = {
    test: null,      // numărul testului curent (1..30)
    ordine: [],      // indecșii întrebărilor în ordinea de joc
    curent: 0,       // poziția în ordine
    raspunsuri: {},  // idxIntrebare -> [indecși selectați]
    corecte: 0,
    esteTestComplet: false, // true dacă rulăm un test întreg (scorul se salvează)
    amesteca: false
  };

  /* ---------- Scoruri salvate local ---------- */
  function scoruri() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}; }
    catch (e) { return {}; }
  }
  function salveazaScor(test, pct, corecte, total) {
    try {
      var s = scoruri();
      var vechi = s[test];
      s[test] = {
        pct: pct, corecte: corecte, total: total,
        best: Math.max(pct, vechi && vechi.best ? vechi.best : 0)
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
    } catch (e) { /* localStorage indisponibil — ignorăm */ }
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
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
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
  function litera(i) { return String.fromCharCode(65 + i); }
  var CHEVRON = '<svg class="chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="6 9 12 15 18 9"></polyline></svg>';

  function seturiEgale(a, b) {
    if (a.length !== b.length) return false;
    var s = {};
    a.forEach(function (x) { s[x] = true; });
    return b.every(function (x) { return s[x]; });
  }
  function intrebariTest(t) {
    var idx = [];
    INTREBARI.forEach(function (q, i) { if (q.test === t) idx.push(i); });
    return idx;
  }

  /* ---------- Componente ---------- */
  function accordionExplicatie(q, deschis) {
    var d = el("details", "accordion");
    if (deschis) d.setAttribute("open", "");
    var sum = el("summary");
    sum.innerHTML = "<span>Explicație și temei legal</span>" + CHEVRON;
    d.appendChild(sum);

    var body = el("div", "accordion-body");
    body.appendChild(el("div", "explic-section-title", "Explicație"));
    body.appendChild(el("p", "explic-text", esc(q.explicatie)));
    body.appendChild(el("div", "explic-section-title", "Temei legal"));

    var legal = el("div", "legal-card");
    legal.appendChild(el("div", "act", esc(q.sursa.act)));
    legal.appendChild(el("span", "articol", esc(q.sursa.articol)));
    legal.appendChild(el("blockquote", null, "„" + esc(q.sursa.citat) + "”"));
    if (q.sursa.fisier) legal.appendChild(el("div", "fisier", "Sursă: " + esc(q.sursa.fisier)));
    body.appendChild(legal);
    d.appendChild(body);
    return d;
  }

  function textVariante(q, indecsi) {
    return indecsi.map(function (i) { return litera(i) + ") " + q.variante[i]; }).join("; ");
  }

  /* ---------- Ecranul de start: alegerea testului ---------- */
  function ecranStart(eroriValidare) {
    root.innerHTML = "";
    var wrap = el("div");

    if (eroriValidare.length) {
      var maxAfisate = 15;
      var listate = eroriValidare.slice(0, maxAfisate);
      var rest = eroriValidare.length - listate.length;
      var v = el("div", "validation-error",
        "<strong>Banca de întrebări conține erori — corectează intrebari.js:</strong>" +
        "<ul>" + listate.map(function (e) { return "<li>" + esc(e) + "</li>"; }).join("") + "</ul>" +
        (rest > 0 ? "<div>… și încă " + rest + " erori (vezi consola browserului).</div>" : ""));
      wrap.appendChild(v);
    }

    var hero = el("div", "hero");
    hero.appendChild(el("div", "emoji", "🪖"));
    hero.appendChild(el("h2", null, "Alege un test"));
    hero.appendChild(el("p", null,
      NR_TESTE + " de teste a câte 20 de întrebări, pe legislația în formă consolidată. " +
      "Feedback imediat, cu explicația detaliată și articolul exact din lege."));
    wrap.appendChild(hero);

    var nrMulti = INTREBARI.filter(function (q) { return q.tip === "multiplu"; }).length;
    var nrVerif = INTREBARI.filter(function (q) { return q.status === "de verificat"; }).length;
    var meta = el("div", "meta-list");
    meta.appendChild(el("span", "badge", INTREBARI.length + " întrebări"));
    meta.appendChild(el("span", "badge multi", nrMulti + " cu răspunsuri multiple"));
    if (nrVerif) meta.appendChild(el("span", "badge warn", nrVerif + " de verificat"));
    wrap.appendChild(meta);

    var card = el("div", "card");
    var lbl = el("label");
    lbl.style.cssText = "display:flex;align-items:center;gap:0.6rem;min-height:2.2rem;cursor:pointer;font-size:0.92rem;margin-bottom:0.8rem;";
    var chk = el("input");
    chk.type = "checkbox";
    chk.id = "chk-shuffle";
    chk.checked = state.amesteca;
    chk.style.cssText = "width:1.15rem;height:1.15rem;accent-color:var(--primary);";
    chk.addEventListener("change", function () { state.amesteca = chk.checked; });
    lbl.appendChild(chk);
    lbl.appendChild(document.createTextNode("Amestecă ordinea întrebărilor în test"));
    card.appendChild(lbl);

    var s = scoruri();
    var grid = el("div", "test-grid");
    for (var t = 1; t <= NR_TESTE; t++) {
      (function (t) {
        var idx = intrebariTest(t);
        var b = el("button", "test-btn");
        b.type = "button";
        var scor = s[t];
        b.innerHTML = '<span class="nr">Test ' + t + "</span>" +
          (scor
            ? '<span class="scor ' + (scor.best >= 70 ? "ok" : scor.best >= 50 ? "mid" : "slab") + '">' + scor.best + "%</span>"
            : '<span class="scor gol">—</span>');
        b.disabled = eroriValidare.length > 0 || idx.length === 0;
        b.addEventListener("click", function () { porneste(t, idx, true); });
        grid.appendChild(b);
      })(t);
    }
    card.appendChild(grid);
    wrap.appendChild(card);

    wrap.appendChild(el("footer", null,
      "Surse: formele consolidate la zi de pe legislatie.just.ro (Portal Legislativ), descărcate în folderul legislatie/.<br>" +
      "Legea 80/1995 · Legea 1/1998 · Codul muncii · Legea 223/2015 · Legea 360/2023 · Legea-cadru 153/2017 (+ anexa VI) · O.U.G. 111/2010 · H.G. 52/2011 · H.G. 1867/2005"));
    root.appendChild(wrap);
    window.scrollTo(0, 0);
  }

  /* ---------- Pornirea unui test / subset ---------- */
  function porneste(test, subset, esteComplet) {
    var idx = subset.slice();
    if (state.amesteca) {
      var perm = amestecat(idx.length);
      idx = perm.map(function (p) { return idx[p]; });
    }
    state.test = test;
    state.ordine = idx;
    state.curent = 0;
    state.raspunsuri = {};
    state.corecte = 0;
    state.esteTestComplet = !!esteComplet;
    arataIntrebare();
  }

  /* ---------- Ecranul unei întrebări ---------- */
  function arataIntrebare() {
    var qIdx = state.ordine[state.curent];
    var q = INTREBARI[qIdx];
    var selectate = [];
    var verificat = false;

    root.innerHTML = "";
    var wrap = el("div");

    var prog = el("div", "progress-wrap");
    var pct = Math.round((state.curent / state.ordine.length) * 100);
    prog.appendChild(el("div", "progress-label",
      "<span>Test " + state.test + " · întrebarea " + (state.curent + 1) + " din " + state.ordine.length +
      "</span><span>" + pct + "%</span>"));
    var bar = el("div", "progress-bar");
    bar.appendChild(el("div", null, ""));
    bar.firstChild.style.width = pct + "%";
    prog.appendChild(bar);
    wrap.appendChild(prog);

    var card = el("div", "card");
    card.appendChild(el("span", "badge", esc(q.sursa.act.split(" privind")[0].split(" (anexa")[0])));
    if (q.tip === "multiplu") card.appendChild(el("span", "badge multi", "Alege toate răspunsurile corecte"));
    if (q.status === "de verificat") card.appendChild(el("span", "badge warn", "⚠ De verificat"));
    card.appendChild(el("div", "question-text", esc(q.intrebare)));

    var optiuni = el("div", "options");
    var butoane = [];
    q.variante.forEach(function (v, i) {
      var b = el("button", "option");
      b.type = "button";
      b.dataset.mode = q.tip;
      b.innerHTML = '<span class="marker">' + (q.tip === "multiplu" ? "✓" : "●") + "</span><span>" +
        "<strong>" + litera(i) + ")</strong> " + esc(v) + "</span>";
      b.addEventListener("click", function () {
        if (verificat) return;
        if (q.tip === "unic") {
          selectate = [i];
          verifica();
        } else {
          var poz = selectate.indexOf(i);
          if (poz >= 0) { selectate.splice(poz, 1); b.classList.remove("selected"); }
          else { selectate.push(i); b.classList.add("selected"); }
          btnVerifica.disabled = selectate.length === 0;
        }
      });
      butoane.push(b);
      optiuni.appendChild(b);
    });
    card.appendChild(optiuni);

    var zonaJos = el("div");
    card.appendChild(zonaJos);

    var btnVerifica = null;
    if (q.tip === "multiplu") {
      var acts = el("div", "actions");
      btnVerifica = el("button", "btn btn-primary", "Verifică răspunsul");
      btnVerifica.disabled = true;
      btnVerifica.addEventListener("click", verifica);
      acts.appendChild(btnVerifica);
      zonaJos.appendChild(acts);
    }

    function verifica() {
      verificat = true;
      state.raspunsuri[qIdx] = selectate.slice();
      var esteCorect = seturiEgale(selectate, q.corecte);
      if (esteCorect) state.corecte++;

      butoane.forEach(function (b, i) {
        b.disabled = true;
        b.classList.remove("selected");
        var eCorecta = q.corecte.indexOf(i) >= 0;
        var eAleasa = selectate.indexOf(i) >= 0;
        if (eCorecta && eAleasa) {
          b.classList.add("correct");
          b.innerHTML += '<span class="tag">corect</span>';
        } else if (!eCorecta && eAleasa) {
          b.classList.add("incorrect");
          b.innerHTML += '<span class="tag">greșit</span>';
        } else if (eCorecta && !eAleasa) {
          b.classList.add("missed");
          b.innerHTML += '<span class="tag">răspuns corect</span>';
        }
      });

      zonaJos.innerHTML = "";
      var verdict;
      if (esteCorect) {
        verdict = el("div", "verdict ok", '<span class="icon">✓</span><span>Corect!</span>');
      } else {
        verdict = el("div", "verdict bad",
          '<span class="icon">✗</span><span>Greșit.<span class="sub">Răspunsul corect: <strong>' +
          esc(textVariante(q, q.corecte)) + "</strong></span></span>");
      }
      zonaJos.appendChild(verdict);
      zonaJos.appendChild(accordionExplicatie(q, !esteCorect));

      var acts = el("div", "actions");
      var btnNext = el("button", "btn btn-primary",
        state.curent + 1 < state.ordine.length ? "Întrebarea următoare →" : "Vezi rezultatul");
      btnNext.addEventListener("click", function () {
        state.curent++;
        if (state.curent < state.ordine.length) arataIntrebare();
        else ecranScor();
      });
      acts.appendChild(btnNext);
      zonaJos.appendChild(acts);
      btnNext.focus({ preventScroll: true });
    }

    wrap.appendChild(card);
    root.appendChild(wrap);
    window.scrollTo(0, 0);
  }

  /* ---------- Ecranul de scor ---------- */
  function ecranScor() {
    root.innerHTML = "";
    var wrap = el("div");
    var total = state.ordine.length;
    var pct = Math.round((state.corecte / total) * 100);

    if (state.esteTestComplet && state.test) salveazaScor(state.test, pct, state.corecte, total);

    var hero = el("div", "hero");
    hero.appendChild(el("h2", null, "Rezultat — Test " + state.test));
    var ring = el("div", "score-ring");
    ring.style.setProperty("--pct", pct);
    ring.style.setProperty("--ring-color", pct >= 70 ? "var(--success)" : pct >= 50 ? "var(--warning)" : "var(--destructive)");
    ring.appendChild(el("div", "big", pct + "%"));
    ring.appendChild(el("div", "small", state.corecte + " din " + total + " corecte"));
    hero.appendChild(ring);
    var mesaj = pct === 100 ? "Excelent — fără nicio greșeală!" :
      pct >= 70 ? "Bun! Recapitulează mai jos greșelile." :
      pct >= 50 ? "Mai e de lucru — citește explicațiile de mai jos." :
      "Reia materia pornind de la articolele de mai jos.";
    hero.appendChild(el("p", null, mesaj));
    wrap.appendChild(hero);

    var gresite = state.ordine.filter(function (qIdx) {
      return !seturiEgale(state.raspunsuri[qIdx] || [], INTREBARI[qIdx].corecte);
    });

    if (gresite.length) {
      wrap.appendChild(el("div", "explic-section-title", "Recapitularea greșelilor (" + gresite.length + ")"));
      gresite.forEach(function (qIdx) {
        var q = INTREBARI[qIdx];
        var item = el("div", "recap-item wrong");
        var head = el("div", "recap-head");
        head.appendChild(el("span", "ico", "✗"));
        head.appendChild(el("div", "q", esc(q.intrebare)));
        item.appendChild(head);
        var ans = el("div", "recap-answers");
        var alTau = (state.raspunsuri[qIdx] || []);
        ans.innerHTML =
          '<div class="yours">Răspunsul tău: ' + (alTau.length ? esc(textVariante(q, alTau)) : "—") + "</div>" +
          '<div class="good">Corect: ' + esc(textVariante(q, q.corecte)) + "</div>";
        item.appendChild(ans);
        item.appendChild(accordionExplicatie(q, false));
        wrap.appendChild(item);
      });
    }

    var corecteList = state.ordine.filter(function (qIdx) {
      return seturiEgale(state.raspunsuri[qIdx] || [], INTREBARI[qIdx].corecte);
    });
    if (corecteList.length) {
      wrap.appendChild(el("div", "explic-section-title", "Răspunsuri corecte (" + corecteList.length + ")"));
      corecteList.forEach(function (qIdx) {
        var q = INTREBARI[qIdx];
        var item = el("div", "recap-item right");
        var head = el("div", "recap-head");
        head.appendChild(el("span", "ico", "✓"));
        head.appendChild(el("div", "q", esc(q.intrebare)));
        item.appendChild(head);
        wrap.appendChild(item);
      });
    }

    var acts = el("div", "actions");
    if (gresite.length) {
      var btnGresite = el("button", "btn btn-primary", "Repetă doar greșelile (" + gresite.length + ")");
      btnGresite.addEventListener("click", function () { porneste(state.test, gresite, false); });
      acts.appendChild(btnGresite);
    }
    var btnRestart = el("button", gresite.length ? "btn btn-outline" : "btn btn-primary", "Reia testul " + state.test);
    (function (t) {
      btnRestart.addEventListener("click", function () { porneste(t, intrebariTest(t), true); });
    })(state.test);
    acts.appendChild(btnRestart);
    var btnHome = el("button", "btn btn-outline", "Toate testele");
    btnHome.addEventListener("click", function () { ecranStart([]); });
    acts.appendChild(btnHome);
    wrap.appendChild(acts);

    root.appendChild(wrap);
    window.scrollTo(0, 0);
  }

  /* ---------- Init ---------- */
  var erori = typeof INTREBARI === "undefined"
    ? ["Fișierul intrebari.js nu a putut fi încărcat (INTREBARI nu există)."]
    : valideazaIntrebari(INTREBARI);
  if (erori.length) erori.forEach(function (e) { console.warn("[validare]", e); });
  ecranStart(erori);
})();
