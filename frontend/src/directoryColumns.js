import { computed, ref } from "vue";
import { call, toast, useCall } from "frappe-ui";
import { columnsFor } from "./listColumns.js";

// The columns every directory list shows: one setting for the whole site, not a layout per member. One fetch
// serves all four screens, so a save on one screen is what the next one reads.
const setting = useCall({ url: "/api/v2/method/roadie.api.get_directory_columns" });

export const useDirectoryColumns = (doctype) => {
	const columns = computed(() => columnsFor(doctype, setting.data?.[doctype]));
	// Whether the setting is known. The editor waits on this rather than on the list, which is content to draw
	// the defaults: editing before it arrives would write over the columns that are really there.
	const loaded = computed(() => setting.isFinished === true && !setting.error);
	const saved = computed(() => Boolean(setting.data?.[doctype]?.length));
	const saving = ref(false);

	async function apply(change, success) {
		saving.value = true;
		try {
			await change();
			await setting.reload();
			toast.success(success);
			return true;
		} catch (error) {
			toast.error(error.messages?.join("\n") || error.message);
			return false;
		} finally {
			saving.value = false;
		}
	}

	const save = (next) =>
		apply(
			() => call("roadie.api.set_directory_columns", { doctype, columns: JSON.stringify(next) }),
			__("Columns saved")
		);

	const reset = () =>
		apply(
			() => call("roadie.api.set_directory_columns", { doctype, columns: "[]" }),
			__("Back to the usual columns")
		);

	return { columns, loaded, saved, saving, save, reset };
};
