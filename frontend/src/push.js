// Frappe's push relay hands out one Firebase project per app; roadie/push_notifications.py sends to the same one.
const PROJECT = "roadie";
// Per member: the browser's subscription outlives a session, and a shared device must not read on for the next one.
const tokenKey = () => `firebase_token_${PROJECT}:${window.user}`;

// www/roadie.py only boots the relay URL when the site has push set up, and only a production build registers the worker.
export const isPushAvailable = () =>
	import.meta.env.PROD &&
	Boolean(window.push_relay_server_url) &&
	"serviceWorker" in navigator &&
	"PushManager" in window &&
	"Notification" in window;

export const isPushEnabled = () => localStorage.getItem(tokenKey()) !== null;

/** Turns push on for this device. Call it from a click: Safari only prompts inside one. */
export async function enablePush() {
	if ((await Notification.requestPermission()) !== "granted") return;
	await registerDevice();
}

export async function disablePush() {
	const token = localStorage.getItem(tokenKey());
	// Dropping the browser's subscription stops delivery even if the relay call below fails.
	// Not serviceWorker.ready: it never settles without a worker, and logging out awaits this.
	const registration = await navigator.serviceWorker.getRegistration("/roadie");
	await (await registration?.pushManager.getSubscription())?.unsubscribe();
	if (token) await callFrappePushEndpoint("unsubscribe", token);
	localStorage.removeItem(tokenKey());
}

/** Firebase rotates tokens, so a subscribed device re-registers its current one on every launch. */
export function refreshPushToken() {
	if (isPushAvailable() && isPushEnabled() && Notification.permission === "granted") {
		registerDevice().catch((error) => console.error("Could not refresh the push token", error));
	}
}

async function registerDevice() {
	const token = await getFirebaseToken();
	const previous = localStorage.getItem(tokenKey());
	if (token === previous) return;
	if (previous) {
		await callFrappePushEndpoint("unsubscribe", previous).catch((error) =>
			console.error("Could not drop the previous push token", error)
		);
	}
	await callFrappePushEndpoint("subscribe", token);
	localStorage.setItem(tokenKey(), token);
}

// Firebase only mints the token: the worker shows pushes itself, so the SDK stays out of the main bundle.
async function getFirebaseToken() {
	const response = await fetch(
		`${window.push_relay_server_url}/api/method/notification_relay.api.get_config?project_name=${PROJECT}`
	);
	if (!response.ok) throw new Error(__("The push relay answered with an error ({0})", [response.status]));
	const { config, vapid_public_key: vapidKey } = await response.json();

	const [{ getApps, initializeApp }, { getMessaging, getToken, isSupported }] = await Promise.all([
		import("firebase/app"),
		import("firebase/messaging"),
	]);
	if (!(await isSupported())) throw new Error(__("This browser can't receive push notifications"));
	const messaging = getMessaging(getApps()[0] ?? initializeApp(config));
	return getToken(messaging, { vapidKey, serviceWorkerRegistration: await navigator.serviceWorker.ready });
}

// frappe.push_notification registers the token with the relay for the session user, and only answers GET.
async function callFrappePushEndpoint(method, token) {
	const params = new URLSearchParams({ fcm_token: token, project_name: PROJECT });
	const response = await fetch(`/api/method/frappe.push_notification.${method}?${params}`);
	const result = (await response.json().catch(() => ({}))).message;
	if (!response.ok || !result?.success) {
		throw new Error(result?.message || __("The push relay refused this device ({0})", [response.status]));
	}
}
