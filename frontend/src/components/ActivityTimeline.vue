<script setup>
import { ErrorMessage, useCall } from "frappe-ui";
import ListSkeleton from "./ListSkeleton.vue";
import { describeActivity } from "../activity";
import { formatDateTime } from "../email";
import { relativeDate } from "../notifications";

const props = defineProps({
	doctype: { type: String, required: true },
	name: { type: String, required: true },
});

const activity = useCall({
	url: "/api/v2/method/roadie.api.get_activity",
	params: () => ({ doctype: props.doctype, name: props.name }),
});

const ICONS = {
	created: "lucide-plus",
	changed: "lucide-pencil",
	commented: "lucide-message-square",
	attached: "lucide-paperclip",
	detached: "lucide-trash-2",
	emailed: "lucide-mail",
};
</script>

<template>
	<ListSkeleton v-if="activity.loading && !activity.data" />
	<ErrorMessage v-else-if="activity.error" :message="activity.error" />
	<ol v-else>
		<li v-for="(entry, index) in activity.data" :key="index" class="relative flex gap-3 pb-5">
			<span
				v-if="index < activity.data.length - 1"
				class="absolute bottom-0 left-3.5 top-7 w-px bg-outline-gray-2"
				aria-hidden="true"
			/>
			<span
				class="flex size-7 shrink-0 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-6"
				aria-hidden="true"
			>
				<span class="size-3.5" :class="ICONS[entry.type]" />
			</span>
			<div class="min-w-0 flex-1 pt-1">
				<p class="line-clamp-3 text-p-base text-ink-gray-6">
					<span class="font-medium text-ink-gray-9">{{ entry.by }}</span>
					{{ describeActivity(entry) }}
					<time class="whitespace-nowrap text-ink-gray-5" :title="formatDateTime(entry.at)">
						· {{ relativeDate(entry.at) }}
					</time>
				</p>
				<p v-if="entry.text" class="mt-1 line-clamp-2 text-p-sm text-ink-gray-7">{{ entry.text }}</p>
			</div>
		</li>
	</ol>
</template>
