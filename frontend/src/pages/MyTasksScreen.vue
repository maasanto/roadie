<script setup>
import { computed } from "vue";
import { ErrorMessage, LoadingText, useList } from "frappe-ui";
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
		{ label: "To do", tasks: rows.filter((task) => !task.done).sort(byDueDate) },
		{ label: "Done", tasks: rows.filter((task) => task.done).sort(byDueDate) },
	];
});
</script>

<template>
	<div class="max-w-3xl p-6">
		<h1 class="text-2xl-semibold">My tasks</h1>
		<LoadingText v-if="tasks.loading && !tasks.data" class="mt-4" />
		<ErrorMessage v-else-if="tasks.error" class="mt-4" :message="tasks.error" />
		<template v-else>
			<ErrorMessage class="mt-4" :message="tasks.setValue.error" />
			<p v-if="!tasks.data?.length" class="mt-4 text-p-base text-ink-gray-5">Nothing assigned to you.</p>
			<section v-for="section in sections.filter((section) => section.tasks.length)" :key="section.label" class="mt-6">
				<h2 class="pb-2 text-sm-medium text-ink-gray-7">{{ section.label }} · {{ section.tasks.length }}</h2>
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
