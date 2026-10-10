<script setup>
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { CommandPalette, useCall } from "frappe-ui";
import SearchResultItem from "./SearchResultItem.vue";
import { onShortcut } from "../keyboard";
import { resultRoute, searchGroups } from "../search";

const router = useRouter();
const isOpen = ref(false);
const query = ref("");
const results = ref([]);

// CommandPalette fires on every keystroke; a short debounce keeps the endpoint from seeing each letter.
const SEARCH_DEBOUNCE_MS = 200;
const search = useCall({
	url: "/api/v2/method/roadie.api.search",
	immediate: false,
	onSuccess: (groups) => (results.value = groups || []),
});

let pending;
watch(query, (value) => {
	clearTimeout(pending);
	if (!value.trim()) {
		results.value = [];
		return;
	}
	pending = setTimeout(() => search.submit({ query: value }), SEARCH_DEBOUNCE_MS);
});

const groups = computed(() =>
	searchGroups(query.value, results.value).map((group) => ({ ...group, component: SearchResultItem }))
);

onShortcut({ key: "k", ctrl: true }, () => open());

function open() {
	isOpen.value = true;
}

function select(item) {
	isOpen.value = false;
	router.push(resultRoute(item));
}

defineExpose({ open });
</script>

<template>
	<CommandPalette v-model:show="isOpen" v-model:search-query="query" :groups="groups" @select="select" />
</template>
