<script setup>
import { ref, useId } from "vue";
import { isEmail } from "../email";

const emails = defineModel({ type: Array, required: true });
defineProps({
	label: { type: String, required: true },
	suggestions: { type: Array, default: () => [] },
});

const listId = useId();
const query = ref("");

function addTyped() {
	const typed = query.value.split(/[,;\s]+/).filter(Boolean);
	const valid = typed.filter((email) => isEmail(email) && !emails.value.includes(email));
	emails.value = [...emails.value, ...valid];
	query.value = typed.filter((email) => !isEmail(email)).join(" ");
}

const remove = (email) => (emails.value = emails.value.filter((entry) => entry !== email));

function onKeydown(event) {
	if (event.key === "Enter" || event.key === ",") {
		event.preventDefault();
		addTyped();
	} else if (event.key === "Backspace" && !query.value && emails.value.length) {
		remove(emails.value.at(-1));
	}
}
</script>

<template>
	<label class="flex flex-wrap items-center gap-1.5 border-b border-outline-gray-1 py-1.5">
		<span class="w-8 text-sm text-ink-gray-5">{{ label }}</span>
		<span
			v-for="email in emails"
			:key="email"
			class="inline-flex items-center gap-1 rounded bg-surface-gray-2 py-0.5 pl-2 pr-1 text-sm text-ink-gray-8"
		>
			{{ email }}
			<button
				type="button"
				class="lucide-x size-3.5 text-ink-gray-5 hover:text-ink-gray-8"
				:aria-label="__('Remove {0}', [email])"
				@click="remove(email)"
			/>
		</span>
		<input
			v-model="query"
			type="text"
			:list="listId"
			:aria-label="label"
			class="min-w-40 flex-1 border-none bg-transparent p-0 text-base text-ink-gray-8 focus:ring-0"
			@keydown="onKeydown"
			@blur="addTyped"
		/>
		<datalist :id="listId">
			<option v-for="suggestion in suggestions" :key="suggestion.value" :value="suggestion.value">
				{{ suggestion.label }}
			</option>
		</datalist>
	</label>
</template>
