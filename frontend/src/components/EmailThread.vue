<script setup>
import { computed, ref, watch } from "vue";
import { Avatar, Button, ErrorMessage, useCall } from "frappe-ui";
import EmailBody from "./EmailBody.vue";
import EmailComposer from "./EmailComposer.vue";
import { confirmDiscardDraft } from "../draft";
import { QUOTE_SELECTOR, asHtml, formatDateTime, openByDefault, replyDraft } from "../email";

const props = defineProps({
	doctype: { type: String, required: true },
	name: { type: String, required: true },
});
const emit = defineEmits(["loaded"]);

const openEmails = ref(new Set());
const emails = useCall({
	url: "/api/v2/method/roadie.api.get_emails",
	params: () => ({ doctype: props.doctype, name: props.name }),
});

// Post-flush, so whoever listens to `loaded` finds the emails rendered. A reload after a reply keeps what was open.
watch(
	() => emails.data,
	(thread) => {
		if (!thread) return;
		openEmails.value = new Set([...openEmails.value, ...openByDefault(thread)]);
		emit("loaded", thread);
	},
	{ flush: "post" }
);

function toggle(email) {
	const next = new Set(openEmails.value);
	if (!next.delete(email.name)) next.add(email.name);
	openEmails.value = next;
}

const expandAll = () => (openEmails.value = new Set(emails.data.map((email) => email.name)));

// A DOMParser document is inert: unlike an element's innerHTML, it loads no image and fires no handler.
function textOf(content, selectorToDrop) {
	const email = new DOMParser().parseFromString(asHtml(content), "text/html");
	email.querySelectorAll(selectorToDrop).forEach((node) => node.remove());
	email.querySelectorAll("p, div, br, li, tr").forEach((node) => node.after(" "));
	return email.body.textContent.replace(/\s+/g, " ").trim();
}

// A forward is all quote, so its preview falls back to the quoted text rather than to nothing.
const previews = computed(
	() =>
		new Map(
			(emails.data || []).map((email) => [
				email.name,
				textOf(email.content, `style, script, ${QUOTE_SELECTOR}`) ||
					textOf(email.content, "style, script"),
			])
		)
);

const draft = ref(null);
const composerKey = ref(0);

const composer = ref(null);

function compose(nextDraft) {
	if (composer.value && !confirmDiscardDraft(composer.value.isEdited)) return;
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
		<div class="flex items-center gap-2">
			<h2 class="flex-1 text-lg-semibold">{{ __("Emails") }}</h2>
			<Button
				v-if="emails.data?.length > openEmails.size"
				variant="ghost"
				icon-left="lucide-chevrons-up-down"
				:label="__('Expand all')"
				@click="expandAll"
			/>
			<Button icon-left="lucide-mail-plus" :label="__('Write')" @click="compose({})" />
		</div>
		<ul v-if="emails.data?.length" class="mt-3 space-y-2">
			<li v-for="email in emails.data" :key="email.name" data-email class="rounded-6 border">
				<button
					class="flex w-full items-start gap-2 rounded-6 px-3 py-2.5 text-left hover:bg-surface-gray-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-outline-gray-3"
					:aria-expanded="openEmails.has(email.name)"
					@click="toggle(email)"
				>
					<Avatar :label="email.sender_full_name || email.sender" size="md" />
					<span class="min-w-0 flex-1">
						<span class="block truncate text-base-medium text-ink-gray-8">
							{{ email.sender_full_name || email.sender }}
						</span>
						<span
							v-if="openEmails.has(email.name)"
							class="block truncate text-sm text-ink-gray-5"
						>
							{{ __("to {0}", [email.recipients])
							}}<template v-if="email.cc"> · {{ __("cc {0}", [email.cc]) }}</template>
						</span>
						<span v-else class="block truncate text-sm text-ink-gray-5">
							{{ previews.get(email.name) }}
						</span>
					</span>
					<span class="shrink-0 text-sm text-ink-gray-5">{{
						formatDateTime(email.communication_date)
					}}</span>
				</button>
				<div v-if="openEmails.has(email.name)" class="px-3 pb-2.5">
					<p class="text-base-medium text-ink-gray-8">{{ email.subject }}</p>
					<EmailBody class="mt-2" :content="email.content" />
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
						<Button
							icon-left="lucide-reply"
							variant="ghost"
							:label="__('Reply')"
							@click="compose(replyDraft(email, 'reply'))"
						/>
						<Button
							icon-left="lucide-reply-all"
							variant="ghost"
							:label="__('Reply all')"
							@click="compose(replyDraft(email, 'reply-all'))"
						/>
					</footer>
				</div>
			</li>
		</ul>
		<p v-else-if="emails.isFinished" class="mt-3 text-p-sm text-ink-gray-5">{{ __("No emails yet.") }}</p>
		<ErrorMessage class="mt-2" :message="emails.error" />
		<EmailComposer
			v-if="draft"
			:key="composerKey"
			ref="composer"
			class="mt-3"
			:doctype="doctype"
			:name="name"
			:draft="draft"
			@sent="onSent"
			@discard="draft = null"
		/>
	</section>
</template>
