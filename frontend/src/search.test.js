import assert from "node:assert/strict";
import { test } from "node:test";

globalThis.window = globalThis;
await import("./translation.js");
const { RESULTS_PER_GROUP, resultRoute, searchGroups } = await import("./search.js");

const grouped = [
	{ doctype: "Gig", results: [{ name: "gig-1", title: "Acme Summer Fest" }] },
	{ doctype: "Festival", results: [{ name: "festival-1", title: "Acme Festival", city: "Lyon" }] },
];

test("results are grouped by type in a fixed order, each item stamped with its doctype", () => {
	const groups = searchGroups("acme", grouped);

	assert.deepEqual(
		groups.map((group) => group.doctype),
		["Gig", "Festival"]
	);
	assert.equal(groups[0].title, "Gigs");
	assert.equal(groups[0].items[0].doctype, "Gig");
	assert.equal(groups[1].items[0].city, "Lyon");
});

test("an empty query yields no groups, even with stale results", () => {
	assert.deepEqual(searchGroups("   ", grouped), []);
});

test("each group is capped and empty groups are dropped", () => {
	const many = [
		{
			doctype: "Gig",
			results: Array.from({ length: 8 }, (_, index) => ({
				name: `gig-${index}`,
				title: `Gig ${index}`,
			})),
		},
		{ doctype: "Band", results: [] },
	];
	const groups = searchGroups("gig", many);

	assert.equal(groups.length, 1);
	assert.equal(groups[0].items.length, RESULTS_PER_GROUP);
});

test("a result routes to the screen that opens it", () => {
	assert.deepEqual(resultRoute({ doctype: "Gig", name: "gig-1" }), {
		name: "Pipeline",
		query: { gig: "gig-1" },
	});
	assert.deepEqual(resultRoute({ doctype: "Band Task", name: "task-1" }), {
		name: "MyTasks",
		query: { task: "task-1" },
	});
	assert.deepEqual(resultRoute({ doctype: "Venue", name: "venue-1" }), {
		name: "Venues",
		query: { entry: "Venue:venue-1" },
	});
	assert.deepEqual(resultRoute({ doctype: "Festival", name: "festival-1" }), {
		name: "Festivals",
		query: { entry: "Festival:festival-1" },
	});
});
