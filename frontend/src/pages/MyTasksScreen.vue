<script setup>
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Button, ErrorMessage, TabButtons, useCall, useList } from "frappe-ui";
import EmptyState from "../components/EmptyState.vue";
import ListSkeleton from "../components/ListSkeleton.vue";
import TaskRow from "../components/TaskRow.vue";
import { TASK_FIELDS, byDueDate, setDone } from "../task";
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
		<div class="flex flex-wrap items-center justify-between gap-3">
			<h1 class="text-2xl-semibold">{{ __("My tasks") }}</h1>
			<TabButtons v-model="scope" :options="scopeOptions" :aria-label="__('Tasks to show')" />
		</div>
		<ErrorMessage v-if="loadError" class="mt-4" :message="loadError" />
		<ListSkeleton v-else-if="loadedScope !== scope" class="mt-6" />
		<template v-else>
			<EmptyState
				v-if="!tasks.data?.length"
				class="mt-6"
				icon="lucide-list-checks"
				:title="TASK_SCOPES[scope].emptyTitle"
				:description="TASK_SCOPES[scope].emptyDescription"
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
						:assignee="scope === 'mine' ? null : assigneeAvatar(task, membersByName)"
						:context="task.gig_title"
						@update:done="setDone(tasks, task, $event)"
					/>
				</ul>
			</section>
		</template>
	</div>
</template>
