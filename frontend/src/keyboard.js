import { onMounted, onUnmounted } from "vue";

const isTypingIn = (target) => Boolean(target.closest?.("input, textarea, select, [contenteditable]"));
const isWritingDraftIn = (target) => Boolean(target.closest?.("[data-draft]"));
const isDialogOpen = () => Boolean(document.querySelector('[role="dialog"][data-state="open"]'));

// Page-wide shortcut while the component is mounted. Keys typed into a field are ignored, except Escape,
// and a frappe-ui Dialog on top keeps Escape for itself. Escape inside a `data-draft` form would lose the draft.
export function onKey(key, handler) {
	const listener = (event) => {
		if (event.key !== key || event.defaultPrevented || isDialogOpen()) return;
		if (key === "Escape" ? isWritingDraftIn(event.target) : isTypingIn(event.target)) return;
		event.preventDefault();
		handler(event);
	};
	onMounted(() => window.addEventListener("keydown", listener));
	onUnmounted(() => window.removeEventListener("keydown", listener));
}
