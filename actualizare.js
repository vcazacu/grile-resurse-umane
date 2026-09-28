/* Trecerea la versiunea nouă. sw.js servește întâi din cache, deci la prima deschidere după o actualizare
   pagina rulează încă fișierele vechi; noul service worker se instalează în fundal și preia pagina câteva
   secunde mai târziu („controllerchange” și mesajul „versiune-noua”). Atunci reîncărcăm: imediat dacă nu
   e o întrebare pe ecran, altfel la cerere (bara se poate închide cu ×), ca să nu se piardă răspunsul în
   curs. La revenirea în aplicație (pe iPad rămâne deschisă în fundal) cerem o verificare a versiunii, ca
   actualizarea să nu aștepte o redeschidere. Scriptul stă în <head>, înaintea celorlalte. */
(function () {
  if (!("serviceWorker" in navigator) || location.protocol.indexOf("http") !== 0) return;
  var sw = navigator.serviceWorker;
  if (!sw.controller) return; // prima instalare: pagina tocmai a venit din rețea, e deja la zi
  var preluat = false;
  function versiuneNoua() {
    if (preluat) return;
    preluat = true;
    if (!document.querySelector(".question-text")) { location.reload(); return; }
    var bara = document.createElement("div");
    bara.className = "bara-versiune";
    bara.setAttribute("role", "status");
    bara.innerHTML = '<span>A apărut o versiune nouă a aplicației.</span>' +
      '<button type="button" class="btn btn-primary">Reîncarcă</button>' +
      '<button type="button" class="btn-icon" aria-label="Închide"><svg width="20" height="20" viewBox="0 0 24 24" ' +
      'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">' +
      '<line x1="6" y1="6" x2="18" y2="18"></line><line x1="18" y1="6" x2="6" y2="18"></line></svg></button>';
    bara.querySelector(".btn-primary").addEventListener("click", function () { location.reload(); });
    // Închisă, bara nu mai revine; versiunea nouă pornește la următoarea deschidere.
    bara.querySelector(".btn-icon").addEventListener("click", function () { bara.remove(); });
    document.body.appendChild(bara);
  }
  // Două semnale, pentru că primul se poate pierde: „controllerchange” vine o singură dată și, dacă noul
  // service worker se activează înainte ca pagina să ajungă la acest script, nu-l mai aude nimeni; mesajul
  // „versiune-noua” din sw.js e păstrat de browser până se încarcă pagina.
  sw.addEventListener("controllerchange", versiuneNoua);
  sw.addEventListener("message", function (e) { if (e.data && e.data.tip === "versiune-noua") versiuneNoua(); });
  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState !== "visible") return;
    sw.getRegistration().then(function (r) { if (r) r.update(); }).catch(function () {});
  });
})();
