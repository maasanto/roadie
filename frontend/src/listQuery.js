import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { filtersFromQuery, filtersToQuery, sortFromQuery, sortToQuery } from "./listFilters.js";

// Filters and sort live in the address, so a reload, a shared link or the back button brings the same list back.
// Each screen's last ones are also kept for the session, so a list left for another screen comes back as the
// member left it whichever link opens it: the sidebar, a notification or the search palette.
const lastQueries = {};
const remember = (screen, { filters, sort }) => (lastQueries[screen] = { filters, sort });

export function restoreLastQuery(to) {
	const last = lastQueries[to.name];
	if (to.query.filters || to.query.sort || !(last?.filters || last?.sort)) return;
	return { path: to.path, query: { ...to.query, ...last }, hash: to.hash };
}

export function keepListQueries(router) {
	router.beforeEach(restoreLastQuery);
	router.afterEach((to, from, failure) => failure || remember(to.name, to.query));
}

export function useListQuery(meta, filterFields, sortFields) {
	const route = useRoute();
	const router = useRouter();

	// Remembered before the address changes, or clearing the last filter would bring it straight back.
	function replaceQuery(change) {
		const query = { ...route.query, ...change };
		remember(route.name, query);
		router.replace({ query });
	}

	const filters = computed({
		get: () => filtersFromQuery(route.query.filters, filterFields.value),
		set: (value) => replaceQuery({ filters: filtersToQuery(value) }),
	});
	const sort = computed({
		get: () => sortFromQuery(route.query.sort, sortFields.value),
		set: (value) => replaceQuery({ sort: sortToQuery(value) }),
	});
	// The address's filters and sort are read through the meta. A first load sent before it would be abandoned for
	// the filtered one, and the abort would linger on screen as an error.
	const isReady = computed(() =>
		Boolean(meta.data || meta.error || !(route.query.filters || route.query.sort))
	);
	return { filters, sort, isReady };
}
