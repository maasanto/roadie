<script setup>
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Button, ErrorMessage, call, toast, useList } from "frappe-ui";
import EmptyState from "../components/EmptyState.vue";
import ListSkeleton from "../components/ListSkeleton.vue";
import TaskDialog from "../components/TaskDialog.vue";
import TaskRow from "../components/TaskRow.vue";
import { TASK_FIELDS, byDueDate, setDone } from "../task";

const route = useRoute();
const router = useRouter();

// ponytail: done tasks are never archived, add a date cut-off if the list grows long
const tasks = useList({
	doctype: "Band Task",
	fields: [...TASK_FIELDS, "gig.title as gig_title"],
	filters: { assignee: window.user },
	limit: 500,
});

const openTasks = computed(() => (tasks.data || []).filter((task) => !task.done).sort(byDueDate));
const doneTasks = computed(() => (tasks.data || []).filter((task) => task.done).sort(byDueDate));
const isShowingDone = ref(false);

const isTaskOpen = ref(false);
const openedTask = ref(null);
let requestedTask = null;

// Search and notifications send a task through the query, and it is cleared once read. The task may be
// assigned to someone else and so missing from this list, which is why it is fetched. Only the last task
// picked opens, whichever request answers first.
watch(
	() => route.query.task,
	async (name) => {
		if (!name || route.name !== "MyTasks") return;
		requestedTask = name;
		router.replace({ query: { ...route.query, task: undefined } });
		try {
			const task = await call("frappe.client.get", { doctype: "Band Task", name });
			if (requestedTask !== name) return;
			openedTask.value = task;
			isTaskOpen.value = true;
		} catch (error) {
			toast.error(error.messages?.join("\n") || error.message);
		}
	},
	{ immediate: true }
);
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
			<section v-if="openTasks.length" class="mt-6">
				<h2 class="pb-2 text-sm-medium text-ink-gray-7">
					{{ __("To do") }} · {{ openTasks.length }}
				</h2>
				<ul class="divide-y divide-outline-gray-1 rounded-6 border">
					<TaskRow
						v-for="task in openTasks"
						:key="task.name"
						:task="task"
						:gig-title="task.gig_title"
						@update:done="setDone(tasks, task, $event)"
					/>
				</ul>
			</section>
			<section v-if="doneTasks.length" class="mt-6">
				<h2 class="pb-2 text-sm-medium text-ink-gray-7">
					<button
						type="button"
						class="flex items-center gap-1 rounded-6 hover:text-ink-gray-9 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
						:aria-expanded="isShowingDone"
						@click="isShowingDone = !isShowingDone"
					>
						<span
							class="size-3.5"
							:class="isShowingDone ? 'lucide-chevron-down' : 'lucide-chevron-right'"
							aria-hidden="true"
						/>
						{{ __("Done") }} · {{ doneTasks.length }}
					</button>
				</h2>
				<ul v-if="isShowingDone" class="divide-y divide-outline-gray-1 rounded-6 border">
					<TaskRow
						v-for="task in doneTasks"
						:key="task.name"
						:task="task"
						:gig-title="task.gig_title"
						@update:done="setDone(tasks, task, $event)"
					/>
				</ul>
			</section>
		</template>
		<TaskDialog
			v-if="openedTask"
			v-model:open="isTaskOpen"
			:name="openedTask.name"
			:title="openedTask.title"
		/>
	</div>
</template>
