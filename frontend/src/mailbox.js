import { useCall } from "frappe-ui";
import { onMounted, onUnmounted } from "vue";

// One request shared by every screen, so the sidebar's Inbox badge drops as soon as one of them marks mail read.
export const unreadEmailCount = useCall({ url: "/api/v2/method/roadie.api.get_unread_email_count" });

// Nothing tells the app that mail arrived, so it asks again whenever the member may be looking at it.
const MAIL_REFRESH_INTERVAL_MS = 60 * 1000;

export function refreshWhileVisible(reload) {
	function refresh() {
		// Offline, the failed request would swap what is shown for an error.
		if (document.visibilityState === "visible" && navigator.onLine) reload();
	}

	let refreshTimer = null;
	onMounted(() => {
		document.addEventListener("visibilitychange", refresh);
		window.addEventListener("online", refresh);
		refreshTimer = setInterval(refresh, MAIL_REFRESH_INTERVAL_MS);
	});
	onUnmounted(() => {
		document.removeEventListener("visibilitychange", refresh);
		window.removeEventListener("online", refresh);
		clearInterval(refreshTimer);
	});
}
