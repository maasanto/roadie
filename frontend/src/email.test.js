import assert from "node:assert/strict";
import { test } from "node:test";

globalThis.window = globalThis;
await import("./translation.js");
const { replyDraft } = await import("./email.js");

const received = {
	name: "comm-1",
	sent_or_received: "Received",
	sender: "alice@example.com",
	recipients: "Roadie <band@example.com>, Bob <bob@example.com>",
	cc: "carol@example.com, band@example.com",
	account_email: "band@example.com",
	subject: "Rider",
	content: "<p>See you there</p>",
	communication_date: "2027-07-14 10:00:00",
};

test("reply all keeps every other To and Cc recipient, but never the shared account", () => {
	const draft = replyDraft(received, "reply-all");
	assert.deepEqual(draft.to, ["alice@example.com", "bob@example.com"]);
	assert.deepEqual(draft.cc, ["carol@example.com"]);
});

test("reply only answers the sender", () => {
	const draft = replyDraft(received, "reply");
	assert.deepEqual(draft.to, ["alice@example.com"]);
	assert.deepEqual(draft.cc, []);
});

test("reply all to a sent email goes back to its recipients", () => {
	const sent = { ...received, sent_or_received: "Sent", sender: "john@example.com" };
	const draft = replyDraft(sent, "reply-all");
	assert.deepEqual(draft.to, ["bob@example.com"]);
	assert.deepEqual(draft.cc, ["carol@example.com"]);
});
