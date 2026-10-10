<script setup>
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Button, ErrorMessage, Skeleton, TextInput, useList } from "frappe-ui";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from "frappe-ui/list";
import CommentThread from "../components/CommentThread.vue";
import EmailThread from "../components/EmailThread.vue";
import EmptyState from "../components/EmptyState.vue";
import EntryContacts from "../components/EntryContacts.vue";
import EntryDialog from "../components/EntryDialog.vue";
import ListColumnEditor from "../components/ListColumnEditor.vue";
import { directoryControls, directoryType } from "../directory";
import { fetchFields, formatCell } from "../listColumns";
import { useListView } from "../listView";
import { onKey } from "../keyboard";

const props = defineProps({ doctype: { type: String, required: true } });

const type = directoryType(props.doctype);
const { columns } = useListView(props.doctype);

// The search reads the name and the city whether or not those columns are on screen, so they are always fetched.
const SEARCH_FIELDS = ["title", "city"];

// ponytail: the whole type in one unpaged fetch, page server-side if a directory outgrows a few hundred entries
const entries = useList({
	doctype: props.doctype,
	fields: () => fetchFields(columns.value, SEARCH_FIELDS),
	orderBy: "title asc",
	limit: 500,
});

const isLoading = computed(() => entries.loading && !entries.data);
const placeholderRows = Array.from({ length: 4 }, (unused, index) => ({ name: `row-${index}` }));

const query = ref("");
const searchInput = ref(null);
onKey("/", () => searchInput.value?.el.focus());

const rows = computed(() => {
	const needle = query.value.trim().toLowerCase();
	return (entries.data || []).filter(
		(entry) => !needle || `${entry.title || ""} ${entry.city || ""}`.toLowerCase().includes(needle)
	);
});

// The name column takes the room and the rest are fixed, so a column means the same width on every row. A
// phone drops to the name and its first extra column, as a two-track feed.
const tracks = computed(() => columns.value.map((column, index) => (index === 0 ? "minmax(0,1fr)" : "8rem")));
const isExtra = (index) => index > 1;

const isDialogOpen = ref(false);
const editingName = ref(null);

function openEntry(name = null) {
	editingName.value = name;
	isDialogOpen.value = true;
}

// The search palette sends a record through the query, and it is cleared once the dialog has it.
const route = useRoute();
const router = useRouter();
watch(
	() => route.query.entry,
	(entry) => {
		if (!entry) return;
		const [doctype, name] = entry.split(":");
		if (doctype !== props.doctype) return;
		openEntry(name);
		router.replace({ query: { ...route.query, entry: undefined } });
	},
	{ immediate: true }
);
</script>

<template>
	<div class="p-6">
		<div class="flex flex-wrap items-center justify-between gap-3">
			<h1 class="text-2xl-semibold">{{ type.plural }}</h1>
			<div class="flex items-center gap-2">
				<ListColumnEditor :doctype="doctype" />
				<Button variant="solid" icon-left="lucide-plus" :label="__('New')" @click="openEntry()" />
			</div>
		</div>
		<div class="mt-4 flex flex-wrap items-center gap-3">
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
		<ErrorMessage v-if="entries.error" class="mt-4" :message="entries.error" />
		<EmptyState
			v-else-if="!isLoading && !rows.length && query.trim()"
			class="mt-4"
			icon="lucide-search-x"
			:title="__('No match for “{0}”', [query.trim()])"
			:description="__('Search looks at names and cities. Try a shorter word, or add the entry.')"
		/>
		<EmptyState
			v-else-if="!isLoading && !rows.length"
			class="mt-4"
			:icon="type.icon"
			:title="__('No {0} yet', [type.plural.toLowerCase()])"
			:description="
				__('Add the {0} you deal with, and the people to talk to at each.', [
					type.plural.toLowerCase(),
				])
			"
		>
			<Button icon-left="lucide-plus" :label="__('Add the first one')" @click="openEntry()" />
		</EmptyState>
		<List v-else :columns="tracks" class="mt-4 list-row-px-3 max-sm:[--list-columns:minmax(0,1fr)_auto]">
			<ListHeader class="max-sm:hidden">
				<ListHeaderCell
					v-for="(column, index) in columns"
					:key="column.fieldname"
					:class="isExtra(index) && 'max-sm:hidden'"
				>
					{{ __(column.label) }}
				</ListHeaderCell>
			</ListHeader>
			<ListRows v-if="isLoading" :items="placeholderRows" v-slot="{ item }">
				<ListRow>
					<ListCell
						v-for="(column, index) in columns"
						:key="column.fieldname"
						:class="isExtra(index) && 'max-sm:hidden'"
					>
						<Skeleton class="h-4 rounded" :class="index === 0 ? 'w-40' : 'w-16'" />
					</ListCell>
				</ListRow>
			</ListRows>
			<ListRows v-else :items="rows" v-slot="{ item }">
				<ListRow :on-click="() => openEntry(item.name)">
					<ListCell
						v-for="(column, index) in columns"
						:key="column.fieldname"
						class="text-base"
						:class="[isExtra(index) && 'max-sm:hidden', index > 0 && 'text-sm text-ink-gray-5']"
					>
						<span class="truncate">{{ formatCell(column, item) }}</span>
					</ListCell>
				</ListRow>
			</ListRows>
		</List>
		<EntryDialog
			v-model:open="isDialogOpen"
			:doctype="doctype"
			:name="editingName"
			:controls="directoryControls[doctype]"
			@saved="entries.reload()"
		>
			<template #default="{ entryName }">
				<EntryContacts :doctype="doctype" :name="entryName" />
				<CommentThread :doctype="doctype" :name="entryName" />
				<EmailThread :doctype="doctype" :name="entryName" />
			</template>
		</EntryDialog>
	</div>
</template>
