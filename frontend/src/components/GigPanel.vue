<script setup>
import { ref } from "vue";
import { Button } from "frappe-ui";
import EmailThread from "./EmailThread.vue";
import EntryForm from "./EntryForm.vue";
import GigAttachments from "./GigAttachments.vue";
import GigTasks from "./GigTasks.vue";

defineProps({
	name: { type: String, default: null },
	fields: { type: Array, required: true },
});
const emit = defineEmits(["close", "saved"]);

const entryForm = ref(null);
</script>

<template>
	<aside
		class="fixed inset-y-0 right-0 z-20 flex w-[34rem] max-w-full flex-col border-l bg-surface-base shadow-xl"
		@keydown.esc="emit('close')"
	>
		<header class="flex min-h-12 items-center justify-between gap-2 border-b px-5">
			<h2 class="truncate text-lg-semibold">{{ entryForm?.entryName ? entryForm.form.title || "Gig" : "New gig" }}</h2>
			<Button icon="lucide-x" variant="ghost" label="Close" @click="emit('close')" />
		</header>
		<div class="flex-1 overflow-y-auto px-5 pb-10 pt-5">
			<EntryForm :key="name" ref="entryForm" doctype="Gig" :name="name" :fields="fields" @saved="emit('saved')">
				<template #default="{ entryName }">
					<GigTasks :gig="entryName" />
					<GigAttachments :gig="entryName" />
					<EmailThread doctype="Gig" :name="entryName" />
				</template>
			</EntryForm>
		</div>
	</aside>
</template>
