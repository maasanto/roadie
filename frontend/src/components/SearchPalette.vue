<script setup>
import { computed, nextTick, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { Dialog, TextInput, useCall } from "frappe-ui";
import SearchResultItem from "./SearchResultItem.vue";
import { onShortcut } from "../keyboard";
import { resultRoute, searchGroups } from "../search";

const router = useRouter();
const isOpen = ref(false);
const query = ref("");
const results = ref([]);
const activeIndex = ref(0);
const input = ref(null);

// Matching lives on the server, so the palette asks for a fresh set rather than filtering what it has.
const SEARCH_DEBOUNCE_MS = 200;
const search = useCall({
	url: "/api/v2/method/roadie.api.search",
	immediate: false,
	onSuccess: (groups) => {
		results.value = groups || [];
		activeIndex.value = 0;
	},
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

const groups = computed(() => searchGroups(query.value, results.value));
// One flat list for the arrow keys, in the order the groups render.
const items = computed(() => groups.value.flatMap((group) => group.items));
const activeOptionId = computed(() => (items.value.length ? optionId(items.value[activeIndex.value]) : undefined));

function optionId(item) {
	return `roadie-search-option-${items.value.indexOf(item)}`;
}

onShortcut({ key: "k", ctrl: true }, open);

function open() {
	isOpen.value = true;
	nextTick(() => input.value?.el?.focus());
}

function select(item) {
	isOpen.value = false;
	router.push(resultRoute(item));
}

function onKeydown(event) {
	if (!items.value.length) return;
	if (event.key === "ArrowDown") activeIndex.value = (activeIndex.value + 1) % items.value.length;
	else if (event.key === "ArrowUp") activeIndex.value = (activeIndex.value - 1 + items.value.length) % items.value.length;
	else if (event.key === "Enter") return select(items.value[activeIndex.value]);
	else return;
	event.preventDefault();
}

function reset() {
	query.value = "";
	results.value = [];
	activeIndex.value = 0;
}

defineExpose({ open });
</script>

<template>
	<Dialog v-model:open="isOpen" bare size="2xl" position="top" @after-leave="reset">
		<div class="text-start" @keydown="onKeydown">
			<div class="border-b p-3">
				<TextInput
					ref="input"
					v-model="query"
					type="search"
					:placeholder="__('Search gigs, venues, promoters, bands and tasks')"
					:aria-activedescendant="activeOptionId"
					class="w-full"
				/>
			</div>
			<div v-if="items.length" role="listbox" :aria-label="__('Search results')" class="max-h-96 overflow-auto p-2">
				<div v-for="group in groups" :key="group.doctype" role="group" :aria-label="group.title">
					<p class="px-3 pb-1 pt-3 text-sm text-ink-gray-5" aria-hidden="true">{{ group.title }}</p>
					<button
						v-for="item in group.items"
						:id="optionId(item)"
						:key="`${item.doctype}:${item.name}`"
						type="button"
						role="option"
						:aria-selected="items[activeIndex] === item"
						class="w-full rounded focus-visible:outline-none"
						@click="select(item)"
						@mousemove="activeIndex = items.indexOf(item)"
					>
						<SearchResultItem :item="item" :active="items[activeIndex] === item" />
					</button>
				</div>
			</div>
			<p v-else-if="query.trim()" class="px-4 py-8 text-center text-sm text-ink-gray-5">
				{{ __("No match for “{0}”", [query.trim()]) }}
			</p>
		</div>
	</Dialog>
</template>
