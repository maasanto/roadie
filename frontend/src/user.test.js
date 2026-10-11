import assert from "node:assert/strict";
import { test } from "node:test";

globalThis.window = {
	user: "john@example.com",
	user_full_name: "John Doe",
	user_image: "/files/john.png",
};
const { initials, user } = await import("./user.js");

test("initials takes the first and last word's first letter", () => {
	assert.equal(initials("John Doe"), "JD");
	assert.equal(initials("Jane van der Doe"), "JD");
});

test("a single word gives its first two letters", () => {
	assert.equal(initials("John"), "JO");
});

test("an empty name falls back to a placeholder", () => {
	assert.equal(initials(""), "?");
	assert.equal(initials(), "?");
});

test("user reads the member's name and picture from the boot", () => {
	assert.equal(user.name, "john@example.com");
	assert.equal(user.fullName, "John Doe");
	assert.equal(user.image, "/files/john.png");
});
