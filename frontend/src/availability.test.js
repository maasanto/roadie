import assert from "node:assert/strict";
import { test } from "node:test";

// availability reads the page boot (the global __) at import time.
globalThis.window = globalThis;
window.lang = "en";
window.translations = {};
await import("./translation.js");
const { availabilitySummary, confirmBooking } = await import("./availability.js");

test("a gig card's count turns red as soon as one member can't play, green once everyone can", () => {
	const answers = (...values) => values.map((answer) => ({ answer }));

	assert.deepEqual(availabilitySummary(answers("Yes", "")), {
		available: 1,
		declined: 0,
		asked: 2,
		tone: "",
	});
	assert.equal(availabilitySummary(answers("Yes", "No", "")).tone, "text-ink-red-7");
	assert.equal(availabilitySummary(answers("Yes", "No", "")).declined, 1);
	assert.equal(availabilitySummary(answers("Yes", "Yes")).tone, "text-ink-green-6");
	assert.equal(availabilitySummary(undefined).asked, 0);
});

const members = [
	{ name: "john@example.com", full_name: "John Doe" },
	{ name: "jane@example.com", full_name: "Jane Doe" },
];

test("booking a gig nobody declined asks nothing", () => {
	window.confirm = () => assert.fail("asked for confirmation");
	const rows = [
		{ member: "john@example.com", answer: "Yes" },
		{ member: "jane@example.com", answer: "" },
	];
	assert.equal(confirmBooking([{ title: "Acme Festival", rows }], members), true);
});

test("booking before the members have loaded still warns, by address", () => {
	let asked;
	window.confirm = (message) => ((asked = message), true);
	const rows = [{ member: "john@example.com", answer: "No" }];

	assert.equal(confirmBooking([{ title: "Acme Festival", rows }], null), true);
	assert.equal(asked, "john@example.com can't play Acme Festival.\nBook anyway?");
});

test("booking a gig someone can't play names them and lets the member go ahead or not", () => {
	let asked;
	window.confirm = (message) => ((asked = message), false);
	const rows = [
		{ member: "john@example.com", answer: "No" },
		{ member: "jane@example.com", answer: "Yes" },
	];

	assert.equal(confirmBooking([{ title: "Acme Festival", rows }], members), false);
	assert.equal(asked, "John Doe can't play Acme Festival.\nBook anyway?");
});

test("booking several gigs at once names who can't play each one, in one question", () => {
	let asked;
	window.confirm = (message) => ((asked = message), true);
	const gigs = [
		{ title: "Acme Festival", rows: [{ member: "john@example.com", answer: "No" }] },
		{ title: "Club Night", rows: [{ member: "john@example.com", answer: "Yes" }] },
		{ title: "Open Air", rows: [{ member: "jane@example.com", answer: "No" }] },
		{ title: "Never asked", rows: undefined },
	];

	assert.equal(confirmBooking(gigs, members), true);
	assert.equal(asked, "John Doe can't play Acme Festival.\nJane Doe can't play Open Air.\nBook anyway?");
});
