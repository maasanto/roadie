<script setup>
import { computed, ref } from "vue";
import { Button, ErrorMessage, useList } from "frappe-ui";
import EntryDialog from "./EntryDialog.vue";
import { formatDate } from "../gig";

const props = defineProps({
	festival: { type: String, required: true },
	festivalTitle: { type: String, default: "" },
	festivalWebsite: { type: String, default: "" },
});

const editions = useList({
	doctype: "Festival Edition",
	fields: ["name", "year", "start_date", "end_date", "website", "application_url", "application_closes"],
	filters: () => ({ festival: props.festival }),
	orderBy: "year desc",
	limit: 100,
});

const isDialogOpen = ref(false);
const openedEdition = ref(null);

function openEdition(name) {
	openedEdition.value = name;
	isDialogOpen.value = true;
}

// An edition always belongs to the festival it is opened from, so its festival shows but cannot change.
const controls = computed(() => ({
	festival: {
		type: "combobox",
		options: [{ label: props.festivalTitle, value: props.festival }],
		default: props.festival,
		disabled: true,
	},
}));

const dates = (edition) => [edition.start_date, edition.end_date].filter(Boolean).map(formatDate).join(" – ");

// Frappe's URL check lets a javascript: link through, and a click on it would run as the member.
const webLink = (url) => (/^https?:\/\//i.test(url || "") ? url : null);
const websiteOf = (edition) => webLink(edition.website) || webLink(props.festivalWebsite);
</script>

<template>
	<section>
		<div class="flex items-center justify-between">
			<h2 class="text-lg-semibold">{{ __("Editions") }}</h2>
			<Button icon-left="lucide-plus" :label="__('Add edition')" @click="openEdition(null)" />
		</div>
		<ul v-if="editions.data?.length" class="mt-3 divide-y divide-outline-gray-1 rounded-6 border">
			<li
				v-for="edition in editions.data"
				:key="edition.name"
				class="flex cursor-pointer items-center gap-3 px-3 py-2 hover:bg-surface-gray-1"
				@click="openEdition(edition.name)"
			>
				<button type="button" class="w-12 text-start text-base-medium">{{ edition.year }}</button>
				<span class="min-w-0 flex-1 truncate text-base text-ink-gray-7">{{ dates(edition) }}</span>
				<span v-if="edition.application_closes" class="text-sm text-ink-gray-5">
					{{ __("Apply by {0}", [formatDate(edition.application_closes)]) }}
				</span>
				<a
					v-if="webLink(edition.application_url)"
					:href="webLink(edition.application_url)"
					target="_blank"
					rel="noopener"
					class="text-sm text-ink-blue-link"
					@click.stop
					>{{ __("Apply") }}</a
				>
				<a
					v-if="websiteOf(edition)"
					:href="websiteOf(edition)"
					target="_blank"
					rel="noopener"
					class="text-sm text-ink-blue-link"
					@click.stop
					>{{ __("Website") }}</a
				>
			</li>
		</ul>
		<p v-else-if="editions.data" class="mt-3 text-p-sm text-ink-gray-5">{{ __("No editions yet.") }}</p>
		<ErrorMessage class="mt-2" :message="editions.error" />
		<EntryDialog
			v-model:open="isDialogOpen"
			doctype="Festival Edition"
			:name="openedEdition"
			:controls="controls"
			@saved="editions.reload()"
		/>
	</section>
</template>
