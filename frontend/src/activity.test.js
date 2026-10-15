import assert from "node:assert/strict";
import { test } from "node:test";

// activity reads the page boot (the global __ and window.translations) at import time.
globalThis.window = globalThis;
window.lang = "en";
window.translations = { Status: "Statut", Contacted: "Contacté" };
await import("./translation.js");
const { describeActivity } = await import("./activity.js");

const change = (fieldtype, from, to, label = "Field") => ({ type: "changed", label, fieldtype, from, to });

test("a field and a choice read in the member's language", () => {
	assert.equal(
		describeActivity(change("Select", "Idea", "Contacted", "Status")),
		"changed Statut from Idea to Contacté"
	);
});

test("a value set or cleared reads as such rather than as a change from or to nothing", () => {
	assert.equal(describeActivity(change("Data", "", "Lyon", "City")), "set City to Lyon");
	assert.equal(describeActivity(change("Data", "Lyon", null, "City")), "cleared City");
});

test("a checkbox and a rating, which Version keeps raw, read as the form shows them", () => {
	assert.equal(describeActivity(change("Check", 0, 1, "Done")), "changed Done from No to Yes");
	assert.equal(describeActivity(change("Rating", 0.2, 0.8)), "changed Field from ★☆☆☆☆ to ★★★★☆");
});

test("a date or a fee Version already formatted in the site's format reads as kept", () => {
	assert.equal(
		describeActivity(change("Date", "01-03-2020", "02-03-2020")),
		"changed Field from 01-03-2020 to 02-03-2020"
	);
	assert.equal(
		describeActivity(change("Currency", "€ 1 500,00", "€ 750,00")),
		"changed Field from € 1 500,00 to € 750,00"
	);
});

test("a fee or a rating of 0 reads as unset, while an unticked box is a No", () => {
	assert.equal(describeActivity(change("Currency", 0, "€ 1 500,00", "Fee")), "set Fee to € 1 500,00");
	assert.equal(describeActivity(change("Rating", 0, 0.6, "Relevance")), "set Relevance to ★★★☆☆");
	assert.equal(describeActivity(change("Check", 1, 0, "Done")), "changed Done from Yes to No");
});
