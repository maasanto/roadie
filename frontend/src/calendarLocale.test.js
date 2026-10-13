import assert from "node:assert/strict";
import { test } from "node:test";

// calendarLocale.js reads the page boot (window.lang, window.week_start) at import time.
globalThis.window = globalThis;
window.lang = "fr";
window.week_start = 1;
const { monthNames, weekdayInitials } = await import("./calendarLocale.js");

test("a French site whose week starts on Monday heads the calendar L M M J V S D", () => {
	assert.deepEqual(weekdayInitials, ["L", "M", "M", "J", "V", "S", "D"]);
});

test("month names follow the site language", () => {
	assert.equal(monthNames[0], "janv.");
	assert.equal(monthNames[11], "déc.");
});
