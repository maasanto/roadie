<script setup>
import { ref } from "vue";
import { Avatar, Checkbox, Dialog } from "frappe-ui";
import EmailThread from "./EmailThread.vue";
import { daysUntil, formatDate } from "../gig";
import { resultRoute } from "../search";

defineProps({
	task: { type: Object, required: true },
	assignee: { type: Object, default: null },
	gigTitle: { type: String, default: "" },
});
const emit = defineEmits(["update:done"]);

const isOverdue = (task) => !task.done && task.due_date && daysUntil(task.due_date) < 0;
const isShowingEmails = ref(false);
</script>

<template>
	<li class="flex items-center gap-3 px-3 py-2">
		<!-- A fingertip target for touch screens. The negative margins must match the li's padding, or it reaches into the next row. -->
		<label
			class="flex items-center [@media(pointer:coarse)]:-mx-3 [@media(pointer:coarse)]:-my-2 [@media(pointer:coarse)]:self-stretch [@media(pointer:coarse)]:px-3"
		>
			<Checkbox
				:model-value="Boolean(task.done)"
				:aria-label="__('Done: {0}', [task.title])"
				@update:model-value="emit('update:done', $event)"
			/>
		</label>
		<div class="min-w-0 flex-1">
			<button
				type="button"
				class="block max-w-full truncate text-left text-base hover:underline"
				:class="task.done ? 'text-ink-gray-5 line-through' : 'text-ink-gray-8'"
				@click="isShowingEmails = true"
			>
				{{ task.title }}
			</button>
			<RouterLink
				v-if="gigTitle"
				:to="resultRoute({ doctype: 'Gig', name: task.gig })"
				class="block w-fit max-w-full truncate text-sm text-ink-gray-5 hover:underline"
			>
				{{ gigTitle }}
			</RouterLink>
		</div>
		<span
			v-if="task.due_date"
			class="flex shrink-0 items-center gap-1 text-sm"
			:class="isOverdue(task) ? 'text-ink-red-7' : 'text-ink-gray-5'"
		>
			<span class="lucide-calendar-check size-3.5" aria-hidden="true" />{{ formatDate(task.due_date) }}
		</span>
		<Avatar
			v-if="assignee"
			:label="assignee.full_name"
			:image="assignee.user_image"
			size="sm"
			:title="assignee.full_name"
		/>
		<Dialog v-model:open="isShowingEmails" :title="task.title" size="2xl">
			<EmailThread doctype="Band Task" :name="task.name" />
		</Dialog>
	</li>
</template>
