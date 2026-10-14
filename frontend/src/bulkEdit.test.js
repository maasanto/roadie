import assert from "node:assert/strict";
import { test } from "node:test";
import { DELETE_BATCH_SIZE, UPDATE_BATCH_SIZE, runInBatches } from "./bulkEdit.js";

const gigNames = (count) => Array.from({ length: count }, (unused, index) => `gig-${index}`);

test("a large selection is sent in batches Frappe keeps in the request, and every failure is reported", async () => {
	const batchSizes = [];
	const failed = await runInBatches(gigNames(45), UPDATE_BATCH_SIZE, async (batch) => {
		batchSizes.push(batch.length);
		return batch.filter((name) => name.endsWith("0"));
	});
	assert.deepEqual(batchSizes, [19, 19, 7]);
	assert.deepEqual(failed, ["gig-0", "gig-10", "gig-20", "gig-30", "gig-40"]);
});

test("a batch whose request fails counts as failed whole, and the batches after it still go", async () => {
	let batchCount = 0;
	const failed = await runInBatches(gigNames(45), UPDATE_BATCH_SIZE, async (batch) => {
		if (++batchCount === 2) throw new Error("Gig gig-25 not found");
		return [];
	});
	assert.equal(batchCount, 3);
	assert.deepEqual(failed, gigNames(38).slice(19));
});

test("a deletion goes in batches of ten, past which Frappe would delete in the background", async () => {
	const batchSizes = [];
	const failed = await runInBatches(gigNames(25), DELETE_BATCH_SIZE, async (batch) => {
		batchSizes.push(batch.length);
		return batch.includes("gig-12") ? ["gig-12"] : [];
	});
	assert.deepEqual(batchSizes, [10, 10, 5]);
	assert.deepEqual(failed, ["gig-12"]);
});
