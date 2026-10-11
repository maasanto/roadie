<script setup>
import { computed, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Button, ErrorMessage, ListView, Rating, Skeleton, TextInput, call, toast, useList } from "frappe-ui";
import CommentThread from "../components/CommentThread.vue";
import EmailThread from "../components/EmailThread.vue";
import EmptyState from "../components/EmptyState.vue";
import EntryContacts from "../components/EntryContacts.vue";
import EntryDialog from "../components/EntryDialog.vue";
import ListColumnEditor from "../components/ListColumnEditor.vue";
import { useDirectoryColumns } from "../directoryColumns";
import { RATING_STARS, directoryControls, directoryType, toFraction, toStars } from "../directory";
import { fetchFields, formatCell } from "../listColumns";
import { onKey } from "../keyboard";

const props = defineProps({ doctype: { type: String, required: true } });

const type = directoryType(props.doctype);
const { columns, loaded } = useDirectoryColumns(props.doctype);

// The search reads the name and the city whether or not those columns are on screen, so they are always fetched.
const SEARCH_FIELDS = ["title", "city"];
const fields = computed(() => fetchFields(columns.value, SEARCH_FIELDS));

// ponytail: the whole type in one unpaged fetch, page server-side if a directory outgrows a few hundred entries
const entries = useList({
	doctype: props.doctype,
	fields: () => fields.value,
	orderBy: "relevance desc, title asc",
	limit: 500,
	immediate: false,
	// The fields change when the columns do, and each change would otherwise fire a request that the next one
	// abandons. Asking once per set of fields keeps the network and the console clean; a reorder changes
	// nothing, so it asks for nothing.
	refetch: false,
});

let fetched = null;
watch(
	[loaded, fields],
	() => {
		if (!loaded.value) return;
		const key = fields.value.join(",");
		if (key === fetched) return;
		fetched = key;
		entries.execute();
	},
	{ immediate: true }
);

const isLoading = computed(() => !loaded.value || (entries.loading && !entries.data));
const loadError = computed(() => (entries.loading || entries.data ? null : entries.error));

const query = ref("");
const searchInput = ref(null);
onKey("/", () => searchInput.value?.el.focus());

const rows = computed(() => {
	const needle = query.value.trim().toLowerCase();
	return (entries.data || []).filter(
		(entry) => !needle || `${entry.title || ""} ${entry.city || ""}`.toLowerCase().includes(needle)
	);
});

// The list owns its grid, so a phone drops the trailing columns rather than hiding their cells: two tracks are
// what a phone can read.
const phone = window.matchMedia("(max-width: 639px)");
const isPhone = ref(phone.matches);
const onPhoneChange = (event) => (isPhone.value = event.matches);
phone.addEventListener("change", onPhoneChange);
onUnmounted(() => phone.removeEventListener("change", onPhoneChange));

const listColumns = computed(() =>
	columns.value.slice(0, isPhone.value ? 2 : undefined).map((column) => ({
		key: column.fieldname,
		label: __(column.label),
		// The name takes the room; the rest share what is left. Stars keep the width of five, or a phone's
		// narrow track would clip the last ones.
		width: column.fieldname === "title" ? 3 : column.format === "rating" ? "6rem" : 1,
		format: column.format,
	}))
);

const placeholderRows = Array.from({ length: 4 }, (unused, index) => ({
	name: `row-${index}`,
	__skeleton: true,
}));

const listRows = computed(() => (isLoading.value ? placeholderRows : rows.value));

const options = computed(() => ({
	// A skeleton row is not an entry, so it opens nothing.
	onRowClick: (row) => !row.__skeleton && openEntry(row.name),
	selectable: false,
	showTooltip: true,
	rowHeight: 44,
	emptyState: {
		title: __("No {0} yet", [type.plural.toLowerCase()]),
		description: "",
	},
}));

// Rated in place and kept in place: the row only moves to its new rank on the next load, never from under the
// pointer that rated it.
async function rate(row, fieldname, stars) {
	const previous = row[fieldname];
	const value = toFraction(stars);
	entries.updateRow({ name: row.name, [fieldname]: value });
	try {
		await call("frappe.client.set_value", { doctype: props.doctype, name: row.name, fieldname, value });
	} catch (error) {
		entries.updateRow({ name: row.name, [fieldname]: previous });
		toast.error(error.messages?.join("\n") || error.message);
	}
}

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
				class="w-full sm:w-80"
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
		<ErrorMessage v-if="loadError" class="mt-4" :message="loadError" />
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
		<ListView
			v-else
			class="mt-4"
			:columns="listColumns"
			:rows="listRows"
			row-key="name"
			:options="options"
		>
			<template #cell="{ column, row }">
				<Skeleton
					v-if="row.__skeleton"
					class="h-4 rounded"
					:class="column.key === 'title' ? 'w-40' : 'w-16'"
				/>
				<!-- Rating a row is not opening it. -->
				<div v-else-if="column.format === 'rating'" class="inline-flex" @click.stop>
					<Rating
						:model-value="toStars(row[column.key])"
						:max="RATING_STARS"
						size="sm"
						@update:model-value="(stars) => rate(row, column.key, stars)"
					/>
				</div>
				<span v-else class="truncate">{{
					formatCell({ fieldname: column.key, format: column.format }, row)
				}}</span>
			</template>
		</ListView>
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
