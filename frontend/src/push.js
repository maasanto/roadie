// Frappe's push relay hands out one Firebase project per app; roadie/push_notifications.py sends to the same one.
const PROJECT = "roadie";
// The key Frappe's own push clients use, so a device keeps its token across reloads.
const TOKEN_KEY = `firebase_token_${PROJECT}`;

// www/roadie.py only boots the relay URL when the site has push set up.
export const isPushAvailable = () =>
	Boolean(window.push_relay_server_url) &&
	"serviceWorker" in navigator &&
	"PushManager" in window &&
	"Notification" in window;

export const isPushEnabled = () =>
	Notification.permission === "granted" && localStorage.getItem(TOKEN_KEY) !== null;

/** Turns push on for this device. Call it from a click: Safari only prompts inside one. */
export async function enablePush() {
	if ((await Notification.requestPermission()) !== "granted") return false;
	const token = await getFirebaseToken();
	await callFrappePushEndpoint("subscribe", token);
	localStorage.setItem(TOKEN_KEY, token);
	return true;
}

export async function disablePush() {
	const token = localStorage.getItem(TOKEN_KEY);
	localStorage.removeItem(TOKEN_KEY);
	// Dropping the browser's subscription stops delivery even if the relay call below fails.
	const registration = await navigator.serviceWorker.ready;
	await (await registration.pushManager.getSubscription())?.unsubscribe();
	if (token) await callFrappePushEndpoint("unsubscribe", token);
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
