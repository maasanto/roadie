import assert from "node:assert/strict";
import { test } from "node:test";

globalThis.window = globalThis;
await import("./translation.js");
const { confirmDiscardDraft, keepOpenForDraft, trackDraft } = await import("./draft.js");
const { ref } = await import("vue");

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

test("a dialog holding a kept draft stays open, and opens freely", (t) => {
	questions = 0;
	const isOpen = keepOpenForDraft(ref(true));
	const reply = composer({ isEdited: true });
	t.after(reply.forget);
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
