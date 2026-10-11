import assert from "node:assert/strict";
import { test } from "node:test";

// gig.js reads the page boot (window.lang, window.translations) and the global __ at import time.
globalThis.window = globalThis;
window.lang = "fr";
const { formatDate, memberOptions } = await import("./gig.js");

test("a date in the current year is shown without its year", () => {
	const thisYear = new Date().getFullYear();
	assert.equal(formatDate(`${thisYear}-10-12`), "12 oct.");
});

test("a date in another year keeps its year, so next summer's festival is not mistaken for this one", () => {
	const nextYear = new Date().getFullYear() + 1;
	assert.equal(formatDate(`${nextYear}-07-14`), `14 juil. ${nextYear}`);
});

test("members are offered by full name and valued by their user", () => {
	assert.deepEqual(memberOptions([{ name: "jane@example.com", full_name: "Jane Doe" }]), [
		{ label: "Jane Doe", value: "jane@example.com" },
	]);
});

test("an absent member list yields no options", () => {
	assert.deepEqual(memberOptions(undefined), []);
});
