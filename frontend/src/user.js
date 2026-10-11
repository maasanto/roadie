import { reactive } from "vue";

// www/roadie.py boots the member's name and picture; the settings screen keeps them in step.
export const user = reactive({
	name: window.user,
	fullName: window.user_full_name || window.user,
	image: window.user_image || "",
});

// Up to two letters, for the avatar to fall back on when no picture is set.
export function initials(name = "") {
	const words = String(name).trim().split(/\s+/).filter(Boolean);
	if (!words.length) return "?";
	if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
	return (words[0][0] + words[words.length - 1][0]).toUpperCase();
}
