import { cleanupOutdatedCaches, precacheAndRoute } from "workbox-precaching";

precacheAndRoute(self.__WB_MANIFEST);
cleanupOutdatedCaches();

self.skipWaiting();
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));

const APP_ROUTE = "/roadie";

function readPushPayload(event) {
	try {
		return event.data?.json() ?? {};
	} catch {
		return {};
	}
}

// No Firebase SDK in the worker: FCM delivers a standard push event, so the worker shows the notification itself.
// Every push must show one, unreadable or not: Safari revokes the subscription of a worker that stays silent.
self.addEventListener("push", (event) => {
	const { data = {}, notification = {} } = readPushPayload(event);
	event.waitUntil(
		self.registration.showNotification(data.title || notification.title || "Roadie", {
			body: data.body || notification.body || "",
			icon: data.notification_icon || "/assets/roadie/pwa/icon-192.png",
			data: { url: data.click_action || APP_ROUTE },
		})
	);
});

self.addEventListener("notificationclick", (event) => {
	event.notification.close();
	const url = event.notification.data?.url || APP_ROUTE;
	event.waitUntil(
		self.clients.matchAll({ type: "window" }).then((windows) => {
			const open = windows.find((client) => new URL(client.url).pathname.startsWith(APP_ROUTE));
			return open ? open.focus().then((client) => client.navigate(url)) : self.clients.openWindow(url);
		})
	);
});
