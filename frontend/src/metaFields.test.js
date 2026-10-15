import assert from "node:assert/strict";
import { test } from "node:test";

// translation.js reads the page boot (window.translations) and installs the global __ at import time.
globalThis.window = globalThis;
window.translations = { "Usual month": "Mois habituel", March: "Mars" };
await import("./translation.js");
const { fieldsFromMeta, isStalePick, optionsFor } = await import("./metaFields.js");

const festivalMeta = [
	{ fieldname: "title", fieldtype: "Data", label: "Name", reqd: 1 },
	{ fieldname: "website", fieldtype: "Data", label: "Website", options: "URL" },
	{ fieldname: "usual_month", fieldtype: "Select", label: "Usual month", options: "\nMarch" },
	{ fieldname: "details_section", fieldtype: "Section Break", label: "Details" },
	{ fieldname: "rider", fieldtype: "Attach", label: "Rider" },
	{ fieldname: "old_notes", fieldtype: "Small Text", label: "Old notes", hidden: 1 },
	{ fieldname: "budget", fieldtype: "Currency", label: "Budget", permlevel: 1 },
	{ fieldname: "camping", fieldtype: "Check", label: "Camping on site", reqd: 1, is_custom_field: 1 },
	{ fieldname: "listed_on", fieldtype: "Date", label: "Listed on", default: "Today", read_only: 1 },
];

test("a field added in Desk shows in the form, in the meta's order", () => {
	assert.deepEqual(
		fieldsFromMeta(festivalMeta)
			.filter(({ hidden }) => !hidden)
			.map(({ fieldname }) => fieldname),
		["title", "website", "usual_month", "camping", "listed_on"]
	);
});

test("a hidden field is kept, flagged, so it can be brought back", () => {
	const oldNotes = fieldsFromMeta(festivalMeta).find(({ fieldname }) => fieldname === "old_notes");
	assert.equal(oldNotes.hidden, true);
});

test("layout breaks, types the form cannot edit and higher permlevels stay out", () => {
	const fieldnames = fieldsFromMeta(festivalMeta).map(({ fieldname }) => fieldname);
	for (const fieldname of ["details_section", "rider", "budget"])
		assert.ok(!fieldnames.includes(fieldname));
});

test("labels and choices are translated, while stored values stay English", () => {
	const usualMonth = fieldsFromMeta(festivalMeta).find(({ fieldname }) => fieldname === "usual_month");
	assert.equal(usualMonth.label, "Mois habituel");
	assert.deepEqual(usualMonth.options, [{ label: "Mars", value: "March" }]);
});

test("a URL field gets a URL input and a mandatory field is required", () => {
	const [title, website] = fieldsFromMeta(festivalMeta);
	assert.equal(title.required, true);
	assert.equal(website.type, "url");
});

test("a mandatory checkbox can still be left unticked", () => {
	const camping = fieldsFromMeta(festivalMeta).find(({ fieldname }) => fieldname === "camping");
	assert.equal(camping.type, "checkbox");
	assert.equal(camping.required, false);
});

test("a read-only field is shown disabled, and its 'Today' default is left for the server to resolve", () => {
	const listedOn = fieldsFromMeta(festivalMeta).find(({ fieldname }) => fieldname === "listed_on");
	assert.equal(listedOn.disabled, true);
	assert.equal(listedOn.default, undefined);
});

test("a control override turns a Link into a picker the generic mapping does not offer", () => {
	const gigMeta = [{ fieldname: "venue", fieldtype: "Link", label: "Venue", options: "Venue" }];
	const options = [{ label: "Acme Hall", value: "acme-hall" }];
	const [venue] = fieldsFromMeta(gigMeta, { venue: { type: "combobox", options } });
	assert.equal(venue.type, "combobox");
	assert.deepEqual(venue.options, options);
});

const editionField = {
	fieldname: "festival_edition",
	dependsOn: "festival",
	options: [
		{ label: "Acme Festival 2027", value: "acme-2027", festival: "acme" },
		{ label: "Acme Nights 2027", value: "nights-2027", festival: "nights" },
	],
};

test("a gig's edition picker offers the chosen festival's editions, or all of them with no festival", () => {
	const valuesFor = (form) => optionsFor(editionField, form).map(({ value }) => value);

	assert.deepEqual(valuesFor({ festival: "acme" }), ["acme-2027"]);
	assert.deepEqual(valuesFor({ festival: "" }), ["acme-2027", "nights-2027"]);
});

test("an edition of another festival or of a cleared one goes when the festival changes, one not loaded yet stays", () => {
	assert.equal(isStalePick(editionField, { festival: "nights", festival_edition: "acme-2027" }), true);
	assert.equal(isStalePick(editionField, { festival: "acme", festival_edition: "acme-2027" }), false);
	assert.equal(isStalePick(editionField, { festival: "acme", festival_edition: "not-loaded-yet" }), false);
	assert.equal(isStalePick(editionField, { festival: "", festival_edition: "acme-2027" }), true);
	assert.equal(
		isStalePick({ ...editionField, dependsOn: undefined }, { festival_edition: "acme-2027" }),
		false
	);
});
