import { computed, provide } from "vue";

// One check per composer on screen, each telling whether it holds anything its writer would lose.
const editedChecks = new Set();

// The checks of the composers inside a dialog, which closing it destroys, unlike the ones behind it.
export const DIALOG_EDITED_CHECKS = Symbol("dialog edited checks");

const anyEdited = (checks) => [...checks].some((isEdited) => isEdited());

export function trackDraft(isEdited, dialogEditedChecks) {
	editedChecks.add(isEdited);
	dialogEditedChecks?.add(isEdited);
	return () => {
		editedChecks.delete(isEdited);
		dialogEditedChecks?.delete(isEdited);
	};
}

export const hasEditedDraft = () => anyEdited(editedChecks);

// Asks about every composer on screen, unless the action only destroys the ones `isEdited` checks.
export function confirmDiscardDraft(isEdited = hasEditedDraft) {
	return !isEdited() || window.confirm(__("Discard the unsent email?"));
}

// Matches EMAIL_DRAFT_FIELD in roadie/api.py, which only lets a draft delete the uploads stamped with it.
export const DRAFT_UPLOAD_ARGS = { fieldname: "roadie_email_draft", private: true };

// A draft also carries existing File records, such as a forwarded email's, which sending copies: they aren't the
// draft's to delete, and the server would refuse.
export const isDraftUpload = (file) => file.attached_to_field === DRAFT_UPLOAD_ARGS.fieldname;

// A file picked from the record is the record's, even an earlier draft's upload left there: it is never the draft's.
export const pickedFile = ({ name, file_name }) => ({ name, file_name });

// For a dialog's v-model:open, called from its setup: closing it unmounts the email thread inside, so it stays open
// when that draft is kept. A composer behind the dialog survives the close, so it doesn't ask.
export function keepOpenForDraft(isOpen) {
	const dialogEditedChecks = new Set();
	provide(DIALOG_EDITED_CHECKS, dialogEditedChecks);
	return computed({
		get: () => isOpen.value,
		set: (value) => {
			if (value || confirmDiscardDraft(() => anyEdited(dialogEditedChecks))) isOpen.value = value;
		},
	});
}
