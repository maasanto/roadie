<script setup>
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Button, ErrorMessage, Skeleton, toast, useList } from "frappe-ui";
import EmptyState from "../components/EmptyState.vue";
import GigCard from "../components/GigCard.vue";
import GigPanel from "../components/GigPanel.vue";
import { burstConfetti } from "../celebrate";
import { pipelineColumns } from "../gig";
import { useGigControls } from "../gigControls";
import { UNDO_WINDOW_MS } from "../undo";

// ponytail: the whole pipeline in one unpaged fetch, page per column if a band ever tracks hundreds of gigs
const gigs = useList({
	doctype: "Gig",
	fields: [
		"name",
		"title",
		"status",
		"gig_owner",
		"gig_date",
		"festival",
		"venue",
		"promoter",
		"application_closes",
	],
	orderBy: "modified desc",
	limit: 500,
});
const { linkLists, members, controls } = useGigControls();

const titleOf = (doctype, name) => linkLists[doctype].data?.find((row) => row.name === name)?.title;
const linkedTitles = (gig) =>
	[
		titleOf("Festival", gig.festival),
		titleOf("Venue", gig.venue),
		titleOf("Promoter", gig.promoter),
	].filter(Boolean);
const ownerOf = (gig) => members.data?.find((member) => member.name === gig.gig_owner);

const columns = computed(() =>
	pipelineColumns.map((column) => ({
		...column,
		gigs: (gigs.data || []).filter((gig) => column.statuses.includes(gig.status)),
	}))
);

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

async function dropGig(column, columnElement) {
	const gig = draggedGig.value;
	draggedGig.value = dropColumn.value = null;
	if (!gig || column.statuses.includes(gig.status)) return;

	const previousStatus = gig.status;
	const status = column.statuses[0];
	if (!(await setStatus(gig, status))) return;

	const undoable = {
		action: { label: __("Undo"), onClick: () => setStatus(gig, previousStatus) },
		duration: UNDO_WINDOW_MS,
	};
	if (celebrations[status]) {
		burstConfetti(columnElement);
		toast.success(celebrations[status](gig.title), undoable);
	} else {
		toast(__("Moved {0} to {1}", [gig.title, column.label]), undoable);
	}
}

const isPanelOpen = ref(false);
const openedName = ref(null);

function openGig(name = null) {
	openedName.value = name;
	isPanelOpen.value = true;
}

// The search palette sends a gig name through the query, and it is cleared once the panel has it.
const route = useRoute();
const router = useRouter();
watch(
	() => route.query.gig,
	(name) => {
		if (!name || route.name !== "Pipeline") return;
		openGig(name);
		router.replace({ query: { ...route.query, gig: undefined } });
	},
	{ immediate: true }
);
</script>

<template>
	<div class="p-6">
		<div class="flex items-center justify-between">
			<h1 class="text-2xl-semibold">{{ __("Pipeline") }}</h1>
			<Button
				v-if="gigs.data?.length !== 0"
				variant="solid"
				icon-left="lucide-plus"
				:label="__('New gig')"
				@click="openGig()"
			/>
		</div>
		<div
			v-if="gigs.loading && !gigs.data"
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
		<ErrorMessage v-else-if="gigs.error" class="mt-4" :message="gigs.error" />
		<EmptyState
			v-else-if="!gigs.data?.length"
			class="mt-4"
			icon="lucide-guitar"
			:title="__('No gigs yet')"
			:description="
				__(
					'Add the first gig you are chasing, even if it is only an idea. Drag it from column to column as things move.'
				)
			"
		>
			<Button variant="solid" icon-left="lucide-plus" :label="__('New gig')" @click="openGig()" />
		</EmptyState>
		<template v-else>
			<ErrorMessage class="mt-4" :message="gigs.setValue.error" />
			<div class="mt-4 hidden gap-3 overflow-x-auto pb-2 md:flex">
				<section
					v-for="column in columns"
					:key="column.label"
					class="flex min-w-52 flex-1 flex-col rounded-6 bg-surface-gray-1 p-2"
					:class="dropColumn === column.label ? 'ring-2 ring-outline-gray-3' : ''"
					@dragover.prevent="dropColumn = column.label"
					@drop.prevent="dropGig(column, $event.currentTarget)"
				>
					<h2 class="flex items-center justify-between px-1 pb-2 text-sm-medium text-ink-gray-7">
						{{ column.label }}<span class="text-ink-gray-5">{{ column.gigs.length }}</span>
					</h2>
					<div class="min-h-24 flex-1 space-y-2">
						<GigCard
							v-for="gig in column.gigs"
							:key="gig.name"
							:gig="gig"
							:linked-titles="linkedTitles(gig)"
							:owner="ownerOf(gig)"
							:members="members.data || []"
							class="cursor-grab"
							draggable="true"
							@dragstart="draggedGig = gig"
							@dragend="draggedGig = dropColumn = null"
							@click="openGig(gig.name)"
							@assign="assignOwner(gig, $event)"
						/>
					</div>
				</section>
			</div>
			<div class="mt-4 space-y-6 md:hidden">
				<section v-for="column in columns.filter((column) => column.gigs.length)" :key="column.label">
					<h2 class="pb-2 text-sm-medium text-ink-gray-7">
						{{ column.label }} · {{ column.gigs.length }}
					</h2>
					<div class="space-y-2">
						<GigCard
							v-for="gig in column.gigs"
							:key="gig.name"
							:gig="gig"
							:linked-titles="linkedTitles(gig)"
							:owner="ownerOf(gig)"
							:members="members.data || []"
							@click="openGig(gig.name)"
							@assign="assignOwner(gig, $event)"
						/>
					</div>
				</section>
			</div>
		</template>
		<GigPanel
			v-if="isPanelOpen"
			:name="openedName"
			:controls="controls"
			@close="isPanelOpen = false"
			@saved="gigs.reload()"
		/>
	</div>
</template>
