<script setup>
import { computed, reactive, ref, watch } from "vue";
import { Button, ErrorMessage, FormControl, LoadingText, useCall } from "frappe-ui";

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
const createEntry = useCall({ url: computed(() => `/api/v2/document/${props.doctype}`), method: "POST", immediate: false });
const updateEntry = useCall({ url: documentUrl, method: "PUT", immediate: false });

function fillForm(doc) {
	for (const field of props.fields) form[field.fieldname] = doc?.[field.fieldname] ?? field.default ?? "";
}

watch(
	() => props.name,
	async (name) => {
		entryName.value = name;
		fillForm(null);
		if (!name) return;
		await loadEntry.execute();
		fillForm(loadEntry.data);
	},
	{ immediate: true },
);

const saveCall = computed(() => (entryName.value ? updateEntry : createEntry));

async function save() {
	const call = saveCall.value;
	await call.submit({ ...form });
	if (call.error) return;
	entryName.value = call.data.name;
	fillForm(call.data);
	emit("saved");
}

defineExpose({ form, entryName });
</script>

<template>
	<LoadingText v-if="loadEntry.loading" />
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
				<Button type="submit" variant="solid" :loading="saveCall.loading" :label="entryName ? 'Save' : 'Create'" />
			</div>
		</form>
		<slot v-if="entryName" :entry-name="entryName" />
	</div>
</template>
