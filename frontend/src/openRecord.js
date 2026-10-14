import { computed, onScopeDispose, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { confirmDiscardDraft } from "./draft.js";

// The record open in a screen's panel or dialog lives in the address under `key`, so a row can be a link opened
// in a new tab, a reload keeps the record open and Back closes it. A record being created has no name yet, so it
// stays out of the address.
export function useOpenRecord(key, { toQuery = (name) => name, fromQuery = (value) => value } = {}) {
	const route = useRoute();
	const router = useRouter();
	const addressedName = useAddressedName(route, key, fromQuery);
	const isCreating = ref(false);
	// Kept once the address lets go of it, so a closing dialog does not turn into a blank new one on its way out.
	const name = ref(addressedName.value);
	// Back only closes a record this page opened over the bare list: after a reload, the list's entry belongs to the
	// page before, and going back to it would load the whole app again.
	let wasOpenedHere = false;
	let isClosing = false;
	watch(addressedName, (addressed, previous) => {
		if (!addressed) return;
		name.value = addressed;
		isCreating.value = false;
		wasOpenedHere ||= !previous;
	});

	// Moving from one open record to the next replaces it, so Back and Close both return to the list.
	const routeTo = (recordName) => ({
		query: { ...route.query, [key]: toQuery(recordName) },
		replace: Boolean(addressedName.value),
	});

	function create() {
		name.value = null;
		isCreating.value = true;
	}

	function close() {
		isCreating.value = false;
		if (!addressedName.value || isClosing) return;
		isClosing = true;
		const query = { ...route.query, [key]: undefined };
		if (wasOpenedHere && isPreviousEntry(router, query)) router.back();
		else router.replace({ query });
	}

	const isOpen = computed(() => isCreating.value || Boolean(addressedName.value));
	// Another record, or Back, unmounts the open one's email thread. Close has asked already, and leaving the screen
	// is main.js's to ask about.
	const stopGuard = router.beforeEach((to, from) => {
		const toName = firstValue(to.query[key]);
		const isSwitching = to.path === from.path && toName !== firstValue(from.query[key]);
		const isClose = isClosing && !toName;
		return !isSwitching || !isOpen.value || isClose || confirmDiscardDraft();
	});
	// A close that another navigation overtakes ends too, or Close would never work again.
	const stopClosing = router.afterEach(() => (isClosing = false));
	onScopeDispose(() => {
		stopGuard();
		stopClosing();
	});

	const open = (recordName) => router.push(routeTo(recordName));
	return { name, isOpen, routeTo, open, create, close };
}

function useAddressedName(route, key, fromQuery) {
	const screen = route.name;
	return computed(() => {
		const value = route.name === screen && firstValue(route.query[key]);
		return value ? fromQuery(value) : null;
	});
}

// A key repeated by a hand-edited address reads as its first value.
const firstValue = (queryValue) => [queryValue].flat()[0];

// Going back to the list closes the record as Back does, where replacing the address would leave an entry behind
// that opens it again.
function isPreviousEntry(router, query) {
	return router.options.history.state?.back === router.resolve({ query }).fullPath;
}
