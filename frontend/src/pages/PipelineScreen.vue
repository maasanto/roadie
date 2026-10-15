<script setup>
import { computed, inject, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
	Avatar,
	Badge,
	Button,
	Dropdown,
	ErrorMessage,
	ListHeader,
	ListRows,
	ListView,
	Skeleton,
	TabButtons,
	toast,
	useCall,
	useList,
} from "frappe-ui";
import BulkEditBar from "../components/BulkEditBar.vue";
import EmptyState from "../components/EmptyState.vue";
import GigCard from "../components/GigCard.vue";
import GigPanel from "../components/GigPanel.vue";
import ListColumnEditor from "../components/ListColumnEditor.vue";
import ListFilter from "../components/ListFilter.vue";
import ListSkeleton from "../components/ListSkeleton.vue";
import ListSort from "../components/ListSort.vue";
import QuickFilterBar from "../components/QuickFilterBar.vue";
import { confirmBooking } from "../availability";
import { burstConfetti } from "../celebrate";
import {
	daysUntil,
	feeLabelOf,
	formatDate,
	formatFee,
	isDeadlineClose,
	pipelineColumns,
	totalFee,
} from "../gig";
import { useDirectoryColumns } from "../directoryColumns";
import { useDirectoryQuickFilters } from "../directoryQuickFilters";
import { useGigControls } from "../gigControls";
import { columnFormat, fetchFields, formatCell, isNameColumn } from "../listColumns";
import { useListCount } from "../listCount";
import { orderBy, queryFilters, sortEmptyLast } from "../listFilters";
import { useListQuery } from "../listQuery";
import { useIsPhone } from "../media";
import { useMeta } from "../meta";
import { fieldsFromMeta } from "../metaFields";
import { useOpenRecord } from "../openRecord";
import { UNDO_WINDOW_MS } from "../undo";

const route = useRoute();
const router = useRouter();

// The kanban stays the pipeline's face; the list is asked for through the address, so a refresh or a shared
// link keeps it.
const views = [
	{ label: __("Kanban"), value: "kanban", iconLeft: "lucide-square-kanban" },
	{ label: __("List"), value: "list", iconLeft: "lucide-list" },
];
const view = computed({
	get: () => (route.query.view === "list" ? "list" : "kanban"),
	set: (value) =>
		router.replace({ query: { ...route.query, view: value === "list" ? "list" : undefined } }),
});

const { linkLists, members, controls } = useGigControls();

const meta = useMeta("Gig");
const filterFields = computed(() =>
	fieldsFromMeta(meta.data?.fields ?? [], controls.value).filter((field) => !field.hidden)
);
// The kanban's columns are the statuses, so a status quick filter there would empty all but one of them.
const quickFilterFields = computed(() =>
	view.value === "kanban"
		? filterFields.value.filter((field) => field.fieldname !== "status")
		: filterFields.value
);
// A link sorts by its generated id, a page of notes by its first word and a status by its English name rather
// than its stage: none of them orders anything. The kanban is the view by stage.
const sortFields = computed(() => [
	...filterFields.value.filter(
		(field) => !["textarea", "combobox"].includes(field.type) && field.fieldname !== "status"
	),
	{ fieldname: "modified", label: __("Last modified") },
	{ fieldname: "creation", label: __("Created") },
]);

const { filters, sort, isReady } = useListQuery(meta, filterFields, sortFields);
const activeFilters = computed(() => queryFilters(filters.value, filterFields.value));
const isFiltered = computed(() => Object.keys(activeFilters.value).length > 0);

const isCustomisingQuickFilters = ref(false);
const { loaded: quickFiltersLoaded } = useDirectoryQuickFilters("Gig");
const { columns: listLayout, settled: listLayoutSettled } = useDirectoryColumns("Gig");
// The list's columns change the request, so asking before they are known would abandon the first load.
const canFetch = computed(() => isReady.value && listLayoutSettled.value);

// What the cards read, whichever columns the list shows.
const cardFields = [
	"title",
	"status",
	"gig_owner",
	"gig_date",
	"festival",
	"venue",
	"promoter",
	"application_opens",
	"application_closes",
	// The server leaves it out for a member below its permission level.
	"fee",
].map((fieldname) => ({ fieldname }));

// ponytail: the whole pipeline in one unpaged fetch, page per column if a band ever tracks hundreds of gigs
const gigs = useList({
	// A ref, which the fetch reads as it changes.
	immediate: canFetch.value,
	refetch: canFetch,
	doctype: "Gig",
	fields: () => fetchFields([...cardFields, ...listLayout.value]),
	filters: () => activeFilters.value,
	orderBy: () => (sort.value ? orderBy(sort.value) : "modified desc"),
	transform: (rows) => (sort.value ? sortEmptyLast(rows, sort.value.fieldname) : rows),
	limit: 500,
});
const { count, limitNotice } = useListCount(gigs, "Gig", () => activeFilters.value);

const titleOf = (doctype, name) => linkLists[doctype].data?.find((row) => row.name === name)?.title;
const linkedTitles = (gig) =>
	[
		titleOf("Festival", gig.festival),
		titleOf("Venue", gig.venue),
		titleOf("Promoter", gig.promoter),
	].filter(Boolean);
const ownerOf = (gig) => members.data?.find((member) => member.name === gig.gig_owner);

// Only a band with no gig at all gets the onboarding, and it is decided when a response lands: a cleared filter
// keeps the empty filtered rows until the refetch returns, and the toolbar has to stay put under the pointer.
const hasNoGigs = ref(false);
watch(
	() => gigs.data,
	(data) => (hasNoGigs.value = data?.length === 0 && !isFiltered.value)
);
// Until the first answer, including while the board waits for the meta before asking at all.
const isFirstLoad = computed(() => !gigs.data && !gigs.error);
// A retry hides the last failure while it runs, as the directory does, rather than leaving it over the board.
const loadError = computed(() => (gigs.loading ? null : gigs.error));

const feeLabel = computed(() => feeLabelOf(meta.data?.fields ?? []));

const columns = computed(() =>
	pipelineColumns.map((column) => {
		const columnGigs = (gigs.data || []).filter((gig) => column.statuses.includes(gig.status));
		const fee = feeLabel.value ? totalFee(columnGigs) : 0;
		return { ...column, gigs: columnGigs, fee: fee ? formatFee(fee) : null };
	})
);
// A card has no room for every date, so the opening date shows only while the board is ordered by it.
const showsOpeningDate = computed(() => sort.value?.fieldname === "application_opens");

const isPhone = useIsPhone();
// The ListView grid is as wide as its content, so every column but the title gets a fixed width, or the longest
// label would set them all. The deadline's header is the longest one, "Clôture des candidatures" in French.
const listColumnWidths = { status: "9rem", gig_date: "7rem", application_closes: "10rem" };
const listColumns = computed(() =>
	listLayout.value.slice(0, isPhone.value ? 2 : undefined).map((column) => ({
		key: column.fieldname,
		label: __(column.label),
		width: isNameColumn(column) ? undefined : listColumnWidths[column.fieldname] ?? "8rem",
		format: columnFormat(column, filterFields.value),
	}))
);
const {
	name: openedName,
	isOpen: isPanelOpen,
	routeTo: gigRoute,
	open: openGig,
	create: createGig,
	close: closeGig,
} = useOpenRecord("gig");
const gigPanel = ref(null);
const activity = useCall({ url: "/api/v2/method/roadie.api.get_gig_activity" });
// A task, comment or file added in the panel doesn't reach the board, so the counts are read again once the member
// leaves a gig, by Close, Back or another card.
watch([isPanelOpen, openedName], (_, [wasOpen]) => {
	if (wasOpen) activity.reload();
});

// An answer given in the strip above the board, or a request that reached it, changes a card's availability.
const pendingAvailability = inject("pendingAvailability", null);
watch(
	() => pendingAvailability?.data?.map((gig) => gig.name).join(),
	(_, previous) => previous !== undefined && activity.reload()
);

function refresh() {
	gigs.reload();
	activity.reload();
}

const listOptions = {
	getRowRoute: (gig) => gigRoute(gig.name),
	rowHeight: 44,
};
const linkedDoctypes = {
	festival: "Festival",
	festival_edition: "Festival Edition",
	venue: "Venue",
	promoter: "Promoter",
};

const draggedGig = ref(null);
const dropColumn = ref(null);

const celebrations = {
	Booked: (title) => __("{0} is booked. Time to rehearse!", [title]),
	Played: (title) => __("{0} is in the books. What a night!", [title]),
};

async function setStatus(gig, status) {
	const previousStatus = gig.status;
	gig.status = status;
	await gigs.setValue.submit({ name: gig.name, status });
	if (!gigs.setValue.error) return true;
	gig.status = previousStatus;
	return false;
}

async function assignOwner(gig, memberName) {
	if (memberName === gig.gig_owner) return;
	const previousOwner = gig.gig_owner;
	gig.gig_owner = memberName;
	await gigs.setValue.submit({ name: gig.name, gig_owner: memberName });
	if (gigs.setValue.error) {
		gig.gig_owner = previousOwner;
		return;
	}
	toast.success(__("Assigned to {0}", [ownerOf(gig).full_name]));
}

function dropGig(column) {
	const gig = draggedGig.value;
	draggedGig.value = dropColumn.value = null;
	if (!gig || column.statuses.includes(gig.status)) return;
	moveGig(gig, column.statuses[0]);
}

const listSettled = () =>
	new Promise((resolve) => {
		const stop = watch(
			() => gigs.loading,
			(isLoading) => {
				if (isLoading) return;
				stop();
				resolve();
			}
		);
	});

// A move renders the card anew in its new column, or back in its old one, so the focus its menu had is lost.
// The board has a copy per screen size: the visible one gets the focus back, unless the member has moved on.
function refocusCard(gig) {
	const card = [...document.querySelectorAll(`[data-gig="${CSS.escape(gig.name)}"]`)].find(
		(element) => element.getClientRects().length
	);
	if (!card || document.activeElement !== document.body) return card;
	card.focus({ preventScroll: true });
	// Following the card helps a keyboard member, but would pull a phone or mouse user away from where they were.
	if (card.matches(":focus-visible")) card.scrollIntoView({ block: "nearest" });
	return card;
}

function toastMove(gig, status, previousStatus) {
	const undoable = {
		action: { label: __("Undo"), onClick: () => setStatus(gig, previousStatus) },
		duration: UNDO_WINDOW_MS,
	};
	if (celebrations[status]) toast.success(celebrations[status](gig.title), undoable);
	else toast(__("Moved {0} to {1}", [gig.title, __(status)]), undoable);
}

async function moveGig(gig, status) {
	if (
		status === "Booked" &&
		!confirmBooking(gig.title, activity.data?.[gig.name]?.availability, members.data)
	)
		return;
	const previousStatus = gig.status;
	const isSaved = await setStatus(gig, status);
	if (isSaved) toastMove(gig, status, previousStatus);
	// A save refetches the list, which moves the card again and drops the focus a second time.
	if (gigs.loading) await listSettled();
	const card = refocusCard(gig);
	if (card && isSaved && celebrations[status]) burstConfetti(card);
}
</script>

<template>
	<div class="p-6">
		<div class="flex items-center justify-between">
			<h1 class="text-2xl-semibold">
				{{ __("Gigs") }}
				<span v-if="!hasNoGigs && !loadError && count" class="ms-1 text-ink-gray-5">{{ count }}</span>
			</h1>
			<Button
				v-if="!hasNoGigs"
				variant="solid"
				icon-left="lucide-plus"
				:label="__('New gig')"
				@click="createGig()"
			/>
		</div>
		<div v-if="!hasNoGigs" class="mt-4 flex flex-wrap items-center gap-2">
			<TabButtons v-model="view" :options="views" />
			<!-- Keyed by view so that leaving the list ends a customisation, whose chips the kanban's fields would hide. -->
			<QuickFilterBar
				:key="view"
				v-model="filters"
				v-model:customising="isCustomisingQuickFilters"
				doctype="Gig"
				:fields="quickFilterFields"
			/>
			<div v-if="!isCustomisingQuickFilters" class="ms-auto flex flex-wrap items-center gap-2">
				<Button
					icon="lucide-refresh-ccw"
					:label="__('Refresh')"
					:loading="gigs.loading"
					@click="refresh"
				/>
				<ListFilter v-model="filters" :fields="filterFields" />
				<ListSort v-model="sort" :fields="sortFields" />
				<ListColumnEditor v-if="view === 'list'" doctype="Gig" :controls="controls" />
				<Dropdown
					v-if="view === 'list'"
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
		<ListSkeleton v-if="isFirstLoad && view === 'list'" class="mt-4" />
		<div
			v-else-if="isFirstLoad"
			class="mt-4 flex gap-3 overflow-hidden"
			aria-busy="true"
			:aria-label="__('Loading')"
		>
			<div
				v-for="column in 5"
				:key="column"
				class="min-w-52 flex-1 space-y-2 rounded-6 bg-surface-gray-1 p-2"
			>
				<Skeleton class="mb-3 h-4 w-24 rounded" />
				<Skeleton v-for="card in (column % 3) + 1" :key="card" class="h-20 rounded-4" />
			</div>
		</div>
		<ErrorMessage v-else-if="loadError" class="mt-4" :message="loadError" />
		<EmptyState
			v-else-if="hasNoGigs"
			class="mt-4"
			icon="lucide-guitar"
			:title="__('No gigs yet')"
			:description="
				__(
					'Add the first gig you are chasing, even if it is only an idea. Drag it from column to column as things move.'
				)
			"
		>
			<Button variant="solid" icon-left="lucide-plus" :label="__('New gig')" @click="createGig()" />
		</EmptyState>
		<EmptyState
			v-else-if="!gigs.data?.length"
			class="mt-4"
			icon="lucide-search-x"
			:title="__('No gigs match these filters')"
			:description="__('Loosen a filter, or add the gig.')"
		>
			<Button icon-left="lucide-x" :label="__('Clear all filters')" @click="filters = []" />
		</EmptyState>
		<template v-else>
			<ErrorMessage class="mt-4" :message="gigs.setValue.error" />
			<ErrorMessage v-if="view === 'kanban'" class="mt-4" :message="activity.error" />
			<p v-if="limitNotice" class="mt-4 text-p-sm text-ink-gray-6">{{ limitNotice }}</p>
			<ListView
				v-if="view === 'list'"
				class="mt-4"
				:columns="listColumns"
				:rows="gigs.data"
				row-key="name"
				:options="listOptions"
			>
				<ListHeader />
				<ListRows />
				<BulkEditBar
					doctype="Gig"
					:fields="filterFields"
					@updated="gigs.reload()"
					@deleted="(names) => names.includes(gigPanel?.entryName) && closeGig()"
				/>
				<template #cell="{ column, row }">
					<Badge v-if="column.key === 'status'" :label="__(row.status)" />
					<span v-else-if="column.key === 'fee'" class="truncate">
						{{ row.fee ? formatFee(row.fee) : "" }}
					</span>
					<span
						v-else-if="column.key === 'application_closes' && row.application_closes"
						class="truncate"
						:class="
							daysUntil(row.application_closes) >= 0 && isDeadlineClose(row.application_closes)
								? 'text-ink-red-7'
								: ''
						"
					>
						{{ formatDate(row.application_closes) }}
					</span>
					<!-- A cell slot replaces the ListView's own tooltip, so a truncated name carries its own. -->
					<span
						v-else-if="linkedDoctypes[column.key]"
						class="truncate"
						:title="titleOf(linkedDoctypes[column.key], row[column.key])"
					>
						{{ titleOf(linkedDoctypes[column.key], row[column.key]) }}
					</span>
					<span
						v-else-if="column.key === 'gig_owner' && ownerOf(row)"
						class="flex min-w-0 items-center gap-2"
					>
						<Avatar :label="ownerOf(row).full_name" :image="ownerOf(row).user_image" size="sm" />
						<span class="truncate" :title="ownerOf(row).full_name">{{
							ownerOf(row).full_name
						}}</span>
					</span>
					<span v-else-if="column.key === 'title'" class="truncate text-ink-gray-8">{{
						row.title
					}}</span>
					<!-- An owner who is no longer a member shows no one, as on the card, rather than a login. -->
					<span
						v-else-if="column.key !== 'gig_owner'"
						class="truncate"
						:title="formatCell({ fieldname: column.key, format: column.format }, row)"
					>
						{{ formatCell({ fieldname: column.key, format: column.format }, row) }}
					</span>
				</template>
			</ListView>
			<div v-else class="mt-4 hidden gap-3 overflow-x-auto pb-2 md:flex">
				<section
					v-for="column in columns"
					:key="column.label"
					class="flex min-w-52 flex-1 flex-col rounded-6 bg-surface-gray-1 p-2"
					:class="dropColumn === column.label ? 'ring-2 ring-outline-gray-3' : ''"
					@dragover.prevent="dropColumn = column.label"
					@drop.prevent="dropGig(column)"
				>
					<h2
						class="flex items-center justify-between gap-2 px-1 pb-2 text-sm-medium text-ink-gray-7"
					>
						{{ column.label }}
						<span class="flex shrink-0 gap-2 text-ink-gray-5">
							<span v-if="column.fee" :title="feeLabel">{{ column.fee }}</span>
							{{ column.gigs.length }}
						</span>
					</h2>
					<div class="min-h-24 flex-1 space-y-2">
						<GigCard
							v-for="gig in column.gigs"
							:key="gig.name"
							:gig="gig"
							:linked-titles="linkedTitles(gig)"
							:owner="ownerOf(gig)"
							:members="members.data || []"
							:shows-opening-date="showsOpeningDate"
							:fee-label="feeLabel"
							:activity="activity.data?.[gig.name]"
							class="cursor-grab"
							draggable="true"
							@dragstart="draggedGig = gig"
							@dragend="draggedGig = dropColumn = null"
							@click="openGig(gig.name)"
							@assign="assignOwner(gig, $event)"
							@move="moveGig(gig, $event)"
						/>
					</div>
				</section>
			</div>
			<div v-if="view === 'kanban'" class="mt-4 space-y-6 md:hidden">
				<section v-for="column in columns.filter((column) => column.gigs.length)" :key="column.label">
					<h2 class="pb-2 text-sm-medium text-ink-gray-7">
						{{ column.label }} · {{ column.gigs.length
						}}<template v-if="column.fee"> · {{ column.fee }}</template>
					</h2>
					<div class="space-y-2">
						<GigCard
							v-for="gig in column.gigs"
							:key="gig.name"
							:gig="gig"
							:linked-titles="linkedTitles(gig)"
							:owner="ownerOf(gig)"
							:members="members.data || []"
							:shows-opening-date="showsOpeningDate"
							:fee-label="feeLabel"
							:activity="activity.data?.[gig.name]"
							@click="openGig(gig.name)"
							@assign="assignOwner(gig, $event)"
							@move="moveGig(gig, $event)"
						/>
					</div>
				</section>
			</div>
		</template>
		<GigPanel
			v-if="isPanelOpen"
			ref="gigPanel"
			:name="openedName"
			:controls="controls"
			:on-mail-seen="() => activity.reload()"
			@close="closeGig()"
			@saved="gigs.reload()"
		/>
	</div>
</template>
