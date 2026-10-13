import assert from "node:assert/strict";
import { test } from "node:test";
import { updateInBatches } from "./bulkEdit.js";

const gigNames = (count) => Array.from({ length: count }, (unused, index) => `gig-${index}`);

test("a large selection is sent in batches Frappe keeps in the request, and every failure is reported", async () => {
	const batchSizes = [];
	const failed = await updateInBatches(gigNames(45), async (batch) => {
		batchSizes.push(batch.length);
		return batch.filter((name) => name.endsWith("0"));
	});
	assert.deepEqual(batchSizes, [19, 19, 7]);
	assert.deepEqual(failed, ["gig-0", "gig-10", "gig-20", "gig-30", "gig-40"]);
});

test("a batch whose request fails counts as failed whole, and the batches after it still go", async () => {
	let batchCount = 0;
	const failed = await updateInBatches(gigNames(45), async (batch) => {
		if (++batchCount === 2) throw new Error("Gig gig-25 not found");
		return [];
	});
	assert.equal(batchCount, 3);
	assert.deepEqual(failed, gigNames(38).slice(19));
});
