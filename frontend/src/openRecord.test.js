import assert from "node:assert/strict";
import { test } from "node:test";
import { createApp, effectScope } from "vue";
import { createMemoryHistory, createRouter } from "vue-router";

globalThis.window = globalThis;
await import("./translation.js");
const { trackDraft } = await import("./draft.js");
const { useOpenRecord } = await import("./openRecord.js");

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
// Each screen's scope ends with the test, as an unmount would, so its guard does not outlive it.
let screenScope;
test.beforeEach(() => (screenScope = effectScope()));
test.afterEach(() => screenScope.stop());
const openGig = () => screenScope.run(() => app.runWithContext(() => useOpenRecord("gig")));
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

test("an unsent email asks before another gig or Back replaces it, and Close asks only once", async (t) => {
	let questions = 0;
	let answer = false;
	window.confirm = () => {
		questions++;
		return answer;
	};
	const forgetDraft = trackDraft(() => true);
	t.after(() => {
		forgetDraft();
		delete window.confirm;
	});

	await router.push("/?view=list");
	const gig = openGig();
	gig.open("gig-1");
	await settle();
	questions = 0;

	gig.open("gig-2");
	await settle();
	assert.equal(questions, 1);
	assert.equal(query().gig, "gig-1", "a refusal keeps the gig and its email");
	router.back();
	await settle();
	assert.equal(questions, 2);
	assert.equal(query().gig, "gig-1");

	// The panel's Close button has asked before it closes.
	gig.close();
	await settle();
	assert.equal(questions, 2);
	assert.deepEqual(query(), { view: "list" });

	answer = true;
	gig.create();
	gig.open("gig-3");
	await settle();
	assert.equal(
		questions,
		3,
		"a gig created in the panel stays out of the address, and its email counts too"
	);
	assert.equal(query().gig, "gig-3");
});

test("a close overtaken by reopening the gig still lets the next Close close", async () => {
	await router.push("/?view=list");
	await router.push("/?view=list&gig=gig-1");
	const gig = openGig();
	gig.close();
	gig.open("gig-1");
	await settle();
	assert.equal(query().gig, "gig-1");

	gig.close();
	await settle();
	assert.deepEqual(query(), { view: "list" });
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
