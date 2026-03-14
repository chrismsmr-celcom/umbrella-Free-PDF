const CACHE_NAME = 'umbrella-cache-v1';
const ASSETS = [
  '/',
  '/index.html',
  // Ajoute ici uniquement les fichiers dont tu es SUR de l'existence
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      // On utilise une boucle pour ne pas tout bloquer si un fichier manque
      return Promise.allSettled(
        ASSETS.map(url => cache.add(url))
      );
    })
  );
});