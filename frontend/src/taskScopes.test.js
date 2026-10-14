import assert from "node:assert/strict";
import { test } from "node:test";

globalThis.window = globalThis;
await import("./translation.js");
const { TASK_SCOPES, assigneeAvatar, scopeFromQuery } = await import("./taskScopes.js");

test("each scope asks the server for its own tasks", () => {
	assert.deepEqual(TASK_SCOPES.mine.filters("jane@example.com"), { assignee: "jane@example.com" });
	assert.deepEqual(TASK_SCOPES.unassigned.filters("jane@example.com"), { assignee: ["is", "not set"] });
	assert.deepEqual(TASK_SCOPES.everyone.filters("jane@example.com"), {});
});

test("a missing or unknown scope in the address shows the member's own tasks", () => {
	assert.equal(scopeFromQuery(undefined), "mine");
	assert.equal(scopeFromQuery("someone-else"), "mine");
	assert.equal(scopeFromQuery("constructor"), "mine");
	assert.equal(scopeFromQuery("unassigned"), "unassigned");
});

test("a task shows its assignee, and a member who left still shows by user ID", () => {
	const jane = { name: "jane@example.com", full_name: "Jane Doe" };
	const members = { [jane.name]: jane };

	assert.equal(assigneeAvatar({ assignee: jane.name }, members), jane);
	assert.deepEqual(assigneeAvatar({ assignee: "max@example.com" }, members), {
		full_name: "max@example.com",
	});
	assert.equal(assigneeAvatar({ assignee: null }, members), null);
});

test("no avatar is guessed before the member list has loaded", () => {
	assert.equal(assigneeAvatar({ assignee: "jane@example.com" }, undefined), null);
});
