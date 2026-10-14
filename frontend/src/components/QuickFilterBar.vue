<script setup>
// Adapted from the quick filter row of Frappe CRM's ViewControls.vue (https://github.com/frappe/crm), Copyright
// (C) Frappe Technologies Pvt. Ltd., AGPL-3.0. Modified for Roadie in October 2026: the filters in a row, and the
// same row turned into chips to customise them.
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { Button, Dropdown } from "frappe-ui";
import QuickFilterField from "./QuickFilterField.vue";
import { useDirectoryQuickFilters } from "../directoryQuickFilters";
import { quickValue, setQuickValue } from "../listFilters";

const props = defineProps({
	doctype: { type: String, required: true },
	fields: { type: Array, required: true },
});
const filters = defineModel({ type: Array, required: true });
const isCustomising = defineModel("customising", { type: Boolean, default: false });

const { fieldnames, saving, save } = useDirectoryQuickFilters(props.doctype);

const fieldsNamed = (names) =>
	names.map((fieldname) => props.fields.find((field) => field.fieldname === fieldname)).filter(Boolean);

const quickFields = computed(() => fieldsNamed(fieldnames.value));

const draft = ref([]);
watch(isCustomising, (customising) => customising && (draft.value = [...fieldnames.value]));
// A bar that leaves the page, the pipeline's when its view changes, takes an unsaved customisation with it, or
// the page would keep its toolbar hidden and come back to an empty draft.
onBeforeUnmount(() => (isCustomising.value = false));

const draftFields = computed(() => fieldsNamed(draft.value));
const addOptions = computed(() =>
	props.fields
		.filter((field) => !draft.value.includes(field.fieldname))
		.map((field) => ({ label: field.label, onClick: () => draft.value.push(field.fieldname) }))
);

async function saveDraft() {
	if (await save(draft.value)) isCustomising.value = false;
}
</script>

<template>
	<div v-if="isCustomising" class="flex min-w-0 flex-1 flex-wrap items-center gap-2">
		<Button
			v-for="field in draftFields"
			:key="field.fieldname"
			icon-right="lucide-x"
			:label="field.label"
			:title="__('Remove {0}', [field.label])"
			@click="draft = draft.filter((fieldname) => fieldname !== field.fieldname)"
		/>
		<Dropdown
			v-if="addOptions.length"
			:options="addOptions"
			:button="{ label: __('Add filter'), iconLeft: 'lucide-plus', variant: 'ghost' }"
		/>
		<div class="ms-auto flex gap-1">
			<Button variant="solid" :label="__('Save')" :loading="saving" @click="saveDraft" />
			<Button icon="lucide-x" :label="__('Cancel')" @click="isCustomising = false" />
		</div>
	</div>
	<!-- A phone gives the filters a row of their own, two abreast, above the buttons, unless there are none. -->
	<div v-else-if="quickFields.length" class="grid w-full grid-cols-2 gap-2 sm:flex sm:w-auto sm:min-w-0 sm:flex-1 sm:flex-wrap">
		<div v-for="field in quickFields" :key="field.fieldname" class="sm:w-40">
			<QuickFilterField
				:field="field"
				:value="quickValue(filters, field)"
				@update="(value) => (filters = setQuickValue(filters, field, value))"
			/>
		</div>
	</div>
</template>
