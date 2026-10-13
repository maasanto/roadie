import assert from "node:assert/strict";
import { test } from "node:test";

// listFilters reads the page boot (the global __ and window.translations) at import time.
globalThis.window = globalThis;
window.translations = { Contains: "Contient" };
await import("./translation.js");
const { newFilter, operatorOptions, orderBy, queryFilters, quickValue, setQuickValue, sortEmptyLast } =
	await import("./listFilters.js");

const NAME = { fieldname: "title", label: "Name", type: "text" };
const CAPACITY = { fieldname: "capacity", label: "Capacity", type: "number" };
const RELEVANCE = { fieldname: "relevance", label: "Relevance", type: "rating" };
const MONTH = {
	fieldname: "usual_month",
	label: "Usual month",
	type: "select",
	options: [{ label: "mars", value: "March" }],
};
const ACTIVE = { fieldname: "is_active", label: "Active", type: "checkbox" };
const FIELDS = [NAME, CAPACITY, RELEVANCE, MONTH, ACTIVE];

test("each filter becomes the condition the server reads, in the database's own units", () => {
	const filters = [
		{ fieldname: "title", operator: "like", value: "jazz" },
		{ fieldname: "capacity", operator: ">=", value: "300" },
		{ fieldname: "relevance", operator: ">=", value: "3" },
		{ fieldname: "is_active", operator: "=", value: "No" },
		{ fieldname: "usual_month", operator: "is", value: "not set" },
	];

	assert.deepEqual(queryFilters(filters, FIELDS), {
		title: ["like", "%jazz%"],
		capacity: [">=", 300],
		relevance: [">=", 0.6],
		is_active: ["=", 0],
		usual_month: ["is", "not set"],
	});
});

test("a filter waiting for its value, or on a field the DocType lost, filters nothing", () => {
	const filters = [
		{ fieldname: "title", operator: "not like", value: "" },
		{ fieldname: "gone", operator: "=", value: "x" },
	];

	assert.deepEqual(queryFilters(filters, FIELDS), {});
});

test("a new filter starts on the field's first operator with a value that already filters", () => {
	assert.deepEqual(newFilter(MONTH), { fieldname: "usual_month", operator: "=", value: "March" });
	assert.deepEqual(newFilter(ACTIVE), { fieldname: "is_active", operator: "=", value: "Yes" });
	assert.deepEqual(newFilter(NAME), { fieldname: "title", operator: "like", value: "" });
});

test("a linked record is filtered by picking it, never by typing its id", () => {
	const VENUE = {
		fieldname: "venue",
		label: "Venue",
		type: "combobox",
		options: [{ label: "Le Trianon", value: "a1b2c3" }],
	};

	assert.deepEqual(newFilter(VENUE), { fieldname: "venue", operator: "=", value: "a1b2c3" });
	assert.deepEqual(queryFilters([newFilter(VENUE)], [VENUE]), { venue: ["=", "a1b2c3"] });
});

test("operators are offered in the member's language, and only those the field understands", () => {
	assert.equal(operatorOptions(NAME)[0].label, "Contient");
	assert.deepEqual(
		operatorOptions(ACTIVE).map((option) => option.value),
		["="]
	);
});

test("a quick filter sets, replaces and clears the one filter its field has", () => {
	let filters = [{ fieldname: "title", operator: "=", value: "Jazz à Vienne" }];

	filters = setQuickValue(filters, NAME, "vienne");
	assert.deepEqual(filters, [{ fieldname: "title", operator: "like", value: "vienne" }]);
	assert.equal(quickValue(filters, NAME), "vienne");

	filters = setQuickValue(filters, RELEVANCE, "4");
	assert.deepEqual(queryFilters(filters, FIELDS).relevance, [">=", 0.8]);

	filters = setQuickValue(filters, NAME, "");
	assert.deepEqual(
		filters.map((filter) => filter.fieldname),
		["relevance"]
	);
});

test("a quick filter shows empty when its field is filtered another way from the Filter menu", () => {
	assert.equal(quickValue([{ fieldname: "title", operator: "!=", value: "x" }], NAME), "");
});

test("the list keeps its own order until a member picks one, and the name breaks ties", () => {
	assert.equal(orderBy(null), "relevance desc, title asc");
	assert.equal(orderBy({ fieldname: "city", direction: "desc" }), "city desc, title asc");
	assert.equal(orderBy({ fieldname: "title", direction: "desc" }), "title desc");
});

test("rows without the sorted value move after the others, which keep the order the server gave them", () => {
	const gigs = [
		{ title: "Never set", application_opens: null },
		{ title: "Cleared", application_opens: "" },
		{ title: "September", application_opens: "2026-09-09" },
		{ title: "November", application_opens: "2026-11-01" },
	];
	assert.deepEqual(
		sortEmptyLast(gigs, "application_opens").map((gig) => gig.title),
		["September", "November", "Never set", "Cleared"]
	);
});
