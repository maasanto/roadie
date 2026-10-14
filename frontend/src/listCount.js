import { computed, watch } from "vue";
import { useCall } from "frappe-ui";

const formatNumber = (number) => number.toLocaleString(window.lang);

// A list stops at its limit and only says that more remain, so past it the number that match is asked for
// separately, under the same filters. Below the limit the loaded rows are the count, and nothing is asked.
export function useListCount(list, doctype, filters) {
	const total = useCall({
		url: `/api/v2/doctype/${doctype}/count`,
		params: () => ({ filters: JSON.stringify(filters()) }),
		immediate: false,
	});
	// Once per load, not per row edit: a filter, a refresh or a save can each change the total.
	watch(
		() => list.loading,
		(isLoading) => !isLoading && list.hasNextPage && total.reload()
	);

	const isTruncated = computed(() => Boolean(list.data) && list.hasNextPage);
	// A total still being counted belongs to the previous filters, so it is not shown at all.
	const isCounted = computed(() => !total.loading && !total.error && Number.isInteger(total.data));

	const count = computed(() => {
		if (!isTruncated.value) return list.data && formatNumber(list.data.length);
		return isCounted.value ? formatNumber(total.data) : null;
	});
	const limitNotice = computed(() => {
		if (!isTruncated.value || total.loading) return null;
		const limit = formatNumber(list.limit);
		// Without a total the cut-off is still worth saying.
		return isCounted.value
			? __("Showing the first {0} of {1}. Narrow it with a filter.", [limit, formatNumber(total.data)])
			: __("Showing the first {0}. Narrow it with a filter.", [limit]);
	});
	return { count, limitNotice };
}
