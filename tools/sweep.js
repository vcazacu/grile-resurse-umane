// Parcurge toate testele din pagină (câte butoane .test-btn există — 30 la resurse umane) răspunzând cu cheile
// din INTREBARI; rezultatul în window.__sweep = {teste: [{t, pct}], erori: [str]}.
// Se lipește în pagină cu unealta javascript_tool a panoului de browser, la index.html.
(async function () {
  const pauza = () => new Promise(r => setTimeout(r, 0));
  const out = { teste: [], erori: [] };
  const buton = txt => [...document.querySelectorAll("button.btn")].find(b => b.textContent.trim().startsWith(txt));
  const nrTeste = document.querySelectorAll(".test-btn").length;
  if (!nrTeste) out.erori.push("niciun buton de test pe pagină");
  for (let t = 1; t <= nrTeste; t++) {
    const tb = document.querySelectorAll(".test-btn")[t - 1];
    if (!tb) { out.erori.push("lipsește butonul testului " + t); break; }
    tb.click(); await pauza();
    for (let pas = 0; pas < 25; pas++) {
      const qt = document.querySelector(".question-text");
      if (!qt) break;
      const q = INTREBARI.find(x => x.test === t && x.intrebare === qt.textContent);
      if (!q) { out.erori.push("t" + t + ": întrebare negăsită: " + qt.textContent.slice(0, 60)); break; }
      const opt = document.querySelectorAll(".option");
      q.corecte.forEach(i => opt[i].click()); await pauza();
      const v = buton("Verifică"); if (v) { v.click(); await pauza(); }
      const next = [...document.querySelectorAll("button.btn-primary")].pop();
      next.click(); await pauza();
    }
    const big = document.querySelector(".rezultat-pct");
    out.teste.push({ t, pct: big ? big.textContent : "?" });
    const toate = buton("Toate testele"); if (toate) { toate.click(); await pauza(); }
  }
  window.__sweep = out;
})();
