<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { Button, ErrorMessage, FileUploader, TextEditor, call, toast, useCall, useList } from "frappe-ui";
import DriveLinkDialog from "./DriveLinkDialog.vue";
import EmailRecipients from "./EmailRecipients.vue";
import { confirmDiscardDraft, trackDraft } from "../draft";

const props = defineProps({
	// Left out for a new email from the Inbox: Frappe then threads it on the recipient's contact, or on itself.
	doctype: { type: String, default: null },
	name: { type: String, default: null },
	draft: { type: Object, default: () => ({}) },
});
const emit = defineEmits(["sent", "discard"]);

const EDITOR_BUTTONS = [
	"Bold",
	"Italic",
	"Separator",
	"Bullet List",
	"Numbered List",
	"Separator",
	"Blockquote",
	"Link",
	"Separator",
	"Undo",
	"Redo",
];

// A draft's attachments are existing File records ({ name, file_name }): sending copies them, nothing is re-uploaded.
const { attachments: draftAttachments = [], ...draftFields } = props.draft;
const email = reactive({
	to: [],
	cc: [],
	bcc: [],
	subject: "",
	content: "",
	inReplyTo: null,
	...draftFields,
});
const invalidRecipientFields = reactive({ to: false, cc: false, bcc: false });
const hasInvalidRecipient = computed(() => Object.values(invalidRecipientFields).some(Boolean));
const sendButton = ref(null);
const attachments = ref([...draftAttachments]);
const isShowingCopies = ref(email.cc.length > 0);
const canLinkDriveItems = window.can_link_drive_items;
const isPickingDriveItem = ref(false);
const textEditor = ref(null);

// The first click in a quoted reply makes the editor append an empty paragraph, which is no edit.
const currentState = () =>
	JSON.stringify([
		email.to,
		email.cc,
		email.bcc,
		email.subject,
		attachments.value,
		textEditor.value.editor.getHTML().replace(/(<p><\/p>)+$/, ""),
	]);
let untouchedState;
// Once on its way, the email is no longer the writer's to lose: the request completes without the composer.
const isEdited = () => !send.loading && currentState() !== untouchedState;
let forgetDraft;
onMounted(() => {
	untouchedState = currentState();
	forgetDraft = trackDraft(isEdited);
});
// Before the editor inside is torn down, which would leave the check reading a destroyed editor.
onBeforeUnmount(() => forgetDraft());
defineExpose({ isEdited });

function discard() {
	if (confirmDiscardDraft(isEdited)) emit("discard");
}

function insertLink({ url, label }) {
	const { editor } = textEditor.value;
	if (!editor.state.selection.empty) {
		editor.chain().focus().setLink({ href: url }).run();
		return;
	}
	// The trailing space is unlinked, so typing after the link doesn't extend it.
	editor
		.chain()
		.focus()
		.insertContent([
			{ type: "text", text: label, marks: [{ type: "link", attrs: { href: url } }] },
			{ type: "text", text: " " },
		])
		.run();
}

const contacts = useList({
	doctype: "Contact",
	fields: ["full_name", "email_id"],
	filters: { email_id: ["is", "set"] },
	orderBy: "full_name asc",
	limit: 500,
});
const suggestions = computed(() =>
	(contacts.data || []).map((contact) => ({ label: contact.full_name, value: contact.email_id }))
);

// Matches EMAIL_DRAFT_FIELD in roadie/api.py, which only lets a draft delete the uploads stamped with it.
const UPLOAD_ARGS = { fieldname: "roadie_email_draft", private: true };

const send = useCall({
	url: "/api/v2/method/frappe.core.doctype.communication.email.make",
	method: "POST",
	immediate: false,
	onSuccess: () => {
		forgetDraft();
		emit("sent");
	},
});

// An upload is attached to the record as soon as it lands, so one the email never sends must be deleted.
async function deleteUpload(file) {
	try {
		await call("roadie.api.delete_draft_attachment", { file: file.name });
		return true;
	} catch (error) {
		toast.error(error.messages?.join("\n") || error.message);
		return false;
	}
}

async function removeAttachment(file) {
	if (await deleteUpload(file)) {
		attachments.value = attachments.value.filter((entry) => entry.name !== file.name);
	}
}

// Discard, replying elsewhere and closing the record all unmount the draft. A send under way owns the files.
onBeforeUnmount(() => {
	if (!send.loading && !send.data) attachments.value.forEach(deleteUpload);
});

function submit(event) {
	// The editor's toolbar buttons are submit buttons too: a Bold click, or Enter in the subject, would send the email.
	if (event.submitter !== sendButton.value.rootRef) return;
	send.submit({
		doctype: props.doctype,
		name: props.name,
		recipients: email.to,
		cc: email.cc,
		bcc: email.bcc,
		subject: email.subject,
		content: email.content,
		attachments: attachments.value.map((file) => file.name),
		in_reply_to: email.inReplyTo,
		send_email: 1,
	});
}
</script>

<template>
	<form data-draft class="rounded-6 border border-outline-gray-2 px-3 pb-3" @submit.prevent="submit">
		<div class="flex items-start gap-2">
			<EmailRecipients
				v-model="email.to"
				v-model:invalid="invalidRecipientFields.to"
				class="flex-1"
				:label="__('To')"
				:suggestions="suggestions"
			/>
			<Button
				v-if="!isShowingCopies"
				class="mt-1.5"
				variant="ghost"
				:label="__('Cc / Bcc')"
				@click="isShowingCopies = true"
			/>
		</div>
		<template v-if="isShowingCopies">
			<EmailRecipients
				v-model="email.cc"
				v-model:invalid="invalidRecipientFields.cc"
				:label="__('Cc')"
				:suggestions="suggestions"
			/>
			<EmailRecipients
				v-model="email.bcc"
				v-model:invalid="invalidRecipientFields.bcc"
				:label="__('Bcc')"
				:suggestions="suggestions"
			/>
		</template>
		<input
			v-model="email.subject"
			class="w-full border-x-0 border-b border-t-0 border-outline-gray-1 bg-transparent px-0 py-2 text-base text-ink-gray-8 focus:border-outline-gray-3 focus:ring-0"
			:placeholder="__('Subject')"
			required
		/>
		<TextEditor
			ref="textEditor"
			class="mt-2"
			:content="email.content"
			:fixed-menu="EDITOR_BUTTONS"
			:placeholder="__('Write your email…')"
			editor-class="prose-sm max-w-none min-h-40 max-h-96 overflow-y-auto py-2"
			@change="email.content = $event"
		/>
		<ul v-if="attachments.length" class="mt-2 flex flex-wrap gap-1.5">
			<li
				v-for="file in attachments"
				:key="file.name"
				class="inline-flex items-center gap-1 rounded bg-surface-gray-2 py-0.5 pl-2 pr-1 text-sm text-ink-gray-8"
			>
				<span class="lucide-paperclip size-3.5 text-ink-gray-5" aria-hidden="true" />
				{{ file.file_name }}
				<button
					type="button"
					class="lucide-x size-3.5 text-ink-gray-5 hover:text-ink-gray-8"
					:aria-label="__('Remove {0}', [file.file_name])"
					:disabled="send.loading"
					@click="removeAttachment(file)"
				/>
			</li>
		</ul>
		<ErrorMessage class="mt-2" :message="send.error" />
		<div class="mt-3 flex items-center justify-between">
			<div class="flex items-start gap-1">
				<FileUploader
					:upload-args="doctype ? { ...UPLOAD_ARGS, doctype, docname: name } : UPLOAD_ARGS"
					@success="attachments.push($event)"
				>
					<template #default="{ openFileSelector, uploading, progress, error }">
						<Button
							icon-left="lucide-paperclip"
							variant="ghost"
							:label="uploading ? __('Uploading {0}%', [progress]) : __('Attach')"
							:loading="uploading"
							@click="openFileSelector"
						/>
						<ErrorMessage class="mt-1" :message="error" />
					</template>
				</FileUploader>
				<Button
					v-if="canLinkDriveItems"
					icon-left="lucide-hard-drive"
					variant="ghost"
					:label="__('Link from Drive')"
					@click="isPickingDriveItem = true"
				/>
			</div>
			<div class="flex gap-2">
				<Button :label="__('Discard')" variant="ghost" @click="discard" />
				<Button
					ref="sendButton"
					type="submit"
					variant="solid"
					icon-left="lucide-send"
					:label="__('Send')"
					:loading="send.loading"
					:disabled="!email.to.length || hasInvalidRecipient"
				/>
			</div>
		</div>
		<!-- Mounted per opening, so each one starts from the Drive roots with no stale error. -->
		<DriveLinkDialog v-if="isPickingDriveItem" v-model:open="isPickingDriveItem" @pick="insertLink" />
	</form>
</template>
