<script setup>
import { ref } from "vue";
import { Dialog } from "frappe-ui";
import EntryForm from "./EntryForm.vue";

defineProps({
	doctype: { type: String, required: true },
	name: { type: String, default: null },
	fields: { type: Array, required: true },
});
const open = defineModel("open", { type: Boolean, default: false });
const emit = defineEmits(["saved"]);

const entryForm = ref(null);
</script>

<template>
	<Dialog
		v-model:open="open"
		:title="entryForm?.entryName ? entryForm.form.title || doctype : `New ${doctype}`"
		size="2xl"
	>
		<EntryForm ref="entryForm" :doctype="doctype" :name="name" :fields="fields" @saved="emit('saved')">
			<template #default="{ entryName }"><slot :entry-name="entryName" /></template>
		</EntryForm>
	</Dialog>
</template>
