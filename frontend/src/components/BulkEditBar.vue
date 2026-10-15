<script setup>
// Adapted from Frappe CRM's ListBulkActions.vue and EditValueModal.vue (https://github.com/frappe/crm), Copyright
// (C) Frappe Technologies Pvt. Ltd., AGPL-3.0. Modified for Roadie in October 2026: the edit and delete actions
// only, the form's own controls for the value, and a bar fixed to the screen, since Roadie's lists grow with the page.
// It replaces the ListView's select banner, so it goes in the ListView's default slot.
import { computed, inject, ref, watch } from "vue";
import { Button, Dialog, FormControl, Rating, call, toast } from "frappe-ui";
import { DELETE_BATCH_SIZE, UPDATE_BATCH_SIZE, blankValue, runInBatches } from "../bulkEdit";
import { RATING_STARS } from "../directory";
import { isBlank } from "../listFilters";
import { toStoredValue } from "../metaFields";

const props = defineProps({
	doctype: { type: String, required: true },
	fields: { type: Array, required: true },
	// Given the change and the names it is about to reach; returning false leaves the dialog open.
	confirmSave: { type: Function, default: null },
});
const emit = defineEmits(["updated", "deleted"]);

const list = inject("list");
const selections = computed(() => list.value.selections);

// The ListView keeps a selected name when a filter hides its row, and an edit must never reach what is not shown.
watch(
	() => list.value.rows,
	(rows) => {
		const shown = new Set(rows.map((row) => row[list.value.rowKey]));
		for (const name of selections.value) if (!shown.has(name)) selections.value.delete(name);
	}
);

// Every selected record would end up with the same name, so the title is edited one record at a time.
const editableFields = computed(() =>
	props.fields.filter((field) => !field.disabled && field.fieldname !== "title")
);
const fieldOptions = computed(() => [
	{ label: __("Choose a field"), value: "" },
	...editableFields.value.map((field) => ({ label: field.label, value: field.fieldname })),
]);

const isDialogOpen = ref(false);
// Taken when the dialog opens, so the selection cleared by a save does not relabel the dialog as it fades out.
const names = ref([]);
const fieldname = ref("");
const value = ref("");
const isSaving = ref(false);

const field = computed(() =>
	editableFields.value.find((candidate) => candidate.fieldname === fieldname.value)
);
const isClearing = computed(() => isBlank(value.value));
const canSave = computed(() => field.value && !isSaving.value && !(field.value.required && isClearing.value));
// Saving an empty value empties the field on every record, so the button says so rather than "Apply".
const saveLabel = computed(() =>
	field.value && isClearing.value
		? __("Clear {0} on {1} selected", [field.value.label, names.value.length])
		: __("Apply to {0} selected", [names.value.length])
);

function openDialog() {
	names.value = [...selections.value];
	fieldname.value = "";
	isDialogOpen.value = true;
}

function pickField(picked) {
	fieldname.value = picked;
	value.value = field.value ? blankValue(field.value) : "";
}

async function save() {
	const stored = toStoredValue(field.value, value.value);
	// An emptied field is cleared, where an empty string would be refused by a date.
	const change = { [fieldname.value]: isBlank(stored) ? null : stored };
	if (props.confirmSave && !props.confirmSave(change, names.value)) return;
	isSaving.value = true;
	const failed = await runInBatches(names.value, UPDATE_BATCH_SIZE, (docnames) =>
		call("frappe.desk.doctype.bulk_update.bulk_update.submit_cancel_or_update_docs", {
			doctype: props.doctype,
			docnames,
			action: "update",
			data: change,
		})
	);
	isSaving.value = false;
	isDialogOpen.value = false;
	reloadKeepingFailedSelected(failed);
	if (failed.length)
		toast.error(__("{0} of {1} could not be updated.", [failed.length, names.value.length]));
	else toast.success(__("Saved"));
}

const isDeleteDialogOpen = ref(false);

function confirmDelete() {
	names.value = [...selections.value];
	isDeleteDialogOpen.value = true;
}

async function deleteSelected() {
	isSaving.value = true;
	// A record still linked from another one is refused by Frappe and comes back among the failed names. Frappe
	// reads the names as a JSON string.
	const failed = await runInBatches(names.value, DELETE_BATCH_SIZE, (items) =>
		call("frappe.desk.reportview.delete_items", { doctype: props.doctype, items: JSON.stringify(items) })
	);
	isSaving.value = false;
	isDeleteDialogOpen.value = false;
	reloadKeepingFailedSelected(failed);
	// A record the screen has open must not outlive its deletion, with nothing left to save to.
	emit(
		"deleted",
		names.value.filter((name) => !failed.includes(name))
	);
	// frappe-ui drops Frappe's reason from a request that succeeds, and for a member it is a link that refuses a delete.
	if (failed.length)
		toast.error(
			__(
				"{0} of {1} could not be deleted while other records, such as contacts, tasks or gigs, link to them.",
				[failed.length, names.value.length]
			)
		);
	else toast.success(__("{0} deleted", [names.value.length]));
}

// The batches go on once started, so the dialog stays until they are done rather than look cancelled.
function setDeleteDialogOpen(isOpen) {
	if (!isSaving.value) isDeleteDialogOpen.value = isOpen;
}

// What failed stays selected, so it can be looked into or tried again.
function reloadKeepingFailedSelected(failed) {
	emit("updated");
	list.value.toggleAllRows(false);
	failed.forEach((name) => selections.value.add(name));
}
</script>

<template>
	<!-- Room for the bar under the last row, which it would otherwise cover. -->
	<div v-if="selections.size" class="h-16" aria-hidden="true" />
	<div
		v-if="selections.size"
		class="fixed inset-x-0 bottom-6 z-10 mx-auto flex w-max max-w-[calc(100%-2rem)] flex-wrap items-center gap-2 rounded-lg bg-surface-base px-4 py-2 text-base shadow-2xl"
	>
		<span class="me-2 text-ink-gray-9">{{ __("{0} selected", [selections.size]) }}</span>
		<Button variant="solid" icon-left="lucide-pencil" :label="__('Edit')" @click="openDialog" />
		<Button
			variant="subtle"
			theme="red"
			icon-left="lucide-trash-2"
			:label="__('Delete')"
			@click="confirmDelete"
		/>
		<Button
			variant="ghost"
			:label="__('Select all')"
			:disabled="list.allRowsSelected"
			@click="list.toggleAllRows(true)"
		/>
		<Button
			variant="ghost"
			icon="lucide-x"
			:label="__('Clear selection')"
			@click="list.toggleAllRows(false)"
		/>
	</div>
	<Dialog v-model:open="isDialogOpen" :title="__('Bulk edit')">
		<form class="space-y-4" @submit.prevent="canSave && save()">
			<FormControl
				type="select"
				:label="__('Field')"
				:options="fieldOptions"
				:model-value="fieldname"
				@update:model-value="pickField"
			/>
			<template v-if="field">
				<!-- FormControl has no rating type, so the stars are frappe-ui's own Rating, as in the entry form. -->
				<Rating
					v-if="field.type === 'rating'"
					v-model="value"
					:label="__('Value')"
					:max="RATING_STARS"
				/>
				<FormControl
					v-else
					v-model="value"
					:type="field.type"
					:label="field.type === 'checkbox' ? field.label : __('Value')"
					:options="field.options"
				/>
			</template>
		</form>
		<template #actions>
			<div class="flex justify-end gap-2">
				<Button :label="__('Cancel')" variant="ghost" @click="isDialogOpen = false" />
				<Button
					variant="solid"
					:label="saveLabel"
					:disabled="!canSave"
					:loading="isSaving"
					@click="save"
				/>
			</div>
		</template>
	</Dialog>
	<Dialog
		:open="isDeleteDialogOpen"
		:title="__('Delete {0} selected?', [names.length])"
		@update:open="setDeleteDialogOpen"
	>
		<p class="text-p-base text-ink-gray-7">
			{{
				__(
					"Their comments and attached files go with them, for the whole band, and this cannot be undone."
				)
			}}
		</p>
		<template #actions>
			<div class="flex justify-end gap-2">
				<Button
					:label="__('Cancel')"
					variant="ghost"
					:disabled="isSaving"
					@click="setDeleteDialogOpen(false)"
				/>
				<Button
					variant="solid"
					theme="red"
					:label="__('Delete {0} selected', [names.length])"
					:loading="isSaving"
					@click="deleteSelected"
				/>
			</div>
		</template>
	</Dialog>
</template>
