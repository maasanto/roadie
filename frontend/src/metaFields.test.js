import assert from "node:assert/strict";
import { test } from "node:test";

// translation.js reads the page boot (window.translations) and installs the global __ at import time.
globalThis.window = globalThis;
window.translations = { "Usual month": "Mois habituel", March: "Mars" };
await import("./translation.js");
const { fieldsFromMeta, isStalePick, optionsFor, valuesFromPick } = await import("./metaFields.js");

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
	assert.equal(venue.linkTo, "Venue", "the picker knows which record to open");
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

const gigFields = fieldsFromMeta([
	{ fieldname: "title", fieldtype: "Data", label: "Title" },
	{ fieldname: "notes", fieldtype: "Small Text", label: "Notes" },
	{ fieldname: "custom_city", fieldtype: "Data", label: "City", is_custom_field: 1 },
	{ fieldname: "custom_usual_month", fieldtype: "Data", label: "Usual month", is_custom_field: 1 },
	{ fieldname: "custom_drive_time", fieldtype: "Int", label: "Drive time", is_custom_field: 1 },
	{ fieldname: "custom_camping", fieldtype: "Check", label: "Camping", is_custom_field: 1 },
	{ fieldname: "fee", fieldtype: "Currency", label: "Fee" },
]);
const festival = {
	name: "acme",
	title: "Acme Open Air",
	notes: "Ask for the side stage",
	city: "Lyon",
	usual_month: "July",
	custom_drive_time: 180,
	custom_camping: 1,
	fee: 0,
};

test("a picked festival fills the gig's empty fields it shares, a field added from the form included, not a 0", () => {
	const form = {
		title: "",
		notes: "",
		custom_city: "",
		custom_usual_month: "",
		custom_drive_time: "",
		fee: "",
	};
	assert.deepEqual(valuesFromPick(gigFields, form, festival), {
		custom_city: "Lyon",
		custom_usual_month: "July",
		custom_drive_time: 180,
	});
});

test("a pick never overwrites what the member filled, nor the festival's own title, notes or checkboxes", () => {
	const form = {
		title: "",
		notes: "",
		custom_city: "Lille",
		custom_usual_month: "",
		custom_camping: false,
	};
	assert.deepEqual(valuesFromPick(gigFields, form, { ...festival, usual_month: "" }), {
		custom_drive_time: 180,
	});
});

test("picking another festival replaces what the first one filled, except what the member changed since", () => {
	const firstFill = { custom_city: "Lyon", custom_usual_month: "July", custom_drive_time: 180 };
	const form = { ...firstFill, custom_city: "Roubaix" };
	const otherFestival = { name: "doe", title: "Doe Nights", city: "Nantes", custom_drive_time: 420 };
	assert.deepEqual(valuesFromPick(gigFields, form, otherFestival, firstFill), {
		custom_usual_month: "",
		custom_drive_time: 420,
	});
});

test("clearing the festival blanks only what it filled and the member left alone", () => {
	const firstFill = { custom_city: "Lyon", custom_drive_time: 180 };
	const form = { custom_city: "Lyon", custom_drive_time: 200 };
	assert.deepEqual(valuesFromPick(gigFields, form, {}, firstFill), { custom_city: "" });
});

test("a record's own columns never fill a field added under the same name", () => {
	const fields = fieldsFromMeta([{ fieldname: "custom_owner", fieldtype: "Data", label: "Owner" }]);
	assert.deepEqual(valuesFromPick(fields, { custom_owner: "" }, { owner: "john@example.com" }), {});
});
