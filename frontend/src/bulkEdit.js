// Frappe updates fewer than 20 documents and deletes up to 10 within the request, and queues more in the background,
// where the reload that follows could not see them land. Batches within those limits keep the work inside its request.
export const UPDATE_BATCH_SIZE = 19;
export const DELETE_BATCH_SIZE = 10;

// Resolves to the names the batches report as failed. A batch whose request fails counts as failed whole, and the
// rest still go: an update can safely be repeated, and a record already deleted drops out of the list on reload.
export async function runInBatches(names, batchSize, runBatch) {
	const failed = [];
	for (let start = 0; start < names.length; start += batchSize) {
		const batch = names.slice(start, start + batchSize);
		try {
			failed.push(...(await runBatch(batch)));
		} catch (error) {
			console.error(error);
			failed.push(...batch);
		}
	}
	return failed;
}

// What a control shows before anything is picked: a multiselect holds a list, a checkbox a boolean.
export const blankValue = (field) => ({ multiselect: [], checkbox: false, rating: 0 }[field.type] ?? "");
