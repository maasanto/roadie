import { useCall } from "frappe-ui";
import { onMounted, onUnmounted, ref } from "vue";

// One request shared by every screen, so the sidebar's Inbox badge drops as soon as one of them marks mail read.
export const unreadEmailCount = useCall({ url: "/api/v2/method/roadie.api.get_unread_email_count" });

// Module scope: a delete still waiting on its toast must outlive the thread it was made from, which remounts when
// the reader moves on. Threads hide these emails and the mailbox the rows they empty. An email stays hidden once
// deleted, its name never comes back.
export const deletedEmails = ref(new Set());

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
