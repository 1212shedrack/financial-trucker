/* PFAMS Service Worker — Cache-first static, Network-first API */
const CACHE_VERSION = 'pfams-v2';
const STATIC_CACHE  = 'pfams-static-v2';
const API_CACHE     = 'pfams-api-v2';

const STATIC_ASSETS = [
  '/',
  '/dashboard/',
  '/static/css/style.css',
  '/static/js/main.js',
  '/static/js/offline.js',
  '/static/js/service-worker.js',
  '/static/manifest.json',
  '/static/icons/icon-192.png',
  '/static/vendor/bootstrap/css/bootstrap.min.css',
  '/static/vendor/bootstrap-icons/font/bootstrap-icons.min.css',
  '/static/vendor/bootstrap/js/bootstrap.bundle.min.js',
  '/static/vendor/chart.js/chart.umd.min.js',
  '/static/vendor/bootstrap-icons/font/fonts/bootstrap-icons.woff',
  '/static/vendor/bootstrap-icons/font/fonts/bootstrap-icons.woff2',
];

/* Install */
self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(STATIC_CACHE).then(cache => cache.addAll(STATIC_ASSETS).catch(() => {}))
  );
});

/* ── Activate */
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(k => k !== STATIC_CACHE && k !== API_CACHE).map(k => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

/* ── Fetch */
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET and cross-origin
  if (request.method !== 'GET') return;
  if (url.origin !== self.location.origin) return;

  // API requests — network first
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirst(request, API_CACHE));
    return;
  }

  // Static assets — cache first
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(cacheFirst(request, STATIC_CACHE));
    return;
  }

  // HTML pages — network first with offline fallback
  event.respondWith(networkFirst(request, STATIC_CACHE));
});

async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    if (response.ok) cache.put(request, response.clone());
    return response;
  } catch (err) {
    return new Response('Offline — content not available.', { status: 503 });
  }
}

async function networkFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  try {
    const response = await fetch(request);
    if (response.ok) cache.put(request, response.clone());
    return response;
  } catch (err) {
    const cached = await cache.match(request);
    if (cached) return cached;
    return new Response(
      JSON.stringify({ error: 'You are offline.', offline: true }),
      { status: 503, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

/* ── Background Sync */
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-transactions') {
    event.waitUntil(
      self.clients.matchAll().then(clients =>
        clients.forEach(client => client.postMessage({ type: 'SYNC_NOW' }))
      )
    );
  }
});
