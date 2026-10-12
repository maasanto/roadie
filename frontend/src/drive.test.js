import assert from "node:assert/strict";
import { test } from "node:test";

import { canLink, linkTarget } from "./drive.js";

const pressKit = { name: "press-kit", file_name: "Press kit", is_folder: 1, share: 1 };
const bio = { name: "bio", file_name: "Bio.txt", is_folder: 0, share: 1 };

test("the picked item is linked rather than the folder around it", () => {
	assert.equal(linkTarget(bio, pressKit), bio);
});

test("with nothing picked, the folder being browsed is linked", () => {
	assert.equal(linkTarget(null, pressKit), pressKit);
});

test("Drive's own homes are never linked, so nothing is", () => {
	const site = { name: "Drive", file_name: "Site", is_folder: 1 };
	assert.equal(linkTarget(null, site), null);
	assert.equal(linkTarget(null, undefined), null);
});

test("a folder only a bandmate can share is not linked, unless it is already public", () => {
	const theirs = { ...pressKit, share: 0, share_count: 1 };
	assert.equal(linkTarget(null, theirs), null);
	assert.ok(canLink({ ...theirs, share_count: -2 }));
});
