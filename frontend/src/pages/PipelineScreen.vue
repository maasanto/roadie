<script setup>
import { computed, ref } from "vue";
import { Button, ErrorMessage, LoadingText, useCall, useList } from "frappe-ui";
import GigCard from "../components/GigCard.vue";
import GigPanel from "../components/GigPanel.vue";
import { gigFields, pipelineColumns } from "../gig";

// ponytail: the whole pipeline in one unpaged fetch, page per column if a band ever tracks hundreds of gigs
const gigs = useList({
	doctype: "Gig",
	fields: ["name", "title", "status", "gig_owner", "gig_date", "festival", "venue", "promoter", "application_closes"],
	orderBy: "modified desc",
	limit: 500,
});
const linkLists = Object.fromEntries(
	["Festival", "Venue", "Promoter"].map((doctype) => [
		doctype,
		useList({ doctype, fields: ["name", "title"], orderBy: "title asc", limit: 500 }),
	]),
);
const members = useCall({ url: "/api/v2/method/roadie.api.get_members" });

const titleOf = (doctype, name) => linkLists[doctype].data?.find((row) => row.name === name)?.title;
const linkedTitles = (gig) =>
	[titleOf("Festival", gig.festival), titleOf("Venue", gig.venue), titleOf("Promoter", gig.promoter)].filter(Boolean);
const ownerOf = (gig) => members.data?.find((member) => member.name === gig.gig_owner);

const columns = computed(() =>
	pipelineColumns.map((column) => ({
		...column,
		gigs: (gigs.data || []).filter((gig) => column.statuses.includes(gig.status)),
	})),
);

const fields = computed(() =>
	gigFields({
		festivals: linkLists.Festival.data,
		venues: linkLists.Venue.data,
		promoters: linkLists.Promoter.data,
		members: members.data,
	}),
);

const draggedGig = ref(null);
const dropColumn = ref(null);

async function dropGig(column) {
	const gig = draggedGig.value;
	draggedGig.value = dropColumn.value = null;
	if (!gig || column.statuses.includes(gig.status)) return;

	const previousStatus = gig.status;
	gig.status = column.statuses[0];
	await gigs.setValue.submit({ name: gig.name, status: gig.status });
	if (gigs.setValue.error) gig.status = previousStatus;
}

const panelOpen = ref(false);
const openedName = ref(null);

function openGig(name = null) {
	openedName.value = name;
	panelOpen.value = true;
}
</script>

<template>
	<div class="p-6">
		<div class="flex items-center justify-between">
			<h1 class="text-2xl-semibold">{{ __("Pipeline") }}</h1>
			<Button variant="solid" icon-left="lucide-plus" :label="__('New gig')" @click="openGig()" />
		</div>
		<LoadingText v-if="gigs.loading && !gigs.data" class="mt-4" />
		<ErrorMessage v-else-if="gigs.error" class="mt-4" :message="gigs.error" />
		<template v-else>
			<ErrorMessage class="mt-4" :message="gigs.setValue.error" />
			<div class="mt-4 hidden gap-3 overflow-x-auto pb-2 md:flex">
				<section
					v-for="column in columns"
					:key="column.label"
					class="flex min-w-52 flex-1 flex-col rounded-6 bg-surface-gray-1 p-2"
					:class="dropColumn === column.label ? 'ring-2 ring-outline-gray-3' : ''"
					@dragover.prevent="dropColumn = column.label"
					@drop.prevent="dropGig(column)"
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
							class="cursor-grab"
							draggable="true"
							@dragstart="draggedGig = gig"
							@dragend="draggedGig = dropColumn = null"
							@click="openGig(gig.name)"
						/>
					</div>
				</section>
			</div>
			<div class="mt-4 space-y-6 md:hidden">
				<p v-if="!gigs.data?.length" class="text-p-base text-ink-gray-5">{{ __("No gigs yet.") }}</p>
				<section v-for="column in columns.filter((column) => column.gigs.length)" :key="column.label">
					<h2 class="pb-2 text-sm-medium text-ink-gray-7">{{ column.label }} · {{ column.gigs.length }}</h2>
					<div class="space-y-2">
						<GigCard
							v-for="gig in column.gigs"
							:key="gig.name"
							:gig="gig"
							:linked-titles="linkedTitles(gig)"
							:owner="ownerOf(gig)"
							@click="openGig(gig.name)"
						/>
					</div>
				</section>
			</div>
		</template>
		<GigPanel
			v-if="panelOpen"
			:name="openedName"
			:fields="fields"
			@close="panelOpen = false"
			@saved="gigs.reload()"
		/>
	</div>
</template>
