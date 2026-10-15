<script setup>
import { ref } from "vue";
import { Dialog } from "frappe-ui";
import EntryForm from "./EntryForm.vue";
import { keepOpenForDraft } from "../draft";

defineProps({
	doctype: { type: String, required: true },
	name: { type: String, default: null },
	controls: { type: Object, default: () => ({}) },
});
const openModel = defineModel("open", { type: Boolean, default: false });
const open = keepOpenForDraft(openModel);
const emit = defineEmits(["saved"]);

const entryForm = ref(null);
</script>

<template>
	<Dialog
		v-model:open="open"
		:title="entryForm?.entryName ? entryForm.form.title || __(doctype) : __('New {0}', [__(doctype)])"
		size="2xl"
	>
		<EntryForm
			ref="entryForm"
			:doctype="doctype"
			:name="name"
			:controls="controls"
			@saved="emit('saved')"
		>
			<template v-if="$slots.actions" #actions><slot name="actions" /></template>
			<template #default="{ entryName }"><slot :entry-name="entryName" /></template>
		</EntryForm>
	</Dialog>
</template>
