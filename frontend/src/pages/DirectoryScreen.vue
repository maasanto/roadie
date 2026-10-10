<script setup>
import { computed, ref } from "vue";
import { Badge, Dropdown, ErrorMessage, TabButtons, TextInput, useList } from "frappe-ui";
import CommentThread from "../components/CommentThread.vue";
import EmailThread from "../components/EmailThread.vue";
import EmptyState from "../components/EmptyState.vue";
import EntryContacts from "../components/EntryContacts.vue";
import EntryDialog from "../components/EntryDialog.vue";
import ListSkeleton from "../components/ListSkeleton.vue";
import { directoryTypes } from "../directory";
import { onKey } from "../keyboard";

// ponytail: one unpaged fetch per type, page server-side if the directory outgrows a few hundred entries
const lists = Object.fromEntries(
	directoryTypes.map(({ doctype }) => [
		doctype,
		useList({ doctype, fields: ["name", "title", "city"], orderBy: "title asc", limit: 500 }),
	])
);

const activeType = ref("all");
const query = ref("");
const searchInput = ref(null);
onKey("/", () => searchInput.value?.el.focus());
const typeTabs = [
	{ value: "all", label: __("All") },
	...directoryTypes.map((type) => ({ value: type.doctype, label: type.plural })),
];

const isLoading = computed(() => Object.values(lists).some((list) => list.loading && !list.data));
const loadError = computed(() => Object.values(lists).find((list) => list.error)?.error);

const entries = computed(() => {
	const needle = query.value.trim().toLowerCase();
	return directoryTypes
		.filter(({ doctype }) => activeType.value === "all" || activeType.value === doctype)
		.flatMap(({ doctype }) => (lists[doctype].data || []).map((row) => ({ ...row, doctype })))
		.filter((entry) => !needle || `${entry.title} ${entry.city || ""}`.toLowerCase().includes(needle))
		.sort((a, b) => a.title.localeCompare(b.title));
});

const isDialogOpen = ref(false);
const editing = ref({ doctype: "Festival", name: null });

function openEntry(doctype, name = null) {
	editing.value = { doctype, name };
	isDialogOpen.value = true;
}

const newOptions = directoryTypes.map(({ doctype }) => ({
	label: __(doctype),
	onClick: () => openEntry(doctype),
}));
</script>

<template>
	<div class="p-6">
		<div class="flex items-center justify-between">
			<h1 class="text-2xl-semibold">{{ __("Directory") }}</h1>
			<Dropdown
				:options="newOptions"
				align="end"
				:button="{ label: __('New'), iconLeft: 'lucide-plus', variant: 'solid' }"
			/>
		</div>
		<div class="mt-4 flex flex-wrap items-center gap-3">
			<div class="max-w-full overflow-x-auto">
				<TabButtons v-model="activeType" :options="typeTabs" />
			</div>
			<TextInput
				ref="searchInput"
				v-model="query"
				type="search"
				:placeholder="__('Search by name or city')"
				class="w-full sm:w-64"
			>
				<template #suffix>
					<kbd
						class="hidden rounded border px-1 text-xs text-ink-gray-5 md:inline"
						:title="__('Press / to search')"
						>/</kbd
					>
				</template>
				<template #prefix
					><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true"
				/></template>
			</TextInput>
		</div>
		<ListSkeleton v-if="isLoading" class="mt-4" />
		<ErrorMessage v-else-if="loadError" class="mt-4" :message="loadError" />
		<EmptyState
			v-else-if="!entries.length && query.trim()"
			class="mt-4"
			icon="lucide-search-x"
			:title="__('No match for “{0}”', [query.trim()])"
			:description="__('Search looks at names and cities. Try a shorter word, or add the entry.')"
		/>
		<EmptyState
			v-else-if="!entries.length"
			class="mt-4"
			icon="lucide-book-user"
			:title="__('Your address book starts here')"
			:description="
				__(
					'Add the festivals, venues, promoters and bands you deal with, and the people to talk to at each.'
				)
			"
		>
			<Dropdown
				:options="newOptions"
				:button="{ label: __('Add the first one'), iconLeft: 'lucide-plus' }"
			/>
		</EmptyState>
		<ul v-else class="mt-4 divide-y divide-outline-gray-1 rounded-6 border">
			<li v-for="entry in entries" :key="`${entry.doctype}:${entry.name}`">
				<button
					class="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-surface-gray-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-outline-gray-3"
					@click="openEntry(entry.doctype, entry.name)"
				>
					<span class="min-w-0 flex-1 truncate text-base">{{ entry.title }}</span>
					<span class="hidden w-40 truncate text-sm text-ink-gray-5 sm:block">{{
						entry.city
					}}</span>
					<Badge :label="__(entry.doctype)" class="w-20 justify-center" />
				</button>
			</li>
		</ul>
		<EntryDialog
			v-model:open="isDialogOpen"
			:doctype="editing.doctype"
			:name="editing.name"
			:fields="directoryTypes.find((type) => type.doctype === editing.doctype).fields"
			@saved="lists[editing.doctype].reload()"
		>
			<template #default="{ entryName }">
				<EntryContacts :doctype="editing.doctype" :name="entryName" />
				<CommentThread :doctype="editing.doctype" :name="entryName" />
				<EmailThread :doctype="editing.doctype" :name="entryName" />
			</template>
		</EntryDialog>
	</div>
</template>
