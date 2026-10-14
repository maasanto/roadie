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

// Matches EMAIL_DRAFT_FIELD in roadie/api.py, which only lets a draft delete the uploads stamped with it.
export const DRAFT_UPLOAD_ARGS = { fieldname: "roadie_email_draft", private: true };

// A draft also carries existing File records, such as a forwarded email's, which sending copies: they aren't the
// draft's to delete, and the server would refuse.
export const isDraftUpload = (file) => file.attached_to_field === DRAFT_UPLOAD_ARGS.fieldname;

// For a dialog's v-model:open: closing it unmounts the email thread inside, so it stays open when the draft is kept.
export const keepOpenForDraft = (isOpen) =>
	computed({
		get: () => isOpen.value,
		set: (value) => {
			if (value || confirmDiscardDraft()) isOpen.value = value;
		},
	});
