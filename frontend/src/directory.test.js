import assert from "node:assert/strict";
import { test } from "node:test";

globalThis.window = globalThis;
await import("./translation.js");
const { joinList, splitList, toFraction, toStars } = await import("./directory.js");

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

test("a relevance Desk set to three stars of five reads as three stars, and is stored back the same", () => {
	assert.equal(toStars(0.6), 3);
	assert.equal(toFraction(3), 0.6);
	for (const stars of [0, 1, 2, 3, 4, 5]) assert.equal(toStars(toFraction(stars)), stars);
});

test("an unrated entry reads as no stars", () => {
	assert.equal(toStars(null), 0);
	assert.equal(toStars(""), 0);
	assert.equal(toFraction(0), 0);
});

test("a rating stored on another scale snaps to the nearest star", () => {
	assert.equal(toStars(0.7), 4);
	assert.equal(toStars("0.30"), 2);
});
