import assert from "node:assert/strict";
import { test } from "node:test";
import { createApp } from "vue";
import { createMemoryHistory, createRouter } from "vue-router";
import { useOpenRecord } from "./openRecord.js";

// A browser's history state names the entry before the current one; memory history leaves it empty.
const history = createMemoryHistory();
let previousLocation = null;
const push = history.push.bind(history);
history.push = (to, data) => {
	previousLocation = history.location;
	push(to, data);
};
Object.defineProperty(history, "state", { get: () => ({ back: previousLocation }) });

const screen = { render: () => null };
const router = createRouter({
	history,
	routes: [
		{ path: "/", name: "Pipeline", component: screen },
		{ path: "/festivals", name: "Festivals", component: screen },
	],
});
const app = createApp(screen).use(router);
const openGig = () => app.runWithContext(() => useOpenRecord("gig"));
const query = () => router.currentRoute.value.query;
const settle = () => new Promise((resolve) => setTimeout(resolve));

test("a gig opened from the list stays in the address until Close goes back to the list", async () => {
	await router.push("/?view=list");
	const gig = openGig();
	assert.deepEqual(gig.routeTo("gig-1"), { query: { view: "list", gig: "gig-1" }, replace: false });

	gig.open("gig-1");
	await settle();
	assert.deepEqual(query(), { view: "list", gig: "gig-1" });
	assert.equal(gig.isOpen.value, true);
	assert.equal(gig.name.value, "gig-1");

	// A reload reads the gig back from the address.
	assert.equal(openGig().name.value, "gig-1");

	// Closing twice, as a double click does, still lands on the list rather than the page before it.
	gig.close();
	gig.close();
	await settle();
	assert.deepEqual(query(), { view: "list" });
	assert.equal(gig.isOpen.value, false);
	// The panel keeps its gig while it closes, rather than turning into a blank new one.
	assert.equal(gig.name.value, "gig-1");
	// Close went back rather than adding an entry, so Forward opens the gig again.
	router.forward();
	await settle();
	assert.equal(query().gig, "gig-1");
});

test("moving from gig to gig keeps one entry, so Close still returns to the list", async () => {
	await router.push("/?view=list");
	const gig = openGig();
	gig.open("gig-1");
	await settle();
	gig.open("gig-2");
	await settle();
	assert.equal(gig.name.value, "gig-2");

	gig.close();
	await settle();
	assert.deepEqual(query(), { view: "list" });
	// The list is directly behind the gig the member ended on.
	router.forward();
	await settle();
	assert.equal(query().gig, "gig-2");
	router.back();
	await settle();
	assert.deepEqual(query(), { view: "list" });
});

test("after a reload, Close stays on the page instead of going back to the one before it", async () => {
	await router.push("/?view=list");
	await router.push("/?view=list&gig=gig-1");
	const gig = openGig();
	assert.equal(gig.isOpen.value, true);

	gig.close();
	await settle();
	assert.deepEqual(query(), { view: "list" });
	router.forward();
	await settle();
	assert.equal(query().gig, undefined);
});

test("a gig reached from elsewhere closes in place, leaving the previous page in history", async () => {
	await router.push("/festivals");
	await router.push({ name: "Pipeline", query: { gig: "gig-2" } });
	const gig = openGig();
	assert.equal(gig.isOpen.value, true);

	gig.close();
	await settle();
	assert.equal(router.currentRoute.value.name, "Pipeline");
	assert.deepEqual(query(), {});
});

test("a new gig opens without touching the address, and closing it leaves the address alone", async () => {
	await router.push("/?view=list");
	const gig = openGig();
	gig.create();
	assert.equal(gig.isOpen.value, true);
	assert.equal(gig.name.value, null);

	gig.close();
	await settle();
	assert.equal(gig.isOpen.value, false);
	assert.deepEqual(query(), { view: "list" });
});
