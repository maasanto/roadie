import { toast } from "frappe-ui";

// Sonner's 4-second default is too short to read the toast and reach Undo.
export const UNDO_WINDOW_MS = 8000;

// The change happens when the toast closes unless Undo came first, so Undo needs no server round trip. Either
// settles it once: a toast can report both closing and being dismissed.
export function toastWithUndo(message, { undo, commit }) {
	let isSettled = false;
	const settle = (outcome) => () => {
		if (isSettled) return;
		isSettled = true;
		outcome();
	};
	toast(message, {
		action: { label: __("Undo"), onClick: settle(undo) },
		duration: UNDO_WINDOW_MS,
		onAutoClose: settle(commit),
		onDismiss: settle(commit),
	});
}
