<script setup>
import { computed, reactive, ref, watch } from "vue";
import { Button, ErrorMessage, FormControl, Skeleton, toast, useCall } from "frappe-ui";
import { joinList, splitList } from "../directory";

const props = defineProps({
	doctype: { type: String, required: true },
	name: { type: String, default: null },
	fields: { type: Array, required: true },
});
const emit = defineEmits(["saved"]);

const entryName = ref(null);
const form = reactive({});
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

// A multiselect round-trips: an array in the form, one comma-separated string in the database.
const toFormValue = (field, value) => (field.type === "multiselect" ? splitList(value) : value ?? "");

const toStoredValue = (field, value) => (field.type === "multiselect" ? joinList(value) : value);

const sameValue = (a, b) =>
	Array.isArray(a) && Array.isArray(b)
		? a.length === b.length && a.every((item, index) => item === b[index])
		: a === b;

function fillForm(doc) {
	for (const field of props.fields)
		form[field.fieldname] = toFormValue(field, doc ? doc[field.fieldname] : field.default);
	loadedForm = { ...form };
}

const changedFields = () =>
	Object.fromEntries(
		Object.entries(form).filter(([fieldname, value]) => !sameValue(value, loadedForm[fieldname]))
	);

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
	const fieldByName = Object.fromEntries(props.fields.map((field) => [field.fieldname, field]));
	const values = entryName.value ? changedFields() : { ...form };
	const payload = Object.fromEntries(
		Object.entries(values).map(([fieldname, value]) => [
			fieldname,
			toStoredValue(fieldByName[fieldname], value),
		])
	);
	await call.submit(payload);
	if (call.error) return;
	entryName.value = call.data.name;
	fillForm(call.data);
	toast.success(__("Saved"));
	emit("saved");
}

defineExpose({ form, entryName });
</script>

<template>
	<div v-if="loadEntry.loading" class="grid grid-cols-2 gap-4" aria-busy="true" :aria-label="__('Loading')">
		<Skeleton
			v-for="field in fields"
			:key="field.fieldname"
			class="h-14 rounded"
			:class="field.type === 'textarea' ? 'col-span-2' : ''"
		/>
	</div>
	<ErrorMessage v-else-if="loadEntry.error" :message="loadEntry.error" />
	<div v-else class="space-y-6">
		<form class="grid grid-cols-2 gap-4" @submit.prevent="save">
			<FormControl
				v-for="field in fields"
				:key="field.fieldname"
				v-model="form[field.fieldname]"
				:type="field.type"
				:label="field.label"
				:required="field.required"
				:options="field.options"
				:class="field.type === 'textarea' ? 'col-span-2' : ''"
			/>
			<ErrorMessage class="col-span-2" :message="saveCall.error" />
			<div class="col-span-2 flex justify-end">
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
