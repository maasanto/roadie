<script setup>
// Adapted from Frappe CRM's QuickFilterField.vue (https://github.com/frappe/crm), Copyright (C) Frappe
// Technologies Pvt. Ltd., AGPL-3.0. Modified for Roadie in October 2026.
import { computed } from "vue";
import { FormControl } from "frappe-ui";
import { RATING_STARS } from "../directory";
import { filterKind } from "../listFilters";

const props = defineProps({
	field: { type: Object, required: true },
	value: { type: [String, Number], default: "" },
});
const emit = defineEmits(["update"]);

const kind = computed(() => filterKind(props.field));

// A blank first choice is how a picked value is cleared again.
const selectOptions = computed(() => {
	const choices =
		kind.value === "rating"
			? Array.from({ length: RATING_STARS }, (unused, index) => ({
					label: __("At least {0} ★", [index + 1]),
					value: String(index + 1),
			  }))
			: props.field.options ?? [];
	return [{ label: props.field.label, value: "" }, ...choices];
});
</script>

<template>
	<FormControl
		v-if="kind === 'check'"
		type="checkbox"
		:label="field.label"
		:model-value="value === 'Yes'"
		@update:model-value="(checked) => emit('update', checked ? 'Yes' : '')"
	/>
	<FormControl
		v-else-if="kind === 'select' || kind === 'rating'"
		type="select"
		:options="selectOptions"
		:model-value="String(value)"
		@update:model-value="(picked) => emit('update', picked)"
	/>
	<FormControl
		v-else
		:type="kind === 'text' ? 'search' : kind"
		:placeholder="field.label"
		:aria-label="field.label"
		:debounce="300"
		:model-value="value"
		@update:model-value="(typed) => emit('update', typed)"
	/>
</template>
