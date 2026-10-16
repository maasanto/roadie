import { toast } from "frappe-ui";

// Sonner's 4-second default is too short to read the toast and reach Undo.
export const UNDO_WINDOW_MS = 8000;

const commitsByToast = new Map();

// Leaving the page never closes the toast, so its change would silently not happen. The browser drops a request a
// leaving page starts unless it is keepalive, and frappe-ui's `call` has no option for it.
// Warning: keepalive only reaches a request a commit starts synchronously, as `call` does before its first await.
// A draft's leave warning can still keep the page open, so the toast goes too: its Undo could no longer take the
// change back.
function commitPending() {
	if (!commitsByToast.size) return;
	const fetchWithoutKeepalive = window.fetch;
	window.fetch = (resource, options) => fetchWithoutKeepalive(resource, { ...options, keepalive: true });
	try {
		commitsByToast.forEach((commit, toastId) => {
			commit();
			toast.dismiss(toastId);
		});
	} finally {
		window.fetch = fetchWithoutKeepalive;
	}
}
// beforeunload goes out before a reload asks for the page again, so the change usually lands before the reloaded
// screen loads. iOS never fires it, hence pagehide too.
window.addEventListener("beforeunload", commitPending);
window.addEventListener("pagehide", commitPending);

// The change happens when the toast closes unless Undo came first, so Undo needs no server round trip. Either
// settles it once: a toast can report both closing and being dismissed.
export function toastWithUndo(message, { undo, commit }) {
	const settle = (outcome) => () => {
		if (commitsByToast.delete(toastId)) outcome();
	};
	const toastId = toast(message, {
		action: { label: __("Undo"), onClick: settle(undo) },
		duration: UNDO_WINDOW_MS,
		onAutoClose: settle(commit),
		onDismiss: settle(commit),
	});
	commitsByToast.set(toastId, settle(commit));
}
