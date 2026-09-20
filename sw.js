/* Service worker — face aplicația disponibilă offline după prima deschidere.
   La fiecare modificare a întrebărilor, schimbă VERSIUNE ca să se reîmprospăteze cache-ul. */
const VERSIUNE = "grile-ru-v15";
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
  /* TEMATICA-END */
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
