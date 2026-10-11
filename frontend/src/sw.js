import { cleanupOutdatedCaches, precacheAndRoute } from "workbox-precaching";

precacheAndRoute(self.__WB_MANIFEST);
cleanupOutdatedCaches();

self.skipWaiting();
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));
