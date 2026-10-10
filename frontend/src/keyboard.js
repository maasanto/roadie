import { onMounted, onUnmounted } from "vue";

const FIELDS = "input, textarea, select, [contenteditable]";
const isDialogOpen = () => Boolean(document.querySelector('[role="dialog"][data-state="open"]'));

// Page-wide shortcut while the component is mounted. Keys typed into a field are ignored, except Escape,
// and a frappe-ui Dialog on top keeps Escape for itself. Escape inside a `data-draft` form would lose the draft.
export function onKey(key, handler) {
	const ignoredIn = key === "Escape" ? "[data-draft]" : FIELDS;
	const listener = (event) => {
		if (event.key !== key || event.defaultPrevented || isDialogOpen()) return;
		if (event.target.closest?.(ignoredIn)) return;
		event.preventDefault();
		handler(event);
	};
	onMounted(() => window.addEventListener("keydown", listener));
	onUnmounted(() => window.removeEventListener("keydown", listener));
}
