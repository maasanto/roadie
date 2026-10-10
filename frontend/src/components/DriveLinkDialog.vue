<script setup>
import { computed, ref } from "vue";
import { Button, Dialog, ErrorMessage, useCall } from "frappe-ui";
import ListSkeleton from "./ListSkeleton.vue";

const open = defineModel("open", { type: Boolean, default: false });
const emit = defineEmits(["pick"]);

const openedFolders = ref([]);
const selectedItem = ref(null);
const currentFolder = computed(() => openedFolders.value.at(-1));

const teamHomes = useCall({
	url: "/api/v2/method/drive.api.permissions.get_teams",
	params: { details: 1, exclude_personal: 0 },
	transform: (teamsByName) =>
		Object.values(teamsByName).map((team) => ({
			name: team.file,
			// Drive titles a personal team with the user's email, and shows it as Home.
			file_name: team.personal ? __("Home") : team.title,
			is_folder: 1,
		})),
	onSuccess: (homes) => homes.length === 1 && openFolder(homes[0]),
});
const folderItems = useCall({
	url: "/api/v2/method/drive.api.list.files",
	immediate: false,
	transform: (items) => items.toSorted((first, second) => second.is_folder - first.is_folder),
});
const shareLink = useCall({
	url: "/api/v2/method/roadie.api.share_drive_link",
	method: "POST",
	immediate: false,
});

const listing = computed(() => (currentFolder.value ? folderItems : teamHomes));
// Drive lets only an item's owner, or whoever it was shared with, share it; a public item already has its link.
const PUBLIC_SHARE_COUNT = -2;
const canLink = (item) => item.share || item.share_count === PUBLIC_SHARE_COUNT;

async function insertLink() {
	// Captured now: the selection may change, or the dialog close, while Drive shares the item.
	const item = selectedItem.value;
	const url = await shareLink.submit({ entity_name: item.name });
	if (shareLink.error || !open.value) return;
	emit("pick", { url, label: item.file_name });
	open.value = false;
}

function openFolder(folder) {
	openedFolders.value.push(folder);
	loadCurrentFolder();
}

function goBackTo(depth) {
	openedFolders.value = openedFolders.value.slice(0, depth);
	if (currentFolder.value) loadCurrentFolder();
}

function loadCurrentFolder() {
	selectedItem.value = null;
	folderItems.submit({ entity_name: currentFolder.value.name, order_by: "file_name" });
}
</script>

<template>
	<Dialog v-model:open="open" :title="__('Link to a Drive item')" size="xl">
		<nav
			class="flex flex-wrap items-center gap-1 text-base text-ink-gray-6"
			:aria-label="__('Folder path')"
		>
			<button type="button" class="hover:text-ink-gray-9" @click="goBackTo(0)">
				{{ __("Drive") }}
			</button>
			<template v-for="(folder, index) in openedFolders" :key="folder.name">
				<span class="lucide-chevron-right size-3.5" aria-hidden="true" />
				<button type="button" class="hover:text-ink-gray-9" @click="goBackTo(index + 1)">
					{{ folder.file_name }}
				</button>
			</template>
		</nav>
		<ListSkeleton v-if="listing.loading" class="mt-3" :rows="3" />
		<ul
			v-else-if="listing.data?.length"
			class="mt-3 max-h-80 divide-y divide-outline-gray-1 overflow-y-auto rounded-6 border"
		>
			<li v-for="item in listing.data" :key="item.name" class="flex items-center">
				<button
					type="button"
					class="flex min-w-0 flex-1 items-center gap-3 px-3 py-2 text-left disabled:opacity-50"
					:class="
						selectedItem?.name === item.name
							? 'bg-surface-gray-3'
							: 'enabled:hover:bg-surface-gray-1'
					"
					:aria-pressed="selectedItem?.name === item.name"
					:disabled="currentFolder && !canLink(item)"
					:title="
						currentFolder && !canLink(item)
							? __('Only its owner can share this item.')
							: undefined
					"
					@click="currentFolder ? (selectedItem = item) : openFolder(item)"
				>
					<span
						:class="item.is_folder ? 'lucide-folder' : 'lucide-file'"
						class="size-4 shrink-0 text-ink-gray-5"
						aria-hidden="true"
					/>
					<span class="truncate text-base text-ink-gray-8">{{ item.file_name }}</span>
				</button>
				<Button
					v-if="currentFolder && item.is_folder"
					class="mr-1"
					variant="ghost"
					icon="lucide-chevron-right"
					:label="__('Open {0}', [item.file_name])"
					@click="openFolder(item)"
				/>
			</li>
		</ul>
		<p v-else-if="listing.isFinished" class="mt-3 text-p-sm text-ink-gray-5">
			{{ currentFolder ? __("This folder is empty.") : __("You are not a member of any Drive team.") }}
		</p>
		<ErrorMessage class="mt-2" :message="listing.error || shareLink.error" />
		<p class="mt-3 flex items-start gap-2 text-p-sm text-ink-gray-7">
			<span class="lucide-globe mt-0.5 size-4 shrink-0" aria-hidden="true" />
			{{ __("Inserting the link makes the item public: anyone who has the link can open it.") }}
		</p>
		<template #actions>
			<div class="flex justify-end gap-2">
				<Button :label="__('Cancel')" variant="ghost" @click="open = false" />
				<Button
					variant="solid"
					:label="__('Insert link')"
					:disabled="!selectedItem"
					:loading="shareLink.loading"
					@click="insertLink"
				/>
			</div>
		</template>
	</Dialog>
</template>
