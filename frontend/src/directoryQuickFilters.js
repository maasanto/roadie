import { computed, ref } from "vue";
import { call, toast, useCall } from "frappe-ui";

// Name and city are what members look an entry up by, so a type nobody customised offers those two.
const DEFAULT_QUICK_FILTERS = ["title", "city"];

// One setting for the whole site, read once for all four screens, like the columns.
const setting = useCall({ url: "/api/v2/method/roadie.api.get_directory_quick_filters" });

export const useDirectoryQuickFilters = (doctype) => {
	// The setting is a Code field anyone can hand-edit in Desk, so anything but a list reads as unset.
	const fieldnames = computed(() => {
		const saved = setting.data?.[doctype];
		return Array.isArray(saved) ? saved : DEFAULT_QUICK_FILTERS;
	});
	// Whether the setting is known: customising before it arrives would save the defaults over the real list.
	const loaded = computed(() => setting.isFinished === true && !setting.error);
	const saving = ref(false);

	async function save(next) {
		saving.value = true;
		try {
			await call("roadie.api.set_directory_quick_filters", {
				doctype,
				fieldnames: JSON.stringify(next),
			});
			await setting.reload();
			toast.success(__("Quick filters saved"));
			return true;
		} catch (error) {
			toast.error(error.messages?.join("\n") || error.message);
			return false;
		} finally {
			saving.value = false;
		}
	}

	return { fieldnames, loaded, saving, save };
};
