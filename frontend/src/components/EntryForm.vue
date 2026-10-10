<script setup>
import { computed, reactive, ref, watch } from "vue";
import { Button, ErrorMessage, FormControl, Skeleton, toast, useCall } from "frappe-ui";
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

function fillFields(newFields) {
	for (const { fieldname, type, default: defaultValue } of newFields) {
		const value = loadedDoc ? loadedDoc[fieldname] ?? "" : defaultValue ?? "";
		// A checkbox emits booleans, so a stored 0 must load as false for an untouched box to read as unchanged.
		form[fieldname] = type === "checkbox" ? Boolean(Number(value)) : value;
		loadedForm[fieldname] = form[fieldname];
	}
}

function fillForm(doc) {
	loadedDoc = doc;
	fillFields(fields.value);
}

const changedFields = () =>
	Object.fromEntries(Object.entries(form).filter(([fieldname, value]) => value !== loadedForm[fieldname]));

// Leaving a blank field out lets the server apply its default, e.g. "Today" or the current user.
const filledFields = () => Object.fromEntries(Object.entries(form).filter(([, value]) => value !== ""));

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
	await call.submit(entryName.value ? changedFields() : filledFields());
	if (call.error) return;
	entryName.value = call.data.name;
	fillForm(call.data);
	toast.success(__("Saved"));
	emit("saved");
}

defineExpose({ form, entryName });
</script>

<template>
	<ErrorMessage v-if="meta.error" :message="meta.error" />
	<div
		v-else-if="loadEntry.loading || !meta.data"
		class="grid grid-cols-2 gap-4"
		aria-busy="true"
		:aria-label="__('Loading')"
	>
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
				:disabled="field.disabled"
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
