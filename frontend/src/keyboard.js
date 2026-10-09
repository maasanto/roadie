import { onMounted, onUnmounted } from "vue";

const isTypingIn = (target) => Boolean(target.closest?.("input, textarea, select, [contenteditable]"));
const isDialogOpen = () => Boolean(document.querySelector('[role="dialog"][data-state="open"]'));

// Page-wide shortcut while the component is mounted. Keys typed into a field are ignored, except Escape,
// and a frappe-ui Dialog on top keeps Escape for itself.
export function onKey(key, handler) {
	const listener = (event) => {
		if (event.key !== key || event.defaultPrevented || isDialogOpen()) return;
		if (key !== "Escape" && isTypingIn(event.target)) return;
		event.preventDefault();
		handler(event);
	};
	onMounted(() => window.addEventListener("keydown", listener));
	onUnmounted(() => window.removeEventListener("keydown", listener));
}
