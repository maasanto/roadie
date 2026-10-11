<script setup>
// Adapted from Frappe CRM's SortBy.vue (https://github.com/frappe/crm), Copyright (C) Frappe Technologies
// Pvt. Ltd., AGPL-3.0. Modified for Roadie in October 2026, down to the single key CRM shows as a direction
// toggle beside the field it sorts on.
import { computed } from "vue";
import { Button, Dropdown } from "frappe-ui";

const props = defineProps({ fields: { type: Array, required: true } });
// null is the list's own order: by relevance, then by name.
const sort = defineModel({ type: Object, default: null });

const sortedField = computed(() => props.fields.find((field) => field.fieldname === sort.value?.fieldname));

const options = computed(() => [
	{
		group: __("Sort by"),
		hideLabel: true,
		options: props.fields.map((field) => ({
			label: field.label,
			selected: field.fieldname === sort.value?.fieldname,
			onClick: () =>
				(sort.value = { fieldname: field.fieldname, direction: sort.value?.direction ?? "asc" }),
		})),
	},
	...(sort.value
		? [
				{
					group: __("Reset"),
					hideLabel: true,
					options: [
						{
							label: __("Default order"),
							icon: "lucide-rotate-ccw",
							onClick: () => (sort.value = null),
						},
					],
				},
		  ]
		: []),
]);

const isAscending = computed(() => sort.value?.direction === "asc");
const flip = () => (sort.value = { ...sort.value, direction: isAscending.value ? "desc" : "asc" });
</script>

<template>
	<div class="flex items-center">
		<Button
			v-if="sortedField"
			class="rounded-r-none border-r"
			:icon="isAscending ? 'lucide-arrow-up-narrow-wide' : 'lucide-arrow-down-wide-narrow'"
			:label="isAscending ? __('Ascending') : __('Descending')"
			@click="flip"
		/>
		<Dropdown
			align="end"
			:options="options"
			:button="{
				label: sortedField?.label ?? __('Sort'),
				iconLeft: sortedField ? undefined : 'lucide-arrow-up-down',
				iconRight: sortedField ? 'lucide-chevron-down' : undefined,
				class: sortedField ? 'rounded-l-none' : '',
			}"
		/>
	</div>
</template>
