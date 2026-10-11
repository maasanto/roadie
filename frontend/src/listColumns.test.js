import assert from "node:assert/strict";
import { test } from "node:test";

// listColumns reads the page boot (the global __, window.lang and window.translations) at import time.
globalThis.window = globalThis;
window.lang = "en";
window.translations = { March: "mars" };
await import("./translation.js");
const {
	columnFromField,
	columnsFor,
	defaultColumns,
	fetchFields,
	formatCell,
	isNameColumn,
	moveColumn,
	parseColumns,
} = await import("./listColumns.js");

const fieldnames = (columns) => columns.map((column) => column.fieldname);

test("a type opens with the columns that suit it", () => {
	assert.deepEqual(fieldnames(defaultColumns("Festival")), ["title", "relevance", "city", "usual_month"]);
	assert.deepEqual(fieldnames(defaultColumns("Venue")), ["title", "relevance", "city", "capacity"]);
	assert.deepEqual(fieldnames(defaultColumns("Promoter")), ["title", "relevance", "city"]);
	assert.deepEqual(fieldnames(defaultColumns("Band")), ["title", "relevance", "city", "genre"]);
	assert.deepEqual(defaultColumns("Unknown"), []);
});

test("a member with no saved layout gets the defaults", () => {
	for (const saved of [null, undefined, "", "[]", "not json at all", "{}"]) {
		assert.deepEqual(fieldnames(columnsFor("Venue", saved)), ["title", "relevance", "city", "capacity"]);
		assert.equal(columnsFor("Venue", saved)[0].format, "text");
	}
});

test("a saved layout wins, in the order it was saved", () => {
	const saved = JSON.stringify([
		{ fieldname: "title", label: "Name" },
		{ fieldname: "capacity", label: "Capacity", format: "number" },
		{ fieldname: "city", label: "City" },
	]);

	assert.deepEqual(fieldnames(columnsFor("Venue", saved)), ["title", "capacity", "city"]);
});

test("columns that no longer name a field are dropped, and the name column always leads", () => {
	const saved = JSON.stringify([
		{ fieldname: "capacity", label: "Capacity" },
		{ label: "No fieldname" },
		null,
		{ fieldname: "" },
	]);

	assert.deepEqual(fieldnames(columnsFor("Venue", saved)), ["title", "capacity"]);
});

test("a field named twice in a hand-edited layout shows one column", () => {
	const saved = JSON.stringify([
		{ fieldname: "city", label: "City" },
		{ fieldname: "city", label: "Ville" },
	]);

	assert.deepEqual(fieldnames(columnsFor("Venue", saved)), ["title", "city"]);
});

test("the name column leads whatever position a hand-edited row gave it", () => {
	const saved = JSON.stringify([
		{ fieldname: "capacity", label: "Capacity" },
		{ fieldname: "title", label: "Name" },
	]);

	assert.deepEqual(fieldnames(columnsFor("Venue", saved)), ["title", "capacity"]);
});

test("a column keeps its label and gains a format, however it was stored", () => {
	const columns = columnsFor("Venue", JSON.stringify([{ fieldname: "capacity" }]));

	assert.deepEqual(columns[0], { fieldname: "title", label: "Name", format: "text" });
	assert.deepEqual(columns[1], { fieldname: "capacity", label: "capacity", format: "text" });
});

test("a column of an unknown format shows as stored", () => {
	const columns = columnsFor("Band", JSON.stringify([{ fieldname: "genre", format: "wat" }]));

	assert.equal(columns[1].format, "text");
});

test("the list fetches the row's name first, then each column once", () => {
	const columns = [{ fieldname: "title" }, { fieldname: "city" }, { fieldname: "title" }];

	assert.deepEqual(fetchFields(columns), ["name", "city", "title"]);
});

test("the list fetches what the search reads, whether or not those columns are shown", () => {
	const columns = [{ fieldname: "title" }, { fieldname: "genre" }];

	assert.deepEqual(fetchFields(columns, ["title", "city"]), ["name", "city", "genre", "title"]);
});

test("reordering columns leaves what is fetched, and so the request, alone", () => {
	const columns = defaultColumns("Venue");
	const reordered = moveColumn(columns, "capacity", -1);

	assert.deepEqual(fetchFields(reordered, ["title", "city"]), fetchFields(columns, ["title", "city"]));
});

test("a column moves one slot at a time, and never displaces the name column", () => {
	const columns = columnsFor("Venue", [
		{ fieldname: "title" },
		{ fieldname: "city" },
		{ fieldname: "capacity" },
	]);

	assert.deepEqual(fieldnames(moveColumn(columns, "capacity", -1)), ["title", "capacity", "city"]);
	assert.deepEqual(fieldnames(moveColumn(columns, "city", 1)), ["title", "capacity", "city"]);
});

test("the name column cannot move, and neither end can be stepped past", () => {
	const columns = columnsFor("Venue", [
		{ fieldname: "title" },
		{ fieldname: "city" },
		{ fieldname: "capacity" },
	]);

	assert.deepEqual(moveColumn(columns, "title", 1), columns);
	assert.deepEqual(fieldnames(moveColumn(columns, "city", -1)), ["title", "city", "capacity"]);
	assert.deepEqual(moveColumn(columns, "city", -2), columns);
	assert.deepEqual(moveColumn(columns, "capacity", 1), columns);
	assert.deepEqual(moveColumn(columns, "missing", 1), columns);
});

test("a field picked from the meta becomes a column that reads its value", () => {
	assert.deepEqual(columnFromField({ fieldname: "capacity", label: "Capacity", type: "number" }), {
		fieldname: "capacity",
		label: "Capacity",
		format: "number",
	});
	assert.equal(columnFromField({ type: "select" }).format, "label");
	assert.equal(columnFromField({ type: "multiselect" }).format, "list");
	assert.equal(columnFromField({ type: "rating" }).format, "rating");
	assert.equal(columnFromField({ type: "date" }).format, "text");
});

test("a number column groups its digits in the language the member is reading", () => {
	const column = { fieldname: "capacity", format: "number" };

	assert.equal(formatCell(column, { capacity: 1200 }), "1,200");
	assert.equal(formatCell(column, { capacity: "800" }), "800");
	assert.equal(formatCell(column, { capacity: "roomy" }), "roomy");

	window.lang = "fr";
	assert.match(formatCell(column, { capacity: 1200 }), /^1[\s\u202f\u00a0]200$/u);
});

test("a label column translates a value the database keeps in English", () => {
	assert.equal(formatCell({ fieldname: "usual_month", format: "label" }, { usual_month: "March" }), "mars");
	assert.equal(formatCell({ fieldname: "usual_month", format: "label" }, { usual_month: "July" }), "July");
});

test("a list column joins what the database keeps as one string", () => {
	const column = { fieldname: "genre", format: "list" };

	assert.equal(formatCell(column, { genre: "Rock, Ska" }), "Rock, Ska");
	assert.equal(formatCell(column, { genre: "Jazz" }), "Jazz");
});

test("an empty cell shows nothing, whatever the format", () => {
	for (const format of ["text", "number", "label", "list"]) {
		const column = { fieldname: "city", format };
		assert.equal(formatCell(column, { city: "" }), "");
		assert.equal(formatCell(column, {}), "");
		assert.equal(formatCell(column, { city: null }), "");
	}
});

test("only the title column counts as the name column", () => {
	assert.equal(isNameColumn({ fieldname: "title" }), true);
	assert.equal(isNameColumn({ fieldname: "city" }), false);
});

test("parseColumns only ever returns a list", () => {
	assert.deepEqual(parseColumns(undefined), []);
	assert.deepEqual(parseColumns('{"fieldname": "title"}'), []);
	assert.deepEqual(parseColumns("[1,2]"), [1, 2]);
});
