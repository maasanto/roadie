<script setup>
import { computed, ref, watch } from "vue";
import { Avatar, Badge, Button, ErrorMessage, LoadingText, useCall } from "frappe-ui";
import EmailThread from "../components/EmailThread.vue";
import { deliveryState, formatDateTime } from "../email";

const props = defineProps({
	sentOrReceived: { type: String, required: true },
});
const isInbox = computed(() => props.sentOrReceived === "Received");

const mailbox = useCall({
	url: "/api/v2/method/band_crm.api.get_mailbox",
	params: () => ({ sent_or_received: props.sentOrReceived }),
	refetch: true,
});
const markSeen = useCall({
	url: "/api/v2/method/band_crm.api.mark_seen",
	method: "POST",
	immediate: false,
	onSuccess: () => mailbox.reload(),
});

const openEmail = ref(null);
watch(() => props.sentOrReceived, () => (openEmail.value = null));

function open(email) {
	openEmail.value = email;
	if (isInbox.value && !email.seen) markSeen.submit({ name: email.name });
}
</script>

<template>
	<div class="p-6">
		<h1 class="text-2xl-semibold">{{ isInbox ? __("Inbox") : __("Outbox") }}</h1>
		<LoadingText v-if="mailbox.loading && !mailbox.data" class="mt-4" />
		<ErrorMessage v-else-if="mailbox.error" class="mt-4" :message="mailbox.error" />
		<p v-else-if="!mailbox.data?.length" class="mt-4 text-p-base text-ink-gray-5">{{ __("No emails yet.") }}</p>
		<ul v-else class="mt-4 divide-y divide-outline-gray-1 rounded-6 border">
			<li v-for="email in mailbox.data" :key="email.name">
				<button
					class="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-surface-gray-2"
					:class="{ 'bg-surface-gray-2': openEmail?.name === email.name }"
					@click="open(email)"
				>
					<span
						class="size-2 shrink-0 rounded-full"
						:class="isInbox && !email.seen ? 'bg-surface-blue-7' : 'bg-transparent'"
						:aria-label="isInbox && !email.seen ? __('Unread') : undefined"
					/>
					<Avatar :label="isInbox ? email.sender_full_name || email.sender : email.recipients" size="md" />
					<span
						class="w-48 shrink-0 truncate text-base"
						:class="isInbox && !email.seen ? 'font-semibold text-ink-gray-9' : 'text-ink-gray-8'"
					>
						{{ isInbox ? email.sender_full_name || email.sender : __("To {0}", [email.recipients]) }}
					</span>
					<span class="min-w-0 flex-1 truncate text-base" :class="isInbox && !email.seen ? 'font-semibold text-ink-gray-9' : 'text-ink-gray-7'">
						{{ email.subject }}
					</span>
					<Badge v-if="!isInbox" v-bind="deliveryState(email.delivery_status)" class="w-16 justify-center" />
					<span class="w-36 shrink-0 text-right text-sm text-ink-gray-5">{{ formatDateTime(email.communication_date) }}</span>
				</button>
			</li>
		</ul>
		<aside
			v-if="openEmail"
			class="fixed inset-y-0 right-0 z-20 flex w-[34rem] max-w-full flex-col border-l bg-surface-base shadow-xl"
			@keydown.esc="openEmail = null"
		>
			<header class="flex min-h-12 items-center justify-between gap-2 border-b px-5">
				<h2 class="truncate text-lg-semibold">{{ openEmail.subject }}</h2>
				<Badge v-if="openEmail.thread.doctype !== 'Communication'" :label="__(openEmail.thread.doctype)" />
				<Button class="ml-auto" icon="lucide-x" variant="ghost" :label="__('Close')" @click="openEmail = null" />
			</header>
			<div class="flex-1 overflow-y-auto px-5 pb-10 pt-5">
				<EmailThread
					:key="`${openEmail.thread.doctype}:${openEmail.thread.name}`"
					:doctype="openEmail.thread.doctype"
					:name="openEmail.thread.name"
				/>
			</div>
		</aside>
	</div>
</template>
