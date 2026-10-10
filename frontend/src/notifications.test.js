import assert from "node:assert/strict";
import { test } from "node:test";

globalThis.window = globalThis;
await import("./translation.js");
const { relativeDate, unreadCount } = await import("./notifications.js");

test("unreadCount counts the notifications that were not read yet", () => {
	assert.equal(unreadCount([{ read: 0 }, { read: 1 }, { read: 0 }]), 2);
	assert.equal(unreadCount([]), 0);
	assert.equal(unreadCount(), 0);
});

test("relativeDate labels a notification from the recent past", () => {
	const now = new Date("2027-07-14T12:00:00");
	assert.equal(relativeDate("2027-07-14 11:59:30", now), "Just now");
	assert.equal(relativeDate("2027-07-14 11:30:00", now), "30 min ago");
	assert.equal(relativeDate("2027-07-14 09:00:00", now), "3 h ago");
});
