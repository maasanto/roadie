import { computed } from "vue";

// One check per composer on screen, each telling whether it holds anything its writer would lose.
const editedChecks = new Set();

export function trackDraft(isEdited) {
	editedChecks.add(isEdited);
	return () => editedChecks.delete(isEdited);
}

export const hasEditedDraft = () => [...editedChecks].some((isEdited) => isEdited());

// Asks about every composer on screen, unless the action only destroys the one `isEdited` checks.
export function confirmDiscardDraft(isEdited = hasEditedDraft) {
	return !isEdited() || window.confirm(__("Discard the unsent email?"));
}

// For a dialog's v-model:open: closing it unmounts the email thread inside, so it stays open when the draft is kept.
export const keepOpenForDraft = (isOpen) =>
	computed({
		get: () => isOpen.value,
		set: (value) => {
			if (value || confirmDiscardDraft()) isOpen.value = value;
		},
	});
