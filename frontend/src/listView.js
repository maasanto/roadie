import { computed, effectScope, ref } from "vue";
import { call, toast, useList } from "frappe-ui";
import { columnsFor } from "./listColumns.js";

// A member's saved layout, one row per DocType. Fetched once per session and shared, so the screen and its
// column editor read the same row instead of two copies that drift apart.
const sessionScope = effectScope(true);
const views = {};

export const useListView = (doctype) =>
	(views[doctype] ??= sessionScope.run(() => {
		const list = useList({
			doctype: "Roadie List View",
			fields: ["name", "columns"],
			// Scoped to this member rather than left to the DocType's permissions: a member who also holds a
			// role with plain read (System Manager) would otherwise load the newest layout of whoever has one.
			filters: { dt: doctype, owner: window.user },
			orderBy: "modified desc",
			limit: 1,
		});

		const row = computed(() => list.data?.[0]);
		// A site that has not run migrate has no such DocType, let alone a row: the type's defaults stand in.
		const columns = computed(() => columnsFor(doctype, row.value?.columns));
		// Whether the layout question is settled, so a list whose fields follow from those columns asks once
		// instead of abandoning a first request for a second. A failed fetch is settled too: the type's
		// defaults stand in and the screen should not wait on them.
		const ready = computed(() => Boolean(list.error) || list.isFinished === true);
		// Whether the saved layout is actually known. The column editor waits for this rather than `ready`:
		// `ready` is true after a failed fetch, and an edit on top of one would save the defaults over a
		// layout that is really there.
		const loaded = computed(() => list.isFinished === true && !list.error);
		const saved = computed(() => Boolean(row.value));
		const saving = ref(false);

		async function apply(change, success) {
			saving.value = true;
			try {
				await change();
				await list.reload();
				toast.success(success);
				return true;
			} catch (error) {
				toast.error(error.messages?.join("\n") || error.message);
				return false;
			} finally {
				saving.value = false;
			}
		}

		// frappe.client.* enforces the DocType's permissions, which keep a member to their own rows.
		const save = (next) =>
			apply(
				() =>
					row.value
						? call("frappe.client.set_value", {
								doctype: "Roadie List View",
								name: row.value.name,
								fieldname: "columns",
								value: JSON.stringify(next),
						  })
						: call("frappe.client.insert", {
								doc: {
									doctype: "Roadie List View",
									dt: doctype,
									columns: JSON.stringify(next),
								},
						  }),
				__("Columns saved")
			);

		// Roadie's own method rather than frappe.client.delete: it clears every row this member has for the
		// DocType, not just the newest one.
		const reset = () =>
			apply(
				() => call("roadie.api.delete_list_view", { dt: doctype }),
				__("Back to the usual columns")
			);

		return { columns, ready, loaded, saved, saving, save, reset };
	}));
