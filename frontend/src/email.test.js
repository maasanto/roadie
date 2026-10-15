import assert from "node:assert/strict";
import { test } from "node:test";

globalThis.window = globalThis;
await import("./translation.js");
const { forwardDraft, isFailedDelivery, openByDefault, replyDraft, splitRecipients, withSignature } =
	await import("./email.js");

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

test("a forward starts with no recipient and carries the original's attachments and headers", () => {
	const rider = { name: "file-1", file_name: "rider.pdf" };
	const draft = forwardDraft({ ...received, sender_full_name: "Alice", attachments: [rider] });
	assert.equal(draft.to, undefined);
	assert.equal(draft.inReplyTo, undefined);
	assert.equal(draft.subject, "Fwd: Rider");
	assert.deepEqual(draft.attachments, [rider]);
	assert.match(draft.content, /From: Alice &lt;alice@example\.com&gt;/);
	assert.match(draft.content, /To: Roadie &lt;band@example\.com&gt;, Bob &lt;bob@example\.com&gt;/);
	assert.match(draft.content, /<blockquote><p>See you there<\/p><\/blockquote>$/);
	assert.equal(forwardDraft({ ...received, subject: "TR : Rider" }).subject, "TR : Rider");
});

test("a forward of a Bcc copy from a bare address shows no empty To and no doubled address", () => {
	const bcc = { ...received, sender_full_name: "alice@example.com", recipients: null, cc: null };
	const { content } = forwardDraft(bcc);
	assert.match(content, /From: alice@example\.com<br>/);
	assert.doesNotMatch(content, /To: /);
});

test("the signature opens below the cursor, and above the quote so it still folds", () => {
	const signature = "<p>John, drums</p>";
	assert.equal(withSignature("", signature), "<p></p><p>John, drums</p>");
	assert.match(
		withSignature(replyDraft(received, "reply").content, signature),
		/^<p><\/p><p>John, drums<\/p><p><\/p><p>On .+ wrote:<\/p><blockquote><p>See you there<\/p><\/blockquote>$/
	);
	assert.equal(withSignature("", "John\nAcme Band"), "<p></p><p>John<br>Acme Band</p>");
	assert.equal(withSignature("", null), "");
});

test("a mistyped recipient is kept apart from the addresses, never dropped", () => {
	assert.deepEqual(splitRecipients("jane@example.com, john@exmple;bob@example.org"), {
		valid: ["jane@example.com", "bob@example.org"],
		invalid: ["john@exmple"],
	});
	assert.deepEqual(splitRecipients(" , "), { valid: [], invalid: [] });
});

test("only an email that failed to go out counts as a failed delivery, not a queued, delivered or received one", () => {
	for (const status of ["Error", "Expired", "Bounced"]) {
		assert.equal(isFailedDelivery(status), true, status);
	}
	for (const status of ["", null, undefined, "Sending", "Sent", "Read"]) {
		assert.equal(isFailedDelivery(status), false, String(status));
	}
});

test("a thread opens on its latest email and on unread ones, the read history stays folded", () => {
	const thread = [
		{ name: "sent", sent_or_received: "Sent", seen: 1 },
		{ name: "read-reply", sent_or_received: "Received", seen: 1 },
		{ name: "unread-reply", sent_or_received: "Received", seen: 0 },
		{ name: "follow-up", sent_or_received: "Sent", seen: 1 },
	];
	assert.deepEqual([...openByDefault(thread)], ["unread-reply", "follow-up"]);
	assert.deepEqual([...openByDefault([])], []);
});
