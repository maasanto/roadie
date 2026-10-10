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
			filters: { dt: doctype },
			orderBy: "modified desc",
			limit: 1,
		});

		const row = computed(() => list.data?.[0]);
		// A site that has not run migrate has no such DocType, let alone a row: the type's defaults stand in.
		const columns = computed(() => columnsFor(doctype, row.value?.columns));
		// Whether the saved layout is known yet. A list whose fields follow from those columns must not ask
		// before this is true: its first request would only be abandoned for the second.
		const ready = computed(() => Boolean(list.error) || list.isFinished === true);
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

		const reset = () =>
			apply(
				() =>
					call("frappe.client.delete", {
						doctype: "Roadie List View",
						name: row.value.name,
					}),
				__("Back to the usual columns")
			);

		return { columns, ready, saved, saving, save, reset };
	}));
