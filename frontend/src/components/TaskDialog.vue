<script setup>
import { Dialog } from "frappe-ui";
import EmailThread from "./EmailThread.vue";

defineProps({
	name: { type: String, required: true },
	title: { type: String, required: true },
});
const open = defineModel("open", { type: Boolean, default: false });
</script>

<template>
	<Dialog v-model:open="open" :title="title" size="2xl">
		<EmailThread doctype="Band Task" :name="name" />
	</Dialog>
</template>
