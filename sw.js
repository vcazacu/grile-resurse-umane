/* Service worker — face aplicația disponibilă offline după prima deschidere.
   La fiecare modificare a întrebărilor, schimbă VERSIUNE ca să se reîmprospăteze cache-ul. */
const VERSIUNE = "grile-ru-v27";
const FISIERE = [
  "./",
  "./index.html",
  "./style.css",
  "./app.js",
  "./actualizare.js",
  "./intrebari.js",
  "./manifest.json",
  "./icon-192.png",
  "./icon-512.png",
  "./apple-touch-icon.png",
  /* TEMATICA-START */
  "./tematica/index.html",
  "./tematica/01-gradele-militare-si-stagiile-minime-in-grad.html",
  "./tematica/02-indatoririle-si-drepturile-cadrelor-militare.html",
  "./tematica/03-interzicerea-sau-restrangerea-unor-drepturi.html",
  "./tematica/04-provenienta-ofiterilor-maistrilor-si-subofiterilor.html",
  "./tematica/05-disciplina-militara.html",
  "./tematica/06-acordarea-gradelor-si-inaintarea-in-grad.html",
  "./tematica/07-trecerea-in-rezerva-sau-in-retragere.html",
  "./tematica/08-organizarea-si-functionarea-sie.html",
  "./tematica/09-contractul-individual-de-munca.html",
  "./tematica/10-tipurile-de-contract-individual-de-munca.html",
  "./tematica/11-timpul-de-munca-si-timpul-de-odihna.html",
  "./tematica/12-raspunderea-disciplinara-a-salariatilor.html",
  "./tematica/13-sistemul-pensiilor-militare-de-stat.html",
  "./tematica/14-sistemul-public-de-pensii.html",
  "./tematica/15-salarizarea-personalului-militar-si-contractual.html",
  "./tematica/16-concediul-si-indemnizatia-pentru-cresterea-copiilor.html",
  "./tematica/17-stimulentul-de-insertie.html",
  "./tematica/18-compensatia-lunara-pentru-chirie.html",
  /* TEMATICA-END */
  /* LEGISLATIE-START */
  "./legislatie/index.html",
  "./legislatie/01-legea-80-1995-statutul-cadrelor-militare.html",
  "./legislatie/02-legea-1-1998-organizarea-sie.html",
  "./legislatie/03-legea-53-2003-codul-muncii.html",
  "./legislatie/04-legea-223-2015-pensiile-militare.html",
  "./legislatie/05-legea-360-2023-sistemul-public-de-pensii.html",
  "./legislatie/06-legea-153-2017-salarizarea-bugetara.html",
  "./legislatie/07-oug-111-2010-concediul-crestere-copil.html",
  "./legislatie/08-norme-hg-52-2011-aplicare-oug-111-2010.html",
  "./legislatie/09-hg-1867-2005-compensatia-chirie.html",
  /* LEGISLATIE-END */
  /* SPETE-START */
  "./spete/index.html",
  "./spete/01-plutonierul-major-care-cere-inaintarea-in-grad.html",
  "./spete/02-trei-feluri-de-vechime-pentru-acelasi-capitan.html",
  "./spete/03-compensatia-de-chirie-casa-construita-cu-credit-si-decizia.html",
  "./spete/04-mustrarea-scrisa-aplicata-la-opt-luni-dupa-constatare.html",
  "./spete/05-vaduva-cu-12-ani-de-casatorie-si-pensia-de-urmas.html",
  "./spete/06-doi-subofiteri-in-ture-de-noapte-si-sporul-de-25.html",
  "./spete/07-capitanul-care-isi-urmeaza-sotia-la-ambasada.html",
  "./spete/08-maiorul-trecut-in-rezerva-prin-reorganizare-la-48-de-ani.html",
  "./spete/09-recalcularea-indemnizatiei-de-crestere-a-copilului-dupa-ce.html",
  "./spete/10-referenta-civila-delegata-inca-60-de-zile-fara-sa-fie.html",
  "./spete/11-locotenentul-in-rezerva-care-cere-gradul-de-capitan-dupa-5.html",
  "./spete/12-colonelul-care-implineste-varsta-standard-si-vrea-sa-mai.html",
  "./spete/13-cine-aproba-structura-sie-si-cine-numeste-adjunctii.html",
  "./spete/14-perioada-de-proba-de-120-de-zile-pentru-un-referent.html",
  "./spete/15-demisia-pe-care-angajatorul-refuza-sa-o-inregistreze.html",
  "./spete/16-concediul-de-odihna-neefectuat-cerut-in-bani.html",
  "./spete/17-sergentul-accidentat-in-concediu-si-pensia-de-invaliditate.html",
  "./spete/18-pensia-pentru-limita-de-varsta-cu-13-ani-de-stagiu.html",
  "./spete/19-mama-care-se-intoarce-la-serviciu-la-5-luni-ale-copilului.html",
  "./spete/20-chiria-platita-parintilor-si-cei-doi-soti-militari.html",
  "./spete/21-al-patrulea-contract-pe-durata-determinata.html",
  "./spete/22-orele-suplimentare-care-se-pierd.html",
  "./spete/23-patru-inaintari-in-grad-patru-semnaturi-diferite.html",
  "./spete/24-al-doilea-copil-nascut-in-timpul-concediului-pentru-primul.html",
  "./spete/25-rata-creditului-intr-o-comuna-si-compensatia-de-40.html",
  "./spete/26-pensia-anticipata-cu-doi-ani-inainte-si-reducerea-care-nu.html",
  "./spete/27-capitanul-plecat-la-cerere-cu-12-ani-de-serviciu.html",
  "./spete/28-concedierea-disciplinara-fara-cercetare-prealabila.html",
  "./spete/29-locotenentul-plecat-la-32-de-ani-si-pensia-din-doua-sisteme.html",
  "./spete/30-chiria-in-concediul-de-crestere-a-copilului-si-revenirea-la.html",
  /* SPETE-END */
];

self.addEventListener("install", function (e) {
  e.waitUntil(
    caches.open(VERSIUNE)
      .then(function (c) { return c.addAll(FISIERE); })
      .then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener("activate", function (e) {
  e.waitUntil(
    caches.keys()
      .then(function (chei) {
        return Promise.all(chei.filter(function (k) { return k !== VERSIUNE; })
                               .map(function (k) { return caches.delete(k); }));
      })
      .then(function () { return self.clients.claim(); })
      // Anunță paginile deschise (actualizare.js): mesajul așteaptă până li se încarcă scripturile,
      // deci nu se pierde ca „controllerchange”, care poate veni înainte ca pagina să-l asculte.
      .then(function () { return self.clients.matchAll({ type: "window", includeUncontrolled: true }); })
      .then(function (pagini) {
        pagini.forEach(function (p) { p.postMessage({ tip: "versiune-noua", versiune: VERSIUNE }); });
      })
  );
});

self.addEventListener("fetch", function (e) {
  if (e.request.method !== "GET") return;
  e.respondWith(
    caches.match(e.request).then(function (raspuns) {
      if (raspuns) return raspuns;
      return fetch(e.request).then(function (net) {
        // memorează și resursele cerute ulterior, ca să reziste offline
        var copie = net.clone();
        caches.open(VERSIUNE).then(function (c) { c.put(e.request, copie); });
        return net;
      }).catch(function () {
        // offline: paginile cad pe index.html; restul (ex. fonturile încă necache-uite) eșuează curat
        return e.request.mode === "navigate" ? caches.match("./index.html") : Response.error();
      });
    })
  );
});
