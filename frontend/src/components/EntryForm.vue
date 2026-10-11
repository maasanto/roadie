<script setup>
import { computed, reactive, ref, watch } from "vue";
import { Button, ErrorMessage, FormControl, Rating, Skeleton, toast, useCall } from "frappe-ui";
import FormCustomiser from "./FormCustomiser.vue";
import { RATING_STARS, joinList, splitList, toFraction, toStars } from "../directory";
import { useMeta } from "../meta";
import { fieldsFromMeta } from "../metaFields";

const props = defineProps({
	doctype: { type: String, required: true },
	name: { type: String, default: null },
	controls: { type: Object, default: () => ({}) },
});
const emit = defineEmits(["saved"]);

const entryName = ref(null);
const form = reactive({});
const meta = computed(() => useMeta(props.doctype));
const fields = computed(() => fieldsFromMeta(meta.value.data?.fields ?? [], props.controls));
const visibleFields = computed(() => fields.value.filter((field) => !field.hidden));
const isCustomising = ref(false);
const documentUrl = computed(() => `/api/v2/document/${props.doctype}/${entryName.value}`);

const loadEntry = useCall({ url: documentUrl, immediate: false });
const createEntry = useCall({
	url: computed(() => `/api/v2/document/${props.doctype}`),
	method: "POST",
	immediate: false,
});
const updateEntry = useCall({ url: documentUrl, method: "PUT", immediate: false });

// Saving only what changed keeps a stale form from reverting what a bandmate or a drag changed since.
// A modified-timestamp check would also refuse the save whenever an email lands on the record.
let loadedForm = {};
let loadedDoc = null;

// A multiselect round-trips: an array in the form, one comma-separated string in the database. A rating is a
// count of stars in the form and a fraction in the database.
const FORM_VALUE = { multiselect: splitList, rating: toStars };
const STORED_VALUE = { multiselect: joinList, rating: toFraction };

const toFormValue = (field, value) => FORM_VALUE[field.type]?.(value) ?? value ?? "";

const toStoredValue = (field, value) => STORED_VALUE[field.type]?.(value) ?? value;

// Two multiselections holding the same genres are unchanged, so they cannot be compared by reference.
const sameValue = (a, b) =>
	Array.isArray(a) && Array.isArray(b)
		? a.length === b.length && a.every((item, index) => item === b[index])
		: a === b;

function fillFields(newFields) {
	for (const field of newFields) {
		const { fieldname, type, default: defaultValue } = field;
		const value = loadedDoc ? loadedDoc[fieldname] ?? "" : defaultValue ?? "";
		// A checkbox emits booleans, so a stored 0 must load as false for an untouched box to read as unchanged.
		form[fieldname] = type === "checkbox" ? Boolean(Number(value)) : toFormValue(field, value);
		loadedForm[fieldname] = form[fieldname];
	}
}

function fillForm(doc) {
	loadedDoc = doc;
	fillFields(fields.value);
}

const changedFields = () =>
	Object.fromEntries(
		Object.entries(form).filter(([fieldname, value]) => !sameValue(value, loadedForm[fieldname]))
	);

// Leaving a blank or hidden field out lets the server apply its default, e.g. "Today" or the current user.
const filledFields = () =>
	Object.fromEntries(
		visibleFields.value
			.map(({ fieldname }) => [fieldname, form[fieldname]])
			.filter(([, value]) => value !== "")
	);

// The form holds what the control shows; the database takes the value it stores.
const storedFields = (values) => {
	const byName = Object.fromEntries(fields.value.map((field) => [field.fieldname, field]));
	return Object.fromEntries(
		Object.entries(values).map(([fieldname, value]) => [
			fieldname,
			toStoredValue(byName[fieldname], value),
		])
	);
};

// The meta may land after the record: fill only the newcomers, so it never overwrites what the member typed.
watch(fields, (newFields) => fillFields(newFields.filter(({ fieldname }) => !(fieldname in loadedForm))));

watch(
	() => props.name,
	async (name) => {
		entryName.value = name;
		fillForm(null);
		if (!name) return;
		await loadEntry.execute();
		fillForm(loadEntry.data);
	},
	{ immediate: true }
);

const saveCall = computed(() => (entryName.value ? updateEntry : createEntry));

async function save() {
	const call = saveCall.value;
	await call.submit(storedFields(entryName.value ? changedFields() : filledFields()));
	if (call.error) return;
	entryName.value = call.data.name;
	fillForm(call.data);
	toast.success(__("Saved"));
	emit("saved");
}

defineExpose({ form, entryName });
</script>

<template>
	<ErrorMessage v-if="meta.error && !meta.data" :message="meta.error" />
	<div
		v-else-if="loadEntry.loading || !meta.data"
		class="grid grid-cols-2 gap-4"
		aria-busy="true"
		:aria-label="__('Loading')"
	>
		<Skeleton
			v-for="field in visibleFields"
			:key="field.fieldname"
			class="h-14 rounded"
			:class="field.type === 'textarea' ? 'col-span-2' : ''"
		/>
	</div>
	<ErrorMessage v-else-if="loadEntry.error" :message="loadEntry.error" />
	<div v-else class="space-y-6">
		<FormCustomiser
			v-if="isCustomising"
			:doctype="doctype"
			:fields="fields"
			@done="isCustomising = false"
		/>
		<form v-else class="grid grid-cols-2 gap-4" @submit.prevent="save">
			<template v-for="field in visibleFields" :key="field.fieldname">
				<!-- FormControl has no rating type, so the stars are frappe-ui's own Rating. -->
				<Rating
					v-if="field.type === 'rating'"
					v-model="form[field.fieldname]"
					:label="field.label"
					:max="RATING_STARS"
					:disabled="field.disabled"
				/>
				<FormControl
					v-else
					v-model="form[field.fieldname]"
					:type="field.type"
					:label="field.label"
					:required="field.required"
					:options="field.options"
					:disabled="field.disabled"
					:class="field.type === 'textarea' ? 'col-span-2' : ''"
				/>
			</template>
			<ErrorMessage class="col-span-2" :message="saveCall.error" />
			<div class="col-span-2 flex justify-between">
				<Button
					icon-left="lucide-settings-2"
					variant="ghost"
					:label="__('Customise form')"
					@click="isCustomising = true"
				/>
				<Button
					type="submit"
					variant="solid"
					:loading="saveCall.loading"
					:label="entryName ? __('Save') : __('Create')"
				/>
			</div>
		</form>
		<slot v-if="entryName" :entry-name="entryName" />
	</div>
</template>
