const CACHE_NAME = 'billable-planner-v1';
const CORE_ASSETS = [
  './',
  './index.html',
  './manifest.webmanifest',
  './service-worker.js',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/apple-touch-icon.png'
];

// Install: cache core assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(CORE_ASSETS)).then(() => self.skipWaiting())
  );
});

// Activate: cleanup old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.map((k) => (k === CACHE_NAME ? null : caches.delete(k))))
    ).then(() => self.clients.claim())
  );
});

// Fetch: stale-while-revalidate for everything (including CDN assets).
self.addEventListener('fetch', (event) => {
  const req = event.request;

  // Only handle GET
  if (req.method !== 'GET') return;

  event.respondWith(
    caches.match(req).then((cached) => {
      const fetchPromise = fetch(req)
        .then((resp) => {
          // Cache successful responses, including opaque (cross-origin) responses
          if (resp && (resp.status === 200 || resp.type === 'opaque')) {
            const respClone = resp.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(req, respClone)).catch(() => {});
          }
          return resp;
        })
        .catch(() => cached || caches.match('./index.html'));

      // Return cached immediately if available, else network
      return cached || fetchPromise;
    })
  );
});
