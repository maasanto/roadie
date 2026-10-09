<script setup>
import { computed, ref } from "vue";
import { Badge, Dropdown, ErrorMessage, LoadingText, TabButtons, TextInput, useList } from "frappe-ui";
import EmailThread from "../components/EmailThread.vue";
import EntryContacts from "../components/EntryContacts.vue";
import EntryDialog from "../components/EntryDialog.vue";
import { directoryTypes } from "../directory";

// ponytail: one unpaged fetch per type, page server-side if the directory outgrows a few hundred entries
const lists = Object.fromEntries(
	directoryTypes.map(({ doctype }) => [
		doctype,
		useList({ doctype, fields: ["name", "title", "city"], orderBy: "title asc", limit: 500 }),
	]),
);

const activeType = ref("all");
const query = ref("");
const typeTabs = [{ value: "all", label: "All" }, ...directoryTypes.map((type) => ({ value: type.doctype, label: type.plural }))];

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

const dialogOpen = ref(false);
const editing = ref({ doctype: "Festival", name: null });

function openEntry(doctype, name = null) {
	editing.value = { doctype, name };
	dialogOpen.value = true;
}

const newOptions = directoryTypes.map(({ doctype }) => ({ label: doctype, onClick: () => openEntry(doctype) }));
</script>

<template>
	<div class="p-6">
		<div class="flex items-center justify-between">
			<h1 class="text-2xl-semibold">Directory</h1>
			<Dropdown :options="newOptions" align="end" :button="{ label: 'New', iconLeft: 'lucide-plus', variant: 'solid' }" />
		</div>
		<div class="mt-4 flex flex-wrap items-center gap-3">
			<TabButtons v-model="activeType" :options="typeTabs" />
			<TextInput v-model="query" type="search" placeholder="Search by name or city" class="w-64">
				<template #prefix><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" /></template>
			</TextInput>
		</div>
		<LoadingText v-if="isLoading" class="mt-4" />
		<ErrorMessage v-else-if="loadError" class="mt-4" :message="loadError" />
		<p v-else-if="!entries.length" class="mt-4 text-p-base text-ink-gray-5">Nothing here yet.</p>
		<ul v-else class="mt-4 divide-y divide-outline-gray-1 rounded-6 border">
			<li v-for="entry in entries" :key="`${entry.doctype}:${entry.name}`">
				<button
					class="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-surface-gray-2"
					@click="openEntry(entry.doctype, entry.name)"
				>
					<span class="min-w-0 flex-1 truncate text-base">{{ entry.title }}</span>
					<span class="w-40 truncate text-sm text-ink-gray-5">{{ entry.city }}</span>
					<Badge :label="entry.doctype" class="w-20 justify-center" />
				</button>
			</li>
		</ul>
		<EntryDialog
			v-model:open="dialogOpen"
			:doctype="editing.doctype"
			:name="editing.name"
			:fields="directoryTypes.find((type) => type.doctype === editing.doctype).fields"
			@saved="lists[editing.doctype].reload()"
		>
			<template #default="{ entryName }">
				<EntryContacts :doctype="editing.doctype" :name="entryName" />
				<EmailThread :doctype="editing.doctype" :name="entryName" />
			</template>
		</EntryDialog>
	</div>
</template>
