/* Service worker — face aplicația disponibilă offline după prima deschidere.
   La fiecare modificare a întrebărilor, schimbă VERSIUNE ca să se reîmprospăteze cache-ul. */
const VERSIUNE = "grile-ru-v20";
const FISIERE = [
  "./",
  "./index.html",
  "./style.css",
  "./app.js",
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
        return caches.match("./index.html");
      });
    })
  );
});
