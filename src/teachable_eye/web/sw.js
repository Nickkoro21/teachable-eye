// App-shell cache so the PWA installs and opens fast. The API and the camera
// socket always go to the network: results must be live, never cached.
const CACHE = "teye-shell-v18";
const SHELL = ["/", "/static/style.css", "/static/app.js", "/static/icon.svg", "/manifest.webmanifest"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) =>
    Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))));
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  const shell = SHELL.includes(url.pathname) || url.pathname.startsWith("/static/");
  if (e.request.method !== "GET" || !shell) return;
  // network first, so a server update is picked up; cache when the PC is not
  // reachable (e.g. Tailscale off on the phone). Assets carry a ?v= version:
  // offline, any cached version will do, so the page still works and can say
  // that the PC is not reachable (it once showed up unstyled and dead).
  e.respondWith(fetch(e.request, { cache: "no-cache" }).then((res) => {
    const copy = res.clone();
    caches.open(CACHE).then((c) => c.put(e.request, copy));
    return res;
  }).catch(() => caches.match(e.request, { ignoreSearch: true })));
});
