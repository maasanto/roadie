<script setup>
import { computed } from "vue";
import { Button, ErrorMessage, useList } from "frappe-ui";
import EmptyState from "../components/EmptyState.vue";
import ListSkeleton from "../components/ListSkeleton.vue";
import TaskRow from "../components/TaskRow.vue";
import { TASK_FIELDS, byDueDate, setDone } from "../task";

// ponytail: done tasks are never archived, add a date cut-off if the list grows long
const tasks = useList({
	doctype: "Band Task",
	fields: [...TASK_FIELDS, "gig.title as gig_title"],
	filters: { assignee: window.user },
	limit: 500,
});

const sections = computed(() => {
	const rows = tasks.data || [];
	return [
		{ label: __("To do"), tasks: rows.filter((task) => !task.done).sort(byDueDate) },
		{ label: __("Done"), tasks: rows.filter((task) => task.done).sort(byDueDate) },
	];
});
</script>

<template>
	<div class="max-w-3xl p-6">
		<h1 class="text-2xl-semibold">{{ __("My tasks") }}</h1>
		<ListSkeleton v-if="tasks.loading && !tasks.data" class="mt-6" />
		<ErrorMessage v-else-if="tasks.error" class="mt-4" :message="tasks.error" />
		<template v-else>
			<EmptyState
				v-if="!tasks.data?.length"
				class="mt-6"
				icon="lucide-list-checks"
				:title="__('Nothing assigned to you')"
				:description="
					__(
						'Open a gig and add a task to its checklist. Whatever is assigned to you shows up here, overdue first.'
					)
				"
			>
				<Button :label="__('Open the pipeline')" route="/" />
			</EmptyState>
			<section
				v-for="section in sections.filter((section) => section.tasks.length)"
				:key="section.label"
				class="mt-6"
			>
				<h2 class="pb-2 text-sm-medium text-ink-gray-7">
					{{ section.label }} · {{ section.tasks.length }}
				</h2>
				<ul class="divide-y divide-outline-gray-1 rounded-6 border">
					<TaskRow
						v-for="task in section.tasks"
						:key="task.name"
						:task="task"
						:context="task.gig_title"
						@update:done="setDone(tasks, task, $event)"
					/>
				</ul>
			</section>
		</template>
	</div>
</template>
