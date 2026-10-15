import assert from "node:assert/strict";
import { test } from "node:test";
import { computed, createApp } from "vue";
import { createMemoryHistory, createRouter } from "vue-router";

// listFilters reads the page boot (the global __ and window.translations) at import time.
globalThis.window = globalThis;
window.translations = {};
await import("./translation.js");
const { keepListQueries, useListQuery } = await import("./listQuery.js");

const screen = { render: () => null };
const router = createRouter({
	history: createMemoryHistory(),
	routes: [
		{ path: "/", name: "Pipeline", component: screen },
		{ path: "/festivals", name: "Festivals", component: screen },
	],
});
keepListQueries(router);
const app = createApp(screen).use(router);

const meta = { data: { fields: [] }, error: null };
const fields = computed(() => [{ fieldname: "city", label: "City", type: "text" }]);
const festivalsList = () => app.runWithContext(() => useListQuery(meta, fields, fields));
const query = () => router.currentRoute.value.query;
// A filter or sort change replaces the address, which lands once the navigation resolves.
const settle = () => new Promise((resolve) => setTimeout(resolve));

test("a list left for another screen comes back filtered and sorted, whichever link opens it", async () => {
	await router.push("/festivals");
	const { filters, sort } = festivalsList();
	filters.value = [{ fieldname: "city", operator: "like", value: "Lyon" }];
	await settle();
	sort.value = { fieldname: "city", direction: "desc" };
	await settle();

	await router.push("/");
	await router.push("/festivals");
	assert.deepEqual(query(), { filters: '[["city","like","Lyon"]]', sort: "city:desc" });

	// A notification opening a record keeps the list around it.
	await router.push({ name: "Festivals", query: { entry: "Festival:acme" } });
	assert.equal(query().entry, "Festival:acme");
	assert.equal(query().filters, '[["city","like","Lyon"]]');

	// A link carrying its own filters wins over the remembered ones.
	await router.push({ name: "Festivals", query: { filters: '[["city","like","Paris"]]' } });
	assert.deepEqual(query(), { filters: '[["city","like","Paris"]]' });
});

test("a cleared list stays cleared, on the screen and when it is opened again", async () => {
	await router.push("/festivals");
	const { filters, sort } = festivalsList();
	filters.value = [];
	await settle();
	sort.value = null;
	await settle();
	assert.deepEqual(query(), {});

	await router.push("/");
	await router.push("/festivals");
	assert.deepEqual(query(), {});
});

test("Back leaves a list filtered while a record was open over it, which a link still opens filtered", async () => {
	await router.push("/");
	await router.push("/festivals");
	await router.push({ name: "Festivals", query: { entry: "Festival:acme" } });
	const { filters } = festivalsList();
	filters.value = [{ fieldname: "city", operator: "like", value: "Lyon" }];
	await settle();
	await router.replace({ name: "Festivals", query: { filters: query().filters } });

	router.back();
	await settle();
	assert.deepEqual(query(), {});
	router.back();
	await settle();
	assert.equal(router.currentRoute.value.name, "Pipeline");

	await router.push("/festivals");
	assert.deepEqual(query(), { filters: '[["city","like","Lyon"]]' });
});
