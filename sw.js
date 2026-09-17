/* Service worker — face aplicația disponibilă offline după prima deschidere.
   La fiecare modificare a întrebărilor, schimbă VERSIUNE ca să se reîmprospăteze cache-ul. */
const VERSIUNE = "grile-ru-v1";
const FISIERE = [
  "./",
  "./index.html",
  "./style.css",
  "./app.js",
  "./intrebari.js",
  "./manifest.json",
  "./icon-192.png",
  "./icon-512.png",
  "./apple-touch-icon.png"
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
