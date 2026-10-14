import { onMounted, onUnmounted } from "vue";

const FIELDS = "input, textarea, select, [contenteditable]";
const isOverlayOpen = () =>
	Boolean(document.querySelector(':is([role="dialog"], [role="menu"])[data-state="open"]'));

function listen(key, ignoredIn, matchesModifiers, handler) {
	const listener = (event) => {
		if (event.key !== key || event.defaultPrevented || isOverlayOpen()) return;
		if (!matchesModifiers(event)) return;
		if (event.target.closest?.(ignoredIn)) return;
		event.preventDefault();
		handler(event);
	};
	onMounted(() => window.addEventListener("keydown", listener));
	onUnmounted(() => window.removeEventListener("keydown", listener));
}

// Page-wide shortcut while the component is mounted. Keys typed into a field are ignored, except Escape,
// and a frappe-ui Dialog or menu on top keeps Escape for itself. Escape inside a `data-draft` form would lose the draft.
export function onKey(key, handler) {
	listen(key, key === "Escape" ? "[data-draft]" : FIELDS, () => true, handler);
}

// Same, for a shortcut that asks for a modifier, such as Ctrl/⌘+K. Ctrl and ⌘ count as the same modifier,
// and the unrequested ones must stay up, so Ctrl+Shift+K does not fire a shortcut bound to Ctrl+K.
export function onShortcut({ key, ctrl = false, shift = false, alt = false }, handler) {
	listen(
		key,
		FIELDS,
		(event) =>
			(event.ctrlKey || event.metaKey) === ctrl && event.shiftKey === shift && event.altKey === alt,
		handler
	);
}
