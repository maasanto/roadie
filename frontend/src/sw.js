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
			data: { url: toAppPath(data.click_action) },
		})
	);
});

// The server builds absolute links from its configured host, which can differ from the origin the member browses.
function toAppPath(link) {
	const url = new URL(link || APP_ROUTE, self.location.origin);
	return url.pathname + url.search;
}

self.addEventListener("notificationclick", (event) => {
	event.notification.close();
	const url = event.notification.data?.url || APP_ROUTE;
	// A Suite document opens beside Roadie, as from the panel, so the member's open screen is kept.
	if (!url.startsWith(APP_ROUTE)) {
		event.waitUntil(self.clients.openWindow(url));
		return;
	}
	event.waitUntil(
		self.clients.matchAll({ type: "window" }).then(([open]) =>
			open
				? open
						.focus()
						// Some browsers refuse focus; the window should still move to what was clicked.
						.catch(() => open)
						.then((client) => client.navigate(url))
				: self.clients.openWindow(url)
		)
	);
});
