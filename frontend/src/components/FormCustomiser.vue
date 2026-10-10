<script setup>
import { computed, reactive, ref } from "vue";
import { Button, ErrorMessage, FormControl, TextInput, toast, useCall } from "frappe-ui";
import { useMeta } from "../meta";

const props = defineProps({
	doctype: { type: String, required: true },
	fields: { type: Array, required: true },
});
const emit = defineEmits(["done"]);

const NEW_FIELD_TYPES = [
	{ label: __("Text"), value: "Data" },
	{ label: __("Long text"), value: "Small Text" },
	{ label: __("Number"), value: "Float" },
	{ label: __("Date"), value: "Date" },
	{ label: __("Checkbox"), value: "Check" },
	{ label: __("Choice list"), value: "Select" },
];
const protectedFields = window.protected_fields || [];
const isLocked = (field) => field.required || protectedFields.includes(field.fieldname);

const visibleFields = computed(() => props.fields.filter((field) => !field.hidden));
const hiddenFields = computed(() => props.fields.filter((field) => field.hidden));

const customiseCall = (method) =>
	useCall({ url: `/api/v2/method/roadie.api.${method}`, method: "POST", immediate: false });
const addField = customiseCall("add_form_field");
const renameField = customiseCall("rename_form_field");
const setFieldHidden = customiseCall("set_form_field_hidden");
const error = ref(null);

// One change at a time: overlapping calls abort one another, and the shared meta reload with them.
let pendingChange = Promise.resolve();

function apply(call, params, message) {
	pendingChange = pendingChange.then(async () => {
		await call.submit({ doctype: props.doctype, ...params });
		error.value = call.error;
		if (call.error) return false;
		await useMeta(props.doctype).reload();
		toast.success(message);
		return true;
	});
	return pendingChange;
}

async function rename(field, input) {
	const label = input.value.trim();
	if (label === field.label) return;
	const isRenamed =
		label &&
		(await apply(renameField, { fieldname: field.fieldname, label }, __("Renamed to {0}", [label])));
	if (!isRenamed) input.value = field.label;
}

const hideLabel = (field) =>
	isLocked(field)
		? __("{0} stays visible: Roadie relies on it", [field.label])
		: __("Hide {0}", [field.label]);

function hide(field) {
	if (isLocked(field)) return toast(hideLabel(field));
	apply(setFieldHidden, { fieldname: field.fieldname, hidden: true }, __("{0} hidden", [field.label]));
}

const show = (field) =>
	apply(
		setFieldHidden,
		{ fieldname: field.fieldname, hidden: false },
		__("{0} shown again", [field.label])
	);

const draft = reactive({ label: "", fieldtype: "Data", options: "" });

const isAdding = ref(false);

async function add() {
	if (isAdding.value) return;
	isAdding.value = true;
	const isAdded = await apply(addField, { ...draft }, __("{0} added", [draft.label.trim()]));
	isAdding.value = false;
	if (isAdded) Object.assign(draft, { label: "", fieldtype: "Data", options: "" });
}
</script>

<template>
	<section class="space-y-5">
		<p class="text-p-sm text-ink-gray-5">
			{{ __("Rename, hide or add fields. Changes apply to the whole band.") }}
		</p>
		<ul class="divide-y divide-outline-gray-1 rounded-6 border">
			<li
				v-for="field in visibleFields"
				:key="field.fieldname"
				class="flex items-center gap-2 px-2 py-1.5"
			>
				<TextInput
					class="flex-1"
					variant="ghost"
					:model-value="field.label"
					:aria-label="__('Name of the {0} field', [field.label])"
					@change="rename(field, $event.target)"
				/>
				<Button
					:icon="isLocked(field) ? 'lucide-lock' : 'lucide-eye-off'"
					variant="ghost"
					:label="hideLabel(field)"
					:tooltip="hideLabel(field)"
					@click="hide(field)"
				/>
			</li>
		</ul>
		<div v-if="hiddenFields.length">
			<h3 class="text-base-medium">{{ __("Hidden fields") }}</h3>
			<ul class="mt-2 divide-y divide-outline-gray-1 rounded-6 border">
				<li
					v-for="field in hiddenFields"
					:key="field.fieldname"
					class="flex items-center justify-between gap-2 px-3 py-1.5"
				>
					<span class="truncate text-base text-ink-gray-6">{{ field.label }}</span>
					<Button icon-left="lucide-eye" variant="ghost" :label="__('Show')" @click="show(field)" />
				</li>
			</ul>
		</div>
		<form class="grid grid-cols-[1fr_10rem_auto] items-end gap-2" @submit.prevent="add">
			<FormControl v-model="draft.label" :label="__('New field')" required />
			<FormControl
				v-model="draft.fieldtype"
				type="select"
				:label="__('Type')"
				:options="NEW_FIELD_TYPES"
			/>
			<Button type="submit" icon-left="lucide-plus" :label="__('Add')" :loading="isAdding" />
			<FormControl
				v-if="draft.fieldtype === 'Select'"
				v-model="draft.options"
				class="col-span-3"
				type="textarea"
				:label="__('Choices, one per line')"
				required
			/>
		</form>
		<ErrorMessage :message="error" />
		<div class="flex justify-end">
			<Button variant="solid" :label="__('Done')" @click="emit('done')" />
		</div>
	</section>
</template>
