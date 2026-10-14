<script setup>
import { computed, reactive, ref } from "vue";
import { Button, ErrorMessage, FormControl, useCall, useList } from "frappe-ui";
import TaskRow from "./TaskRow.vue";
import { TASK_FIELDS, byDueDate, setDone } from "../task";

const props = defineProps({ gig: { type: String, required: true } });

const tasks = useList({
	doctype: "Band Task",
	fields: TASK_FIELDS,
	filters: () => ({ gig: props.gig }),
	orderBy: "creation asc",
	limit: 500,
});
const openTasks = computed(() => (tasks.data || []).filter((task) => !task.done).sort(byDueDate));
const doneTasks = computed(() => (tasks.data || []).filter((task) => task.done).sort(byDueDate));
const isShowingDone = ref(false);

const members = useCall({ url: "/api/v2/method/roadie.api.get_members" });
const memberOptions = computed(() =>
	(members.data || []).map((member) => ({ label: member.full_name, value: member.name }))
);
const memberOf = (task) => members.data?.find((member) => member.name === task.assignee);

const emptyTask = () => ({ title: "", assignee: window.user, start_date: "", due_date: "" });
const newTask = reactive(emptyTask());

async function addTask() {
	await tasks.insert.submit({ ...newTask, gig: props.gig });
	if (tasks.insert.error) return;
	Object.assign(newTask, emptyTask());
}
</script>

<template>
	<section>
		<h2 class="text-lg-semibold">{{ __("Tasks") }}</h2>
		<template v-if="tasks.data?.length">
			<ul v-if="openTasks.length" class="mt-3 divide-y divide-outline-gray-1 rounded-6 border">
				<TaskRow
					v-for="task in openTasks"
					:key="task.name"
					:task="task"
					:assignee="memberOf(task)"
					@update:done="setDone(tasks, task, $event)"
				/>
			</ul>
			<Button
				v-if="doneTasks.length"
				class="mt-2"
				variant="ghost"
				:icon-left="isShowingDone ? 'lucide-chevron-down' : 'lucide-chevron-right'"
				:label="isShowingDone ? __('Hide done') : __('Show {0} done', [doneTasks.length])"
				:aria-expanded="isShowingDone"
				@click="isShowingDone = !isShowingDone"
			/>
			<ul
				v-if="isShowingDone && doneTasks.length"
				class="mt-2 divide-y divide-outline-gray-1 rounded-6 border"
			>
				<TaskRow
					v-for="task in doneTasks"
					:key="task.name"
					:task="task"
					:assignee="memberOf(task)"
					@update:done="setDone(tasks, task, $event)"
				/>
			</ul>
		</template>
		<p v-else-if="tasks.isFinished" class="mt-3 text-p-sm text-ink-gray-5">{{ __("No tasks yet.") }}</p>
		<ErrorMessage class="mt-2" :message="tasks.error" />
		<form class="mt-3 grid grid-cols-2 gap-3" @submit.prevent="addTask">
			<FormControl
				v-model="newTask.title"
				class="col-span-2"
				type="text"
				:placeholder="__('New task')"
				required
			/>
			<template v-if="newTask.title">
				<FormControl
					v-model="newTask.assignee"
					class="col-span-2"
					type="combobox"
					:label="__('Assignee')"
					:options="memberOptions"
				/>
				<FormControl v-model="newTask.start_date" type="date" :label="__('Start date')" />
				<FormControl v-model="newTask.due_date" type="date" :label="__('Due date')" />
				<div class="col-span-2 flex justify-end">
					<Button
						type="submit"
						icon-left="lucide-plus"
						:label="__('Add task')"
						:loading="tasks.insert.loading"
					/>
				</div>
			</template>
			<ErrorMessage class="col-span-2" :message="tasks.insert.error" />
		</form>
	</section>
</template>
