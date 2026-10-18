<script setup>
import { computed } from "vue";
import { Avatar, Badge, Dropdown } from "frappe-ui";
import { availabilitySummary } from "../availability";
import {
	GIG_STATUSES,
	daysUntil,
	formatDate,
	formatFee,
	isDeadlineClose,
	memberOptions,
	pipelineColumns,
} from "../gig";
import { translatedOptions } from "../translation";

const props = defineProps({
	gig: { type: Object, required: true },
	linkedTitles: { type: Array, default: () => [] },
	owner: { type: Object, default: null },
	members: { type: Array, default: () => [] },
	showsOpeningDate: { type: Boolean, default: false },
	feeLabel: { type: String, default: null },
	activity: { type: Object, default: () => ({}) },
});
const emit = defineEmits(["assign", "move"]);

const closedStatuses = pipelineColumns.at(-1).statuses;
const hasOpenDeadline = computed(
	() => props.gig.application_closes && daysUntil(props.gig.application_closes) >= 0
);

// The label carries what the red or bold alone would only show.
const activityBadges = computed(() => {
	const { emails, unread_emails, open_tasks, next_due, comments, attachments } = props.activity;
	const isOverdue = next_due && daysUntil(next_due) < 0;
	return [
		{
			icon: "lucide-mail",
			count: emails,
			label: unread_emails ? __("Emails, {0} unread", [unread_emails]) : __("Emails"),
			class: unread_emails ? "font-semibold text-ink-gray-9" : "",
		},
		{
			icon: "lucide-list-checks",
			count: open_tasks,
			label: isOverdue ? __("Open tasks, some overdue") : __("Open tasks"),
			class: isOverdue ? "text-ink-red-7" : "",
		},
		{ icon: "lucide-message-square", count: comments, label: __("Comments") },
		{ icon: "lucide-paperclip", count: attachments, label: __("Attachments") },
	].filter((badge) => badge.count);
});

const availability = computed(() => {
	const summary = availabilitySummary(props.activity.availability);
	const label = summary.declined
		? __("{0} of {1} can play, {2} can't", [summary.available, summary.asked, summary.declined])
		: __("{0} of {1} can play", [summary.available, summary.asked]);
	return { ...summary, label };
});

const assignOptions = computed(() =>
	memberOptions(props.members).map((option) => ({
		...option,
		onClick: () => emit("assign", option.value),
	}))
);

// Statuses rather than columns, so a gig the band gave up on can be told apart from one the venue turned down.
const moveOptions = computed(() =>
	translatedOptions(GIG_STATUSES)
		.filter((option) => option.value !== props.gig.status)
		.map((option) => ({ ...option, onClick: () => emit("move", option.value) }))
);
</script>

<template>
	<div
		role="button"
		tabindex="0"
		:data-gig="gig.name"
		class="space-y-1.5 rounded-4 border border-outline-gray-1 bg-surface-elevation-1 p-3 shadow-sm hover:border-outline-gray-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-4"
		@keydown.enter.self.prevent="$event.currentTarget.click()"
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
			<span v-if="availability.asked" class="flex items-center gap-1" :title="availability.label">
				<span class="lucide-user-check size-3.5" :class="availability.tone" aria-hidden="true" />{{
					availability.available
				}}/{{ availability.asked }}<span class="sr-only">{{ availability.label }}</span>
			</span>
			<span v-if="feeLabel && gig.fee" class="flex items-center gap-1">
				<span class="lucide-banknote size-3.5" aria-hidden="true" />{{ feeLabel }}
				{{ formatFee(gig.fee) }}
			</span>
			<span v-if="showsOpeningDate && gig.application_opens" class="flex items-center gap-1">
				<span class="lucide-calendar-clock size-3.5" aria-hidden="true" />{{
					__("Applications open {0}", [formatDate(gig.application_opens)])
				}}
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
			<span
				v-for="badge in activityBadges"
				:key="badge.icon"
				class="flex items-center gap-1"
				:class="badge.class"
				:title="badge.label"
			>
				<span class="size-3.5" :class="badge.icon" aria-hidden="true" />{{ badge.count
				}}<span class="sr-only">{{ badge.label }}</span>
			</span>
			<Badge v-if="closedStatuses.includes(gig.status)" :label="__(gig.status)" />
			<!-- Beside Assign to, a second button would leave the title a third of a narrow column. -->
			<span class="ms-auto" @click.stop>
				<Dropdown
					:options="moveOptions"
					align="end"
					:button="{ icon: 'lucide-arrow-right-left', variant: 'ghost', label: __('Move to') }"
				/>
			</span>
		</div>
	</div>
</template>
