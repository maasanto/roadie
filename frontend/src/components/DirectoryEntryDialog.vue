<script setup>
import { computed, reactive, ref, watch } from "vue";
import { Button, Dialog, ErrorMessage, FormControl, LoadingText, useCall } from "frappe-ui";
import EntryContacts from "./EntryContacts.vue";
import { directoryTypes } from "../directory";

const props = defineProps({ doctype: { type: String, required: true }, name: { type: String, default: null } });
const open = defineModel("open", { type: Boolean, default: false });
const emit = defineEmits(["saved"]);

const entryName = ref(null);
const form = reactive({});
const fields = computed(() => directoryTypes.find((type) => type.doctype === props.doctype).fields);
const documentUrl = computed(() => `/api/v2/document/${props.doctype}/${entryName.value}`);

const loadEntry = useCall({ url: documentUrl, immediate: false });
const createEntry = useCall({ url: computed(() => `/api/v2/document/${props.doctype}`), method: "POST", immediate: false });
const updateEntry = useCall({ url: documentUrl, method: "PUT", immediate: false });

watch(open, async (isOpen) => {
	if (!isOpen) return;
	entryName.value = props.name;
	for (const { fieldname } of fields.value) form[fieldname] = "";
	if (!entryName.value) return;
	await loadEntry.execute();
	for (const { fieldname } of fields.value) form[fieldname] = loadEntry.data?.[fieldname] ?? "";
});

const saveCall = computed(() => (entryName.value ? updateEntry : createEntry));

async function save() {
	const call = saveCall.value;
	await call.submit({ ...form });
	if (call.error) return;
	entryName.value = call.data.name;
	emit("saved");
}
</script>

<template>
	<Dialog v-model:open="open" :title="entryName ? form.title || doctype : `New ${doctype}`" size="2xl">
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
			<EntryContacts v-if="entryName" :doctype="doctype" :name="entryName" />
		</div>
	</Dialog>
</template>
