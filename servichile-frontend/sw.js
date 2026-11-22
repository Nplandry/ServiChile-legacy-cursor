const CACHE_NAME = 'servichile-v219';

self.addEventListener('install', function () {
  self.skipWaiting();
});

self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys().then(function (names) {
      return Promise.all(
        names.filter(function (name) {
          return name !== CACHE_NAME;
        }).map(function (name) {
          return caches.delete(name);
        })
      );
    }).then(function () {
      return self.clients.claim();
    })
  );
});

function guardar(request, response) {
  if (!response || !response.ok) return response;
  const copia = response.clone();
  caches.open(CACHE_NAME).then(function (cache) {
    cache.put(request, copia);
  }).catch(function () {});
  return response;
}

self.addEventListener('fetch', function (event) {
  const request = event.request;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin || request.headers.has('Authorization')) return;

  const path = url.pathname;
  const estatico =
    path.endsWith('.js') ||
    path.endsWith('.css') ||
    path.endsWith('.html') ||
    path.endsWith('/') ||
    path.endsWith('/onboarding');

  if (!estatico) return;

  event.respondWith(
    fetch(request)
      .then(function (response) {
        return guardar(request, response);
      })
      .catch(function () {
        return caches.match(request);
      })
  );
});
