<script setup>
import { computed } from "vue";
import { Button, Dropdown, Popover } from "frappe-ui";
import { directoryControls } from "../directory";
import { columnFromField, isNameColumn, moveColumn } from "../listColumns";
import { useListView } from "../listView";
import { useMeta } from "../meta";
import { fieldsFromMeta } from "../metaFields";

const props = defineProps({ doctype: { type: String, required: true } });

const { columns, loaded, saved, saving, save, reset } = useListView(props.doctype);
const meta = useMeta(props.doctype);
const metaFields = computed(() => meta.data?.fields ?? []);
// The DocType's own word for a field, so a saved column does not carry one language's translation into another.
const ownLabels = computed(
	() => new Map(metaFields.value.map((field) => [field.fieldname, field.label || field.fieldname]))
);

// The fields this DocType can show but the list does not already. Only the ones a form can edit are offered,
// so a table, an attachment or a layout break never lands in a column.
const options = computed(() =>
	fieldsFromMeta(metaFields.value, directoryControls[props.doctype] ?? {})
		.filter((field) => !columns.value.some((column) => column.fieldname === field.fieldname))
		.map((field) => ({
			label: field.label,
			onClick: () =>
				save([
					...columns.value,
					columnFromField({
						...field,
						label: ownLabels.value.get(field.fieldname) ?? field.fieldname,
					}),
				]),
		}))
);

const move = (column, offset) => save(moveColumn(columns.value, column.fieldname, offset));
const remove = (column) => save(columns.value.filter((entry) => entry.fieldname !== column.fieldname));
</script>

<template>
	<Popover align="end">
		<template #trigger>
			<!-- A save inserts or updates depending on the layout already loaded, so the editor stays shut
			     until that is known — a failed fetch included, since saving on top of one would write the
			     defaults over the layout the member actually has. -->
			<Button icon="lucide-columns-3" :label="__('Columns')" :disabled="!loaded" />
		</template>
		<template #default>
			<div class="flex w-64 flex-col">
				<div
					v-for="(column, index) in columns"
					:key="column.fieldname"
					class="flex items-center gap-1 rounded px-2 py-1 text-base hover:bg-surface-gray-2"
				>
					<span class="min-w-0 flex-1 truncate">{{ __(column.label) }}</span>
					<Button
						v-if="index > 1"
						variant="ghost"
						icon="lucide-arrow-up"
						:disabled="saving"
						:label="__('Move {0} up', [__(column.label)])"
						@click="move(column, -1)"
					/>
					<Button
						v-if="index > 0 && index < columns.length - 1"
						variant="ghost"
						icon="lucide-arrow-down"
						:disabled="saving"
						:label="__('Move {0} down', [__(column.label)])"
						@click="move(column, 1)"
					/>
					<Button
						v-if="!isNameColumn(column)"
						variant="ghost"
						icon="lucide-x"
						:disabled="saving"
						:label="__('Remove {0}', [__(column.label)])"
						@click="remove(column)"
					/>
				</div>
				<div class="mt-1 flex flex-col gap-1 border-t pt-1">
					<Dropdown
						v-if="options.length"
						:options="options"
						:button="{
							label: __('Add column'),
							iconLeft: 'lucide-plus',
							variant: 'ghost',
							disabled: saving,
						}"
					/>
					<Button
						v-if="saved"
						variant="ghost"
						icon-left="lucide-rotate-ccw"
						class="!justify-start"
						:disabled="saving"
						:label="__('Reset to default')"
						@click="reset"
					/>
				</div>
			</div>
		</template>
	</Popover>
</template>
