const CACHE_NAME = 'oracle-ai-v3';
const STATIC_ASSETS = [
    '/',
    '/static/style.css',
    '/static/manifest.json'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
    );
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        )
    );
    self.clients.claim();
});

self.addEventListener('fetch', event => {
    // Network first for API calls, cache first for static assets
    if (event.request.url.includes('/analyze') ||
        event.request.url.includes('/history') ||
        event.request.url.includes('/api-key') ||
        event.request.url.includes('/ask-followup') ||
        event.request.url.includes('/dashboard')) {
        event.respondWith(
            fetch(event.request).catch(() => caches.match(event.request))
        );
    } else {
        event.respondWith(
            caches.match(event.request).then(cached => cached || fetch(event.request))
        );
    }
});
