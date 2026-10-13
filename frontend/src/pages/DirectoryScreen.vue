<script setup>
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
	Button,
	Dropdown,
	ErrorMessage,
	ListHeader,
	ListRows,
	ListView,
	Rating,
	Skeleton,
	call,
	toast,
	useList,
} from "frappe-ui";
import BulkEditBar from "../components/BulkEditBar.vue";
import CommentThread from "../components/CommentThread.vue";
import EmailThread from "../components/EmailThread.vue";
import EmptyState from "../components/EmptyState.vue";
import EntryContacts from "../components/EntryContacts.vue";
import EntryDialog from "../components/EntryDialog.vue";
import ListColumnEditor from "../components/ListColumnEditor.vue";
import ListFilter from "../components/ListFilter.vue";
import ListSort from "../components/ListSort.vue";
import QuickFilterBar from "../components/QuickFilterBar.vue";
import { useDirectoryColumns } from "../directoryColumns";
import { useDirectoryQuickFilters } from "../directoryQuickFilters";
import { RATING_STARS, directoryControls, directoryType, toFraction, toStars } from "../directory";
import { fetchFields, formatCell } from "../listColumns";
import { orderBy, queryFilters } from "../listFilters";
import { useMeta } from "../meta";
import { fieldsFromMeta } from "../metaFields";
import { onKey } from "../keyboard";
import { useIsPhone } from "../media";

const props = defineProps({ doctype: { type: String, required: true } });

const type = directoryType(props.doctype);
const { columns, loaded } = useDirectoryColumns(props.doctype);
const fields = computed(() => fetchFields(columns.value));

const meta = useMeta(props.doctype);
const filterFields = computed(() =>
	fieldsFromMeta(meta.data?.fields ?? [], directoryControls[props.doctype] ?? {}).filter(
		(field) => !field.hidden
	)
);
// Sorting on an address or a page of notes orders nothing anyone reads.
const sortFields = computed(() => [
	...filterFields.value.filter((field) => field.type !== "textarea"),
	{ fieldname: "modified", label: __("Last modified") },
	{ fieldname: "creation", label: __("Created") },
]);

// ponytail: in memory only, so a reload starts unfiltered; persist per member if the band asks for saved views
const filters = ref([]);
const sort = ref(null);
const activeFilters = computed(() => queryFilters(filters.value, filterFields.value));

// ponytail: the whole type in one unpaged fetch, page server-side if a directory outgrows a few hundred entries
const entries = useList({
	doctype: props.doctype,
	fields: () => fields.value,
	filters: () => activeFilters.value,
	orderBy: () => orderBy(sort.value),
	limit: 500,
	immediate: false,
	// Columns, filters and sort all change the request. Asking once the column setting is known keeps the first
	// load from being abandoned for the next; a column reorder leaves the request as it was, so it asks for
	// nothing. Text filters wait for the member to pause before they change it at all.
	refetch: false,
});

watch([loaded, () => entries.url], () => loaded.value && entries.execute(), { immediate: true });

const isLoading = computed(() => !loaded.value || (entries.loading && !entries.data));
// The previous rows stay in place when a refetch fails, so the error has to show over them, or the list would
// look filtered by conditions the server never applied.
const loadError = computed(() => (entries.loading ? null : entries.error));

const isCustomisingQuickFilters = ref(false);
const { loaded: quickFiltersLoaded } = useDirectoryQuickFilters(props.doctype);
const quickFilterBar = ref(null);
onKey("/", () => quickFilterBar.value?.querySelector("input")?.focus());

const rows = computed(() => entries.data || []);

const isPhone = useIsPhone();

const listColumns = computed(() =>
	// The list owns its grid, so a phone drops the trailing columns rather than hiding their cells: two tracks
	// are what a phone can read.
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
	// A skeleton row is not an entry, so it can be neither opened nor selected.
	onRowClick: (row) => !row.__skeleton && openEntry(row.name),
	selectable: !isLoading.value,
	showTooltip: true,
	rowHeight: 44,
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
			<Button variant="solid" icon-left="lucide-plus" :label="__('New')" @click="openEntry()" />
		</div>
		<div class="mt-4 flex flex-wrap items-center gap-2">
			<div ref="quickFilterBar" class="contents">
				<QuickFilterBar
					v-model="filters"
					v-model:customising="isCustomisingQuickFilters"
					:doctype="doctype"
					:fields="filterFields"
				/>
			</div>
			<div v-if="!isCustomisingQuickFilters" class="ms-auto flex flex-wrap items-center gap-2">
				<Button
					icon="lucide-refresh-ccw"
					:label="__('Refresh')"
					:loading="entries.loading"
					@click="entries.reload()"
				/>
				<ListFilter v-model="filters" :fields="filterFields" />
				<ListSort v-model="sort" :fields="sortFields" />
				<ListColumnEditor :doctype="doctype" />
				<Dropdown
					align="end"
					:options="[
						{
							label: __('Customise quick filters'),
							icon: 'lucide-sliders-horizontal',
							disabled: !quickFiltersLoaded,
							onClick: () => (isCustomisingQuickFilters = true),
						},
					]"
					:button="{ icon: 'lucide-ellipsis', label: __('More options') }"
				/>
			</div>
		</div>
		<ErrorMessage v-if="loadError" class="mt-4" :message="loadError" />
		<EmptyState
			v-else-if="!isLoading && !rows.length && Object.keys(activeFilters).length"
			class="mt-4"
			icon="lucide-search-x"
			:title="__('No {0} match these filters', [type.plural.toLowerCase()])"
			:description="__('Loosen a filter, or add the entry.')"
		>
			<Button icon-left="lucide-x" :label="__('Clear all filters')" @click="filters = []" />
		</EmptyState>
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
			<ListHeader />
			<ListRows />
			<BulkEditBar :doctype="doctype" :fields="filterFields" @updated="entries.reload()" />
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
