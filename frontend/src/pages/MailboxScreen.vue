<script setup>
import { computed, ref, watch } from "vue";
import { Avatar, Badge, Button, ErrorMessage, useCall } from "frappe-ui";
import EmailThread from "../components/EmailThread.vue";
import EmptyState from "../components/EmptyState.vue";
import ListSkeleton from "../components/ListSkeleton.vue";
import { deliveryState, formatDateTime } from "../email";
import { onKey } from "../keyboard";

const props = defineProps({
	sentOrReceived: { type: String, required: true },
});
const isInbox = computed(() => props.sentOrReceived === "Received");

const mailbox = useCall({
	url: "/api/v2/method/roadie.api.get_mailbox",
	params: () => ({ sent_or_received: props.sentOrReceived }),
	refetch: true,
});
const markSeen = useCall({
	url: "/api/v2/method/roadie.api.mark_seen",
	method: "POST",
	immediate: false,
	onSuccess: () => mailbox.reload(),
});

const openEmail = ref(null);
watch(
	() => props.sentOrReceived,
	() => (openEmail.value = null)
);
onKey("Escape", () => (openEmail.value = null));

function open(email) {
	openEmail.value = email;
	if (isInbox.value && !email.seen) markSeen.submit({ name: email.name });
}
</script>

<template>
	<div class="p-6">
		<h1 class="text-2xl-semibold">{{ isInbox ? __("Inbox") : __("Outbox") }}</h1>
		<ListSkeleton v-if="mailbox.loading && !mailbox.data" class="mt-4" />
		<ErrorMessage v-else-if="mailbox.error" class="mt-4" :message="mailbox.error" />
		<EmptyState
			v-else-if="!mailbox.data?.length && isInbox"
			class="mt-4"
			icon="lucide-inbox"
			:title="__('No emails received yet')"
			:description="
				__('Replies to the emails the band sends from a gig or a directory entry land here.')
			"
		/>
		<EmptyState
			v-else-if="!mailbox.data?.length"
			class="mt-4"
			icon="lucide-send"
			:title="__('Nothing sent yet')"
			:description="
				__(
					'Open a gig and write to its contacts. Every email the band sends shows here with its delivery status.'
				)
			"
		>
			<Button :label="__('Open the pipeline')" route="/" />
		</EmptyState>
		<ul v-else class="mt-4 divide-y divide-outline-gray-1 rounded-6 border">
			<li v-for="email in mailbox.data" :key="email.name">
				<button
					class="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-surface-gray-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-outline-gray-3"
					:class="{ 'bg-surface-gray-2': openEmail?.name === email.name }"
					@click="open(email)"
				>
					<span
						class="size-2 shrink-0 rounded-full"
						:class="isInbox && !email.seen ? 'bg-surface-blue-7' : 'bg-transparent'"
						:aria-label="isInbox && !email.seen ? __('Unread') : undefined"
					/>
					<Avatar
						:label="isInbox ? email.sender_full_name || email.sender : email.recipients"
						size="md"
					/>
					<span
						class="min-w-0 flex-1 text-base md:flex md:items-center md:gap-3"
						:class="isInbox && !email.seen ? 'font-semibold text-ink-gray-9' : 'text-ink-gray-8'"
					>
						<span class="block truncate md:w-48 md:shrink-0">
							{{
								isInbox
									? email.sender_full_name || email.sender
									: __("To {0}", [email.recipients])
							}}
						</span>
						<span
							class="block truncate md:min-w-0 md:flex-1"
							:class="{ 'text-ink-gray-7': !isInbox || email.seen }"
						>
							{{ email.subject }}
						</span>
					</span>
					<Badge
						v-if="!isInbox"
						v-bind="deliveryState(email.delivery_status)"
						class="w-16 shrink-0 justify-center"
					/>
					<span class="hidden w-36 shrink-0 text-right text-sm text-ink-gray-5 md:block">{{
						formatDateTime(email.communication_date)
					}}</span>
				</button>
			</li>
		</ul>
		<aside
			v-if="openEmail"
			class="fixed inset-y-0 right-0 z-20 flex w-[34rem] max-w-full flex-col border-l bg-surface-base shadow-xl"
		>
			<header class="flex min-h-12 items-center justify-between gap-2 border-b px-5">
				<h2 class="truncate text-lg-semibold">{{ openEmail.subject }}</h2>
				<Badge
					v-if="openEmail.thread.doctype !== 'Communication'"
					:label="__(openEmail.thread.doctype)"
				/>
				<Button
					class="ml-auto"
					icon="lucide-x"
					variant="ghost"
					:label="__('Close')"
					@click="openEmail = null"
				/>
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
