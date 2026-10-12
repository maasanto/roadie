import { resultRoute } from "./search.js";

export const unreadCount = (notifications = []) =>
	notifications.filter((notification) => !notification.read).length;

// A notification about a record opens that record, as the search palette would, so Frappe's own mentions,
// which carry no Roadie link, open it too. The server's route covers the rest.
export const notificationRoute = ({ document_type, document_name, route }) =>
	(document_name && resultRoute({ doctype: document_type, name: document_name })) || route;

const MINUTE = 60 * 1000;
const HOUR = 60 * MINUTE;

export function relativeDate(value, now = new Date()) {
	// Server timestamps read "2027-07-14 10:00:00", which Safari refuses to parse without the T.
	const at = new Date(String(value).replace(" ", "T"));
	const elapsed = now - at;
	if (elapsed < MINUTE) return __("Just now");
	if (elapsed < HOUR) return __("{0} min ago", [Math.floor(elapsed / MINUTE)]);
	if (elapsed < 24 * HOUR) return __("{0} h ago", [Math.floor(elapsed / HOUR)]);
	return at.toLocaleDateString(window.lang);
}
