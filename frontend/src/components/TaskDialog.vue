<script setup>
import { Dialog } from "frappe-ui";
import EmailThread from "./EmailThread.vue";
import { keepOpenForDraft } from "../draft";

defineProps({
	name: { type: String, required: true },
	title: { type: String, required: true },
});
const openModel = defineModel("open", { type: Boolean, default: false });
const open = keepOpenForDraft(openModel);
</script>

<template>
	<Dialog v-model:open="open" :title="title" size="2xl">
		<EmailThread doctype="Band Task" :name="name" />
	</Dialog>
</template>
