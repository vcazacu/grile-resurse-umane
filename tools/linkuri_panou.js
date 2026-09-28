// Verifică linkurile din panoul „Temei legal” („Deschide în lege” și articolul întreg copiat din pagina
// de legislație):
// parcurge toate testele ca sweep.js, după „Verifică” așteaptă articolul și strânge linkurile, apoi
// încarcă fiecare pagină-țintă și caută ancora. Rezultatul în window.__linkuri =
// {intrebari, aparitii (linkuri văzute), linkuri (distincte), rupte: [{id, href, motiv}], fara_articol: [id], erori: [str]}.
// Cere lățime ≥ 1024 px (acolo panoul aduce singur articolul) și pagina servită prin http.
(async function () {
  const pauza = ms => new Promise(r => setTimeout(r, ms || 0));
  const out = { intrebari: 0, aparitii: 0, linkuri: 0, rupte: [], fara_articol: [], erori: [] };
  const buton = txt => [...document.querySelectorAll("button.btn")].find(b => b.textContent.trim().startsWith(txt));
  const gasite = new Map(); // href absolut -> primul id de întrebare
  const nrTeste = document.querySelectorAll(".test-btn").length;
  if (!nrTeste) out.erori.push("niciun buton de test pe pagină");
  for (let t = 1; t <= nrTeste; t++) {
    document.querySelectorAll(".test-btn")[t - 1].click(); await pauza();
    for (let pas = 0; pas < 25; pas++) {
      const qt = document.querySelector(".question-text");
      if (!qt) break;
      const q = INTREBARI.find(x => x.test === t && x.intrebare === qt.textContent);
      if (!q) { out.erori.push("t" + t + ": întrebare negăsită"); break; }
      const opt = document.querySelectorAll(".option");
      q.corecte.forEach(i => opt[i].click()); await pauza();
      const v = buton("Verifică"); if (v) { v.click(); await pauza(); }
      out.intrebari++;
      // Panoul trebuie să fie al întrebării curente (referința ei) și articolul încărcat — altfel am citi
      // panoul vechi sau „Se încarcă…” și am sări linkuri fără să știm.
      let stare = "neîncărcat", cutie = null;
      for (let i = 0; i < 250 && stare === "neîncărcat"; i++) {
        const ref = document.querySelector(".panou-lege .lege-act .ref");
        cutie = document.querySelector(".panou-lege .articol-intreg");
        if (ref && ref.textContent === q.sursa.articol && cutie) {
          // mesajele aplicației sunt un <p class="stare"> direct în cutie; după text nu se poate judeca,
          // pentru că articolul însuși poate conține „nu s-a putut” (art. 85 din Legea 80/1995)
          const mesaj = cutie.querySelector(":scope > p.stare");
          if (mesaj && /nu apare separat/.test(mesaj.textContent)) stare = "fără articol";
          else if (mesaj && /nu s-a putut/.test(mesaj.textContent)) stare = "neîncărcat-eroare";
          else if (!mesaj && cutie.firstElementChild) stare = "gata";
        }
        if (stare === "neîncărcat") await pauza(20);
      }
      if (stare === "neîncărcat") out.erori.push(q.id + ": panoul întrebării nu s-a încărcat");
      else if (stare === "neîncărcat-eroare") out.erori.push(q.id + ": textul legii nu s-a putut încărca");
      else if (stare === "fără articol") out.fara_articol.push(q.id);
      else document.querySelectorAll(".panou-lege a[href]").forEach(a => {
        out.aparitii++;
        if (!gasite.has(a.href)) gasite.set(a.href, q.id);
      });
      [...document.querySelectorAll("button.btn-primary")].pop().click(); await pauza();
    }
    const toate = buton("Toate testele"); if (toate) { toate.click(); await pauza(); }
  }
  out.linkuri = gasite.size;
  const pagini = {};
  for (const [href, id] of gasite) {
    const u = new URL(href), pag = u.origin + u.pathname;
    if (u.origin !== location.origin) continue;
    if (!(pag in pagini)) {
      pagini[pag] = await fetch(pag).then(r => r.ok ? r.text() : null).catch(() => null)
        .then(t => t && new DOMParser().parseFromString(t, "text/html"));
    }
    const doc = pagini[pag];
    if (!doc) { out.rupte.push({ id, href, motiv: "pagina nu există" }); continue; }
    const anc = decodeURIComponent(u.hash.slice(1));
    if (anc && !doc.getElementById(anc)) out.rupte.push({ id, href, motiv: "ancora nu există" });
  }
  window.__linkuri = out;
})();
