<script setup>
import { Avatar, Checkbox } from "frappe-ui";
import { daysUntil, formatDate } from "../gig";

defineProps({
	task: { type: Object, required: true },
	assignee: { type: Object, default: null },
	context: { type: String, default: "" },
});
const emit = defineEmits(["update:done"]);

const isOverdue = (task) => !task.done && task.due_date && daysUntil(task.due_date) < 0;
</script>

<template>
	<li class="flex items-center gap-3 px-3 py-2">
		<Checkbox :model-value="Boolean(task.done)" :aria-label="`Done: ${task.title}`" @update:model-value="emit('update:done', $event)" />
		<div class="min-w-0 flex-1">
			<p class="truncate text-base" :class="task.done ? 'text-ink-gray-5 line-through' : 'text-ink-gray-8'">{{ task.title }}</p>
			<p v-if="context" class="truncate text-sm text-ink-gray-5">{{ context }}</p>
		</div>
		<span
			v-if="task.due_date"
			class="flex shrink-0 items-center gap-1 text-sm"
			:class="isOverdue(task) ? 'text-ink-red-7' : 'text-ink-gray-5'"
		>
			<span class="lucide-calendar-check size-3.5" aria-hidden="true" />{{ formatDate(task.due_date) }}
		</span>
		<Avatar v-if="assignee" :label="assignee.full_name" :image="assignee.user_image" size="sm" :title="assignee.full_name" />
	</li>
</template>
