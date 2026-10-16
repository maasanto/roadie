import assert from "node:assert/strict";
import { test } from "node:test";

globalThis.window = globalThis;
await import("./translation.js");
const {
	DIALOG_EDITED_CHECKS,
	DRAFT_UPLOAD_ARGS,
	confirmDiscardDraft,
	isDraftUpload,
	keepOpenForDraft,
	pickedFile,
	trackDraft,
} = await import("./draft.js");
const { forwardDraft } = await import("./email.js");
const { createSSRApp, h, inject, ref } = await import("vue");
const { renderToString } = await import("vue/server-renderer");

let answer;
let questions;
window.confirm = () => {
	questions++;
	return answer;
};

function composer({ isEdited }) {
	const forget = trackDraft(() => isEdited);
	return { forget, isEdited: () => isEdited };
}

test("only an edited composer asks, and a refusal keeps it", (t) => {
	questions = 0;
	const reply = composer({ isEdited: false });
	t.after(reply.forget);
	assert.equal(confirmDiscardDraft(), true, "an untouched composer goes without asking");
	assert.equal(questions, 0);

	const newEmail = composer({ isEdited: true });
	t.after(newEmail.forget);
	answer = false;
	assert.equal(confirmDiscardDraft(), false);
	answer = true;
	assert.equal(confirmDiscardDraft(), true);
	assert.equal(questions, 2);
});

test("discarding one composer does not ask about another one's draft", (t) => {
	questions = 0;
	const gigReply = composer({ isEdited: true });
	t.after(gigReply.forget);
	const taskReply = composer({ isEdited: false });
	t.after(taskReply.forget);
	assert.equal(confirmDiscardDraft(taskReply.isEdited), true);
	assert.equal(questions, 0);
});

test("a sent or unmounted composer no longer asks", () => {
	questions = 0;
	composer({ isEdited: true }).forget();
	assert.equal(confirmDiscardDraft(), true);
	assert.equal(questions, 0);
});

test("discarding a forward or removing its chips deletes only the files the writer uploaded", () => {
	const rider = { name: "file-1", file_name: "rider.pdf", file_url: "/private/files/rider.pdf" };
	const { attachments: forwarded } = forwardDraft({
		name: "comm-1",
		sender: "alice@example.com",
		subject: "Rider",
		content: "<p>See you there</p>",
		communication_date: "2027-07-14 10:00:00",
		attachments: [rider],
	});
	// What upload_file answers the composer's FileUploader with.
	const setlist = {
		name: "file-2",
		file_name: "setlist.pdf",
		attached_to_field: DRAFT_UPLOAD_ARGS.fieldname,
	};
	assert.deepEqual([...forwarded, setlist].filter(isDraftUpload), [setlist]);
});

test("a file picked from the gig is never deleted, even an earlier draft's upload left on it", () => {
	const staleUpload = {
		name: "file-3",
		file_name: "stage-plan.pdf",
		file_url: "/private/files/stage-plan.pdf",
		attached_to_field: DRAFT_UPLOAD_ARGS.fieldname,
	};
	const picked = pickedFile(staleUpload);
	assert.deepEqual(picked, { name: "file-3", file_name: "stage-plan.pdf" });
	assert.equal(isDraftUpload(picked), false);
});

// Mounts a dialog around composers that register the way EmailComposer does, so provide and inject are exercised.
async function dialogWithComposers(t, composerEdits) {
	let isOpen;
	const DialogComposer = {
		props: ["isEdited"],
		setup(props) {
			t.after(trackDraft(() => props.isEdited, inject(DIALOG_EDITED_CHECKS, null)));
			return () => null;
		},
	};
	const Dialog = {
		setup() {
			isOpen = keepOpenForDraft(ref(true));
			return () => composerEdits.map((isEdited) => h(DialogComposer, { isEdited }));
		},
	};
	await renderToString(createSSRApp(Dialog));
	return isOpen;
}

test("a dialog holding a kept draft stays open, and opens freely", async (t) => {
	questions = 0;
	const isOpen = await dialogWithComposers(t, [true]);
	answer = false;
	isOpen.value = false;
	assert.equal(isOpen.value, true);
	answer = true;
	isOpen.value = false;
	assert.equal(isOpen.value, false);
	isOpen.value = true;
	assert.equal(isOpen.value, true);
	assert.equal(questions, 2);
});

test("a task dialog closes without asking about the gig's unsent reply behind it", async (t) => {
	questions = 0;
	const gigReply = composer({ isEdited: true });
	t.after(gigReply.forget);
	const isOpen = await dialogWithComposers(t, [false]);
	answer = false;
	isOpen.value = false;
	assert.equal(isOpen.value, false);
	assert.equal(questions, 0);
	assert.equal(confirmDiscardDraft(), false, "leaving the gig still asks about its reply");
});
