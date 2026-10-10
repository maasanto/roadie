import assert from "node:assert/strict";
import { test } from "node:test";

globalThis.window = globalThis;
await import("./translation.js");
const { joinList, splitList } = await import("./directory.js");

test("splitList reads an empty stored value as no genre", () => {
	assert.deepEqual(splitList(""), []);
	assert.deepEqual(splitList(null), []);
});

test("splitList reads a single genre", () => {
	assert.deepEqual(splitList("Rock"), ["Rock"]);
});

test("splitList reads several genres", () => {
	assert.deepEqual(splitList("Rock, Jazz, Funk"), ["Rock", "Jazz", "Funk"]);
});

test("splitList keeps the spaces inside a genre name", () => {
	assert.deepEqual(splitList("Hip Hop, Rhythm and Blues"), ["Hip Hop", "Rhythm and Blues"]);
});

test("joinList writes an empty string for no genre", () => {
	assert.equal(joinList([]), "");
	assert.equal(joinList(null), "");
});

test("joinList joins several genres", () => {
	assert.equal(joinList(["Rock", "Jazz"]), "Rock, Jazz");
});

test("a genre list round-trips through storage and back", () => {
	const genres = ["Hip Hop", "Rhythm and Blues", "Rock"];
	assert.deepEqual(splitList(joinList(genres)), genres);
});
