<script setup>
import { useId } from "vue";
import { splitRecipients } from "../email";

const emails = defineModel({ type: Array, required: true });
const isInvalid = defineModel("invalid", { type: Boolean, default: false });
const query = defineModel("query", { type: String, default: "" });
defineProps({
	label: { type: String, required: true },
	suggestions: { type: Array, default: () => [] },
});

const inputId = useId();
const errorId = useId();
const listId = useId();

function addTyped() {
	const { valid, invalid } = splitRecipients(query.value);
	emails.value = [...emails.value, ...valid.filter((email) => !emails.value.includes(email))];
	query.value = invalid.join(" ");
	isInvalid.value = invalid.length > 0;
}

function recheckWhileInvalid() {
	if (isInvalid.value) isInvalid.value = splitRecipients(query.value).invalid.length > 0;
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
	<!-- Without `for`, a click on the label would go to its first control: the first chip's remove button. -->
	<label :for="inputId" class="flex flex-wrap items-center gap-1.5 border-b border-outline-gray-1 py-1.5">
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
			:id="inputId"
			v-model="query"
			type="text"
			:list="listId"
			:aria-label="label"
			:aria-invalid="isInvalid"
			:aria-describedby="isInvalid ? errorId : undefined"
			class="min-w-40 flex-1 border-none bg-transparent p-0 text-base focus:ring-0"
			:class="isInvalid ? 'text-ink-red-7' : 'text-ink-gray-8'"
			@keydown="onKeydown"
			@input="recheckWhileInvalid"
			@blur="addTyped"
		/>
		<span v-if="isInvalid" :id="errorId" role="alert" class="basis-full text-sm text-ink-red-8">
			{{ __("Not a valid email address: {0}", [query]) }}
		</span>
		<datalist :id="listId">
			<option v-for="suggestion in suggestions" :key="suggestion.value" :value="suggestion.value">
				{{ suggestion.label }}
			</option>
		</datalist>
	</label>
</template>
