<script setup>
import { Button, ErrorMessage, FileUploader, useCall } from "frappe-ui";

const props = defineProps({ gig: { type: String, required: true } });

const attachments = useCall({
	url: "/api/v2/method/band_crm.api.get_attachments",
	params: () => ({ gig: props.gig }),
});

const formatSize = (bytes) =>
	bytes < 1024 * 1024 ? __("{0} KB", [Math.ceil(bytes / 1024)]) : __("{0} MB", [(bytes / 1024 / 1024).toFixed(1)]);
</script>

<template>
	<section>
		<div class="flex items-center justify-between">
			<h2 class="text-lg-semibold">{{ __("Attachments") }}</h2>
			<FileUploader :upload-args="{ doctype: 'Gig', docname: gig, private: true }" @success="attachments.reload()">
				<template #default="{ openFileSelector, uploading, progress, error }">
					<Button
						icon-left="lucide-paperclip"
						:label="uploading ? __('Uploading {0}%', [progress]) : __('Attach')"
						:loading="uploading"
						@click="openFileSelector"
					/>
					<ErrorMessage class="mt-2" :message="error" />
				</template>
			</FileUploader>
		</div>
		<ul v-if="attachments.data?.length" class="mt-3 divide-y divide-outline-gray-1 rounded-6 border">
			<li v-for="file in attachments.data" :key="file.name">
				<a :href="file.file_url" target="_blank" class="flex items-center gap-3 px-3 py-2 hover:bg-surface-gray-1">
					<span class="lucide-file-text size-4 text-ink-gray-5" aria-hidden="true" />
					<span class="min-w-0 flex-1 truncate text-base text-ink-gray-8">{{ file.file_name }}</span>
					<span class="text-sm text-ink-gray-5">{{ formatSize(file.file_size) }}</span>
				</a>
			</li>
		</ul>
		<p v-else-if="attachments.isFinished" class="mt-3 text-p-sm text-ink-gray-5">{{ __("No attachments yet.") }}</p>
		<ErrorMessage class="mt-2" :message="attachments.error" />
	</section>
</template>
