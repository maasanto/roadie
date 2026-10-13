// Frappe updates fewer than 20 documents within the request and queues more in the background, where the reload
// that follows could not see them land. Batches below that keep every update inside its request.
const BATCH_SIZE = 19;

// Resolves to the names that could not be updated. A batch whose request fails counts as failed whole, and the
// rest still go: setting a field to a value can safely be repeated on whichever of them did save.
export async function updateInBatches(names, updateBatch) {
	const failed = [];
	for (let start = 0; start < names.length; start += BATCH_SIZE) {
		const batch = names.slice(start, start + BATCH_SIZE);
		try {
			failed.push(...(await updateBatch(batch)));
		} catch {
			failed.push(...batch);
		}
	}
	return failed;
}

// What a control shows before anything is picked: a multiselect holds a list, a checkbox a boolean.
export const blankValue = (field) => ({ multiselect: [], checkbox: false, rating: 0 }[field.type] ?? "");
