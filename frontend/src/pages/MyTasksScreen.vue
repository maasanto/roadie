<script setup>
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Button, ErrorMessage, TabButtons, call, toast, useCall, useList } from "frappe-ui";
import EmptyState from "../components/EmptyState.vue";
import ListSkeleton from "../components/ListSkeleton.vue";
import TaskDialog from "../components/TaskDialog.vue";
import TaskRow from "../components/TaskRow.vue";
import { TASK_FIELDS, byDueDate, isShownTask, setDone } from "../task";
import { TASK_SCOPES, assigneeAvatar, scopeFromQuery } from "../taskScopes";

const route = useRoute();
const router = useRouter();

const scopeOptions = Object.entries(TASK_SCOPES).map(([value, { label }]) => ({ label, value }));
const scope = computed({
	get: () => scopeFromQuery(route.query.show),
	set: (value) => router.replace({ query: { ...route.query, show: value === "mine" ? undefined : value } }),
});

// Until a scope's own rows arrive, the previous scope's rows would show under the new tab.
const loadedScope = ref(null);
// ponytail: done tasks are never archived and Everyone reaches the cap first, add a date cut-off if the list grows long
const tasks = useList({
	doctype: "Band Task",
	fields: [...TASK_FIELDS, "gig.title as gig_title"],
	filters: () => TASK_SCOPES[scope.value].filters(window.user),
	limit: 500,
	onSuccess: () => (loadedScope.value = scope.value),
});
// Switching scope aborts the request in flight, and frappe-ui reports that abort as the list's error.
const loadError = computed(() => (tasks.loading || tasks.error?.name === "AbortError" ? null : tasks.error));

const members = useCall({ url: "/api/v2/method/roadie.api.get_members" });
const membersByName = computed(
	() => members.data && Object.fromEntries(members.data.map((member) => [member.name, member]))
);

const shownTasks = computed(() => (tasks.data || []).filter(isShownTask));
const openTasks = computed(() => shownTasks.value.filter((task) => !task.done).sort(byDueDate));
const doneTasks = computed(() => shownTasks.value.filter((task) => task.done).sort(byDueDate));
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

function openTask(task) {
	openedTask.value = task;
	isTaskOpen.value = true;
}
</script>

<template>
	<div class="max-w-3xl p-6">
		<div class="flex flex-wrap items-center justify-between gap-3">
			<h1 class="text-2xl-semibold">{{ __("My tasks") }}</h1>
			<TabButtons v-model="scope" :options="scopeOptions" :aria-label="__('Tasks to show')" />
		</div>
		<ErrorMessage v-if="loadError" class="mt-4" :message="loadError" />
		<ListSkeleton v-else-if="loadedScope !== scope" class="mt-6" />
		<template v-else>
			<EmptyState
				v-if="!shownTasks.length"
				class="mt-6"
				icon="lucide-list-checks"
				:title="TASK_SCOPES[scope].emptyTitle"
				:description="TASK_SCOPES[scope].emptyDescription"
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
						:assignee="scope === 'mine' ? null : assigneeAvatar(task, membersByName)"
						:gig-title="task.gig_title"
						@update:done="setDone(tasks, task, $event)"
						@open="openTask(task)"
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
						:assignee="scope === 'mine' ? null : assigneeAvatar(task, membersByName)"
						:gig-title="task.gig_title"
						@update:done="setDone(tasks, task, $event)"
						@open="openTask(task)"
					/>
				</ul>
			</section>
		</template>
		<TaskDialog
			v-if="openedTask"
			v-model:open="isTaskOpen"
			:name="openedTask.name"
			:members="members.data"
			@saved="tasks.reload()"
		/>
	</div>
</template>
