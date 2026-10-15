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
	availability_requested: "lucide-calendar-check",
	answered: "lucide-calendar-check",
};
</script>

<template>
	<ListSkeleton v-if="activity.loading && !activity.data" />
	<ErrorMessage v-else-if="activity.error" :message="activity.error" />
	<ol v-else>
		<!-- Frappe CRM's timeline: each icon sits on one rail that runs down to the last entry. -->
		<li
			v-for="(entry, index) in activity.data"
			:key="index"
			class="grid grid-cols-[30px_minmax(0,1fr)] gap-2 sm:gap-4"
		>
			<div
				class="relative z-0 flex justify-center before:absolute before:left-1/2 before:top-0 before:-z-[1] before:border-l before:border-outline-gray-2"
				:class="index < activity.data.length - 1 ? 'before:h-full' : 'before:h-4'"
				aria-hidden="true"
			>
				<span class="flex size-7 items-center justify-center bg-surface-base">
					<span
						class="size-4"
						:class="[
							ICONS[entry.type],
							entry.type === 'changed' ? 'text-ink-gray-4' : 'text-ink-gray-8',
						]"
					/>
				</span>
			</div>
			<div class="mb-4 min-w-0 py-1.5">
				<div class="flex items-start gap-2 text-base">
					<p class="line-clamp-3 min-w-0 flex-1 text-ink-gray-5">
						<span class="font-medium text-ink-gray-8">{{ entry.by }}</span>
						{{ describeActivity(entry) }}
					</p>
					<time
						class="shrink-0 whitespace-nowrap text-sm text-ink-gray-5"
						:title="formatDateTime(entry.at)"
					>
						{{ relativeDate(entry.at) }}
					</time>
				</div>
				<p v-if="entry.text" class="mt-1.5 line-clamp-2 text-p-sm text-ink-gray-7">
					{{ entry.text }}
				</p>
			</div>
		</li>
	</ol>
</template>
