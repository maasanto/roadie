<script setup>
import { computed } from "vue";
import { Avatar, Badge, Dropdown } from "frappe-ui";
import { daysUntil, formatDate, isDeadlineClose, memberOptions, pipelineColumns } from "../gig";

const props = defineProps({
	gig: { type: Object, required: true },
	linkedTitles: { type: Array, default: () => [] },
	owner: { type: Object, default: null },
	members: { type: Array, default: () => [] },
});
const emit = defineEmits(["assign"]);

const closedStatuses = pipelineColumns.at(-1).statuses;
const hasOpenDeadline = computed(
	() => props.gig.application_closes && daysUntil(props.gig.application_closes) >= 0
);

const assignOptions = computed(() =>
	memberOptions(props.members).map((option) => ({
		...option,
		onClick: () => emit("assign", option.value),
	}))
);
</script>

<template>
	<div
		role="button"
		tabindex="0"
		class="space-y-1.5 rounded-4 border border-outline-gray-1 bg-surface-elevation-1 p-3 shadow-sm hover:border-outline-gray-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-4"
		@keydown.enter.prevent="$event.currentTarget.click()"
	>
		<div class="flex items-start gap-2">
			<span class="min-w-0 flex-1 text-base-medium text-ink-gray-8">{{ gig.title }}</span>
			<Avatar
				v-if="owner"
				:label="owner.full_name"
				:image="owner.user_image"
				size="sm"
				:title="owner.full_name"
			/>
			<span class="contents" @click.stop>
				<Dropdown
					:options="assignOptions"
					align="end"
					:button="{ icon: 'lucide-user-plus', variant: 'ghost', label: __('Assign to') }"
				/>
			</span>
		</div>
		<p v-if="linkedTitles.length" class="truncate text-sm text-ink-gray-6">
			{{ linkedTitles.join(" · ") }}
		</p>
		<div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-ink-gray-5">
			<span v-if="gig.gig_date" class="flex items-center gap-1">
				<span class="lucide-calendar size-3.5" aria-hidden="true" />{{ formatDate(gig.gig_date) }}
			</span>
			<span
				v-if="hasOpenDeadline"
				class="flex items-center gap-1"
				:class="isDeadlineClose(gig.application_closes) ? 'text-ink-red-7' : ''"
			>
				<span class="lucide-alarm-clock size-3.5" aria-hidden="true" />{{
					__("Apply by {0}", [formatDate(gig.application_closes)])
				}}
			</span>
			<Badge v-if="closedStatuses.includes(gig.status)" :label="__(gig.status)" />
		</div>
	</div>
</template>
