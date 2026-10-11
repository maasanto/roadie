<script setup>
// Adapted from Frappe CRM's Filter.vue (https://github.com/frappe/crm), Copyright (C) Frappe Technologies
// Pvt. Ltd., AGPL-3.0. Modified for Roadie in October 2026.
import { computed } from "vue";
import { Button, Dropdown, FormControl, Popover, Rating } from "frappe-ui";
import { RATING_STARS } from "../directory";
import { defaultValue, filterKind, newFilter, operatorOptions } from "../listFilters";

const props = defineProps({ fields: { type: Array, required: true } });
const filters = defineModel({ type: Array, required: true });

const fieldOf = (filter) => props.fields.find((field) => field.fieldname === filter.fieldname);
// A filter on a field since removed from the DocType filters nothing, so it is not listed either.
const shown = computed(() => filters.value.filter(fieldOf));

// One filter per field: a row can switch to its own field or to one no other row filters on.
const fieldOptions = (filter) =>
	props.fields
		.filter(
			(field) =>
				field.fieldname === filter.fieldname ||
				!filters.value.some((other) => other.fieldname === field.fieldname)
		)
		.map((field) => ({ label: field.label, value: field.fieldname }));

const addOptions = computed(() =>
	props.fields
		.filter((field) => !filters.value.some((filter) => filter.fieldname === field.fieldname))
		.map((field) => ({
			label: field.label,
			onClick: () => (filters.value = [...filters.value, newFilter(field)]),
		}))
);

const SET_OPTIONS = [
	{ label: __("Set"), value: "set" },
	{ label: __("Not set"), value: "not set" },
];
const YES_NO = [
	{ label: __("Yes"), value: "Yes" },
	{ label: __("No"), value: "No" },
];

function valueControl(filter) {
	const field = fieldOf(filter);
	if (filter.operator === "is") return { type: "select", options: SET_OPTIONS };
	const kind = filterKind(field);
	if (kind === "check") return { type: "select", options: YES_NO };
	if (kind === "select") return { type: "select", options: field.options };
	if (kind === "date") return { type: kind };
	// Each value reloads the list, so typed ones wait for the member to pause.
	return { type: kind === "number" ? "number" : "text", debounce: 300 };
}

function update(filter, change) {
	filters.value = filters.value.map((candidate) =>
		candidate === filter ? { ...filter, ...change } : candidate
	);
}

const changeField = (filter, fieldname) =>
	update(filter, newFilter(props.fields.find((field) => field.fieldname === fieldname)));

// "Is" takes Set or Not set, which no other operator understands, so crossing that line resets the value.
function changeOperator(filter, operator) {
	const crossesIs = (operator === "is") !== (filter.operator === "is");
	update(filter, { operator, value: crossesIs ? defaultValue(fieldOf(filter), operator) : filter.value });
}

const remove = (filter) => (filters.value = filters.value.filter((candidate) => candidate !== filter));
</script>

<template>
	<Popover align="end">
		<template #trigger>
			<div class="flex items-center">
				<Button
					icon-left="lucide-filter"
					:label="__('Filter')"
					:class="shown.length ? 'rounded-r-none' : ''"
				>
					<template v-if="shown.length" #suffix>
						<span
							class="flex size-5 items-center justify-center rounded bg-surface-base text-xs-medium text-ink-gray-8 shadow-sm"
							>{{ shown.length }}</span
						>
					</template>
				</Button>
				<Button
					v-if="shown.length"
					class="rounded-l-none border-l"
					icon="lucide-x"
					:label="__('Clear all filters')"
					@click.stop="filters = []"
				/>
			</div>
		</template>
		<template #default>
			<div class="flex w-[min(36rem,calc(100vw-2rem))] flex-col gap-2 p-2">
				<div
					v-for="(filter, index) in shown"
					:key="filter.fieldname"
					class="grid gap-2 sm:grid-cols-[3rem_9rem_9rem_1fr_auto] sm:items-center"
				>
					<span class="text-base text-ink-gray-5 sm:text-end">{{
						index === 0 ? __("Where") : __("And")
					}}</span>
					<FormControl
						type="select"
						:options="fieldOptions(filter)"
						:model-value="filter.fieldname"
						@update:model-value="(fieldname) => changeField(filter, fieldname)"
					/>
					<FormControl
						type="select"
						:options="operatorOptions(fieldOf(filter))"
						:model-value="filter.operator"
						@update:model-value="(operator) => changeOperator(filter, operator)"
					/>
					<!-- FormControl has no rating type, so the stars are frappe-ui's own Rating. Clicking the lit star
					     again clears it to 0, which leaves the filter waiting for a value rather than matching the unrated. -->
					<Rating
						v-if="filterKind(fieldOf(filter)) === 'rating'"
						:model-value="Number(filter.value) || 0"
						:max="RATING_STARS"
						@update:model-value="(value) => update(filter, { value: value || '' })"
					/>
					<FormControl
						v-else
						v-bind="valueControl(filter)"
						:model-value="filter.value"
						@update:model-value="(value) => update(filter, { value })"
					/>
					<Button
						variant="ghost"
						icon="lucide-x"
						:label="__('Remove filter')"
						@click="remove(filter)"
					/>
				</div>
				<p v-if="!shown.length" class="px-2 py-1 text-base text-ink-gray-5">
					{{ __("No filters yet: choose a field to filter by.") }}
				</p>
				<div class="flex items-center justify-between gap-2">
					<Dropdown
						v-if="addOptions.length"
						:options="addOptions"
						:button="{ label: __('Add filter'), iconLeft: 'lucide-plus', variant: 'ghost' }"
					/>
					<Button
						v-if="shown.length"
						variant="ghost"
						:label="__('Clear all filters')"
						@click="filters = []"
					/>
				</div>
			</div>
		</template>
	</Popover>
</template>
