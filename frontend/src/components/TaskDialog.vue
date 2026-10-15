<script setup>
import { computed } from "vue";
import { Button } from "frappe-ui";
import EmailThread from "./EmailThread.vue";
import EntryDialog from "./EntryDialog.vue";
import { confirmDiscardDraft } from "../draft";
import { memberOptions } from "../gig";
import { deleteTask } from "../task";

const props = defineProps({
	name: { type: String, required: true },
	members: { type: Array, default: () => [] },
});
const open = defineModel("open", { type: Boolean, default: false });
const emit = defineEmits(["saved"]);

const controls = computed(() => ({
	assignee: { type: "combobox", options: memberOptions(props.members) },
}));

function deleteThisTask() {
	if (!confirmDiscardDraft()) return;
	open.value = false;
	deleteTask(props.name);
}
</script>

<template>
	<EntryDialog
		v-model:open="open"
		doctype="Band Task"
		:name="name"
		:controls="controls"
		@saved="emit('saved')"
	>
		<!-- Band Task isn't one of the forms members customise, so Delete takes the customiser's place. -->
		<template #actions>
			<Button
				icon-left="lucide-trash-2"
				variant="ghost"
				theme="red"
				:label="__('Delete task')"
				@click="deleteThisTask"
			/>
		</template>
		<template #default="{ entryName }">
			<EmailThread doctype="Band Task" :name="entryName" />
		</template>
	</EntryDialog>
</template>
