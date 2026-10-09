<script setup>
import { ref } from "vue";
import { Avatar, Button, ErrorMessage, TextEditor, useCall } from "frappe-ui";
import EmailComposer from "./EmailComposer.vue";
import { asHtml, formatDateTime, replyDraft } from "../email";

const props = defineProps({
	doctype: { type: String, required: true },
	name: { type: String, required: true },
});

const emails = useCall({
	url: "/api/v2/method/band_crm.api.get_emails",
	params: () => ({ doctype: props.doctype, name: props.name }),
});

const draft = ref(null);
const composerKey = ref(0);

function compose(nextDraft) {
	draft.value = nextDraft;
	composerKey.value++;
}

function onSent() {
	draft.value = null;
	emails.reload();
}
</script>

<template>
	<section>
		<div class="flex items-center justify-between">
			<h2 class="text-lg-semibold">{{ __("Emails") }}</h2>
			<Button icon-left="lucide-mail-plus" :label="__('Write')" @click="compose({})" />
		</div>
		<ul v-if="emails.data?.length" class="mt-3 space-y-3">
			<li v-for="email in emails.data" :key="email.name" class="rounded-6 border px-3 py-2.5">
				<header class="flex items-start gap-2">
					<Avatar :label="email.sender_full_name || email.sender" size="md" />
					<div class="min-w-0 flex-1">
						<p class="truncate text-base-medium text-ink-gray-8">{{ email.sender_full_name || email.sender }}</p>
						<p class="truncate text-sm text-ink-gray-5">
							{{ __("to {0}", [email.recipients]) }}<template v-if="email.cc"> · {{ __("cc {0}", [email.cc]) }}</template>
						</p>
					</div>
					<span class="shrink-0 text-sm text-ink-gray-5">{{ formatDateTime(email.communication_date) }}</span>
				</header>
				<p class="mt-2 text-base-medium text-ink-gray-8">{{ email.subject }}</p>
				<TextEditor :content="asHtml(email.content)" :editable="false" editor-class="prose-sm max-w-none" />
				<ul v-if="email.attachments.length" class="mt-2 flex flex-wrap gap-1.5">
					<li v-for="file in email.attachments" :key="file.name">
						<a
							:href="file.file_url"
							target="_blank"
							class="inline-flex items-center gap-1 rounded bg-surface-gray-2 px-2 py-0.5 text-sm text-ink-gray-8 hover:bg-surface-gray-3"
						>
							<span class="lucide-paperclip size-3.5 text-ink-gray-5" aria-hidden="true" />
							{{ file.file_name }}
						</a>
					</li>
				</ul>
				<footer class="mt-2 flex gap-1">
					<Button icon-left="lucide-reply" variant="ghost" :label="__('Reply')" @click="compose(replyDraft(email, 'reply'))" />
					<Button icon-left="lucide-reply-all" variant="ghost" :label="__('Reply all')"@click="compose(replyDraft(email, 'reply-all'))" />
				</footer>
			</li>
		</ul>
		<p v-else-if="emails.isFinished" class="mt-3 text-p-sm text-ink-gray-5">{{ __("No emails yet.") }}</p>
		<ErrorMessage class="mt-2" :message="emails.error" />
		<EmailComposer v-if="draft" :key="composerKey" class="mt-3" :doctype="doctype" :name="name" :draft="draft" @sent="onSent" @discard="draft = null" />
	</section>
</template>
