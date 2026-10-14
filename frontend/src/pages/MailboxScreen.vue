<script setup>
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Avatar, Badge, Button, ErrorMessage, toast, useCall } from "frappe-ui";
import EmailComposer from "../components/EmailComposer.vue";
import EmailThread from "../components/EmailThread.vue";
import EmptyState from "../components/EmptyState.vue";
import ListSkeleton from "../components/ListSkeleton.vue";
import { confirmDiscardDraft } from "../draft";
import { deliveryState, formatListDate, isUnread } from "../email";
import { onKey, onShortcut } from "../keyboard";
import { resultRoute } from "../search";

const props = defineProps({
	sentOrReceived: { type: String, required: true },
});
const isInbox = computed(() => props.sentOrReceived === "Received");
const route = useRoute();
const router = useRouter();

const mailbox = useCall({
	url: "/api/v2/method/roadie.api.get_mailbox",
	params: () => ({ sent_or_received: props.sentOrReceived }),
	refetch: true,
});
const markSeen = useCall({
	url: "/api/v2/method/roadie.api.mark_thread_seen",
	method: "POST",
	immediate: false,
	onSuccess: () => mailbox.reload(),
});

const isUnreadOnly = ref(false);
const isComposing = ref(false);
const openThread = computed(() =>
	route.params.doctype ? { doctype: route.params.doctype, name: route.params.name } : null
);
const isOpen = (row) =>
	row.thread.doctype === openThread.value?.doctype && row.thread.name === openThread.value?.name;
// The open thread stays listed once read, or it would vanish under the reader and j/k would lose their place.
const rows = computed(() =>
	(mailbox.data || []).filter((row) => !isUnreadOnly.value || row.unread || isOpen(row))
);
const threadSubject = ref("");

const list = ref(null);
const pane = ref(null);

// The route guard asks before an unsent email is lost, so the screen only changes once the navigation went through.
// A failed one is a kept draft, the thread already open, or a later j/k overtaking this one.
async function open(row) {
	if (await router.push({ name: route.name, params: row.thread })) return;
	isComposing.value = false;
	threadSubject.value = row.subject;
	list.value?.querySelector("[aria-current]")?.scrollIntoView({ block: "nearest" });
}

const close = () => router.push({ name: route.name });

async function compose() {
	if (openThread.value && (await close())) return;
	isComposing.value = true;
}

function stopComposing() {
	if (confirmDiscardDraft()) isComposing.value = false;
}

function onNewEmailSent() {
	isComposing.value = false;
	toast.success(__("Email sent"));
	router.push({ name: "Outbox" });
}

// Read once the thread is on screen, so its unread emails are still the ones it opens on. Decided from the thread
// itself, not its row, which a deep link can reach before the mailbox has loaded.
function onThreadLoaded(thread) {
	threadSubject.value = thread.at(-1)?.subject || threadSubject.value;
	if (isInbox.value && thread.some(isUnread)) markSeen.submit(openThread.value);
	pane.value?.querySelector("[data-email]:last-child")?.scrollIntoView({ block: "start" });
}

function step(offset) {
	const index = rows.value.findIndex(isOpen);
	const next = index === -1 ? rows.value[0] : rows.value[index + offset];
	if (next) open(next);
}

// No arrow keys: they scroll the reading pane. And no modifier, which would steal Ctrl+J and the like.
onShortcut({ key: "j" }, () => step(1));
onShortcut({ key: "k" }, () => step(-1));
onKey("Escape", close);
</script>

<template>
	<div class="flex h-full">
		<section
			class="flex min-w-0 flex-1 flex-col md:max-w-md md:border-r"
			:class="{ 'max-md:hidden': openThread || isComposing }"
		>
			<header class="flex h-12 shrink-0 items-center gap-2 px-4">
				<h1 class="flex-1 text-2xl-semibold">{{ isInbox ? __("Inbox") : __("Outbox") }}</h1>
				<template v-if="isInbox">
					<Button
						:variant="isUnreadOnly ? 'subtle' : 'ghost'"
						:label="__('Unread')"
						:aria-pressed="isUnreadOnly"
						@click="isUnreadOnly = !isUnreadOnly"
					/>
					<Button
						variant="solid"
						icon-left="lucide-mail-plus"
						:label="__('New email')"
						@click="compose"
					/>
				</template>
			</header>
			<div ref="list" class="flex-1 overflow-y-auto border-t">
				<ListSkeleton v-if="mailbox.loading && !mailbox.data" class="m-4" />
				<ErrorMessage v-else-if="mailbox.error" class="m-4" :message="mailbox.error" />
				<EmptyState
					v-else-if="!mailbox.data?.length && isInbox"
					class="m-4"
					icon="lucide-inbox"
					:title="__('No emails received yet')"
					:description="
						__('Replies to the emails the band sends from a gig or a directory entry land here.')
					"
				/>
				<EmptyState
					v-else-if="!mailbox.data?.length"
					class="m-4"
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
				<p v-else-if="!rows.length" class="m-4 text-p-sm text-ink-gray-5">
					{{ __("No unread emails.") }}
				</p>
				<ul v-else class="divide-y divide-outline-gray-1">
					<li v-for="row in rows" :key="`${row.thread.doctype}:${row.thread.name}`">
						<button
							class="flex w-full items-start gap-3 px-4 py-3 text-left hover:bg-surface-gray-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-outline-gray-3"
							:class="{ 'bg-surface-gray-2': isOpen(row) }"
							:aria-current="isOpen(row) || undefined"
							@click="open(row)"
						>
							<span
								class="mt-3 size-2 shrink-0 rounded-full"
								:class="isInbox && row.unread ? 'bg-surface-blue-7' : 'bg-transparent'"
								:aria-label="isInbox && row.unread ? __('Unread') : undefined"
							/>
							<Avatar
								:label="isInbox ? row.sender_full_name || row.sender : row.recipients"
								size="md"
							/>
							<span class="min-w-0 flex-1">
								<span class="flex items-baseline gap-2">
									<span
										class="min-w-0 flex-1 truncate text-base"
										:class="
											isInbox && row.unread
												? 'font-semibold text-ink-gray-9'
												: 'text-ink-gray-8'
										"
									>
										{{
											isInbox
												? row.sender_full_name || row.sender
												: __("To {0}", [row.recipients])
										}}
									</span>
									<span v-if="row.count > 1" class="text-sm text-ink-gray-5">{{
										row.count
									}}</span>
									<span class="shrink-0 text-sm text-ink-gray-5">{{
										formatListDate(row.communication_date)
									}}</span>
								</span>
								<span class="mt-0.5 flex items-center gap-2">
									<span
										class="min-w-0 flex-1 truncate text-sm"
										:class="isInbox && row.unread ? 'text-ink-gray-8' : 'text-ink-gray-6'"
									>
										{{ row.subject }}
									</span>
									<Badge
										v-if="!isInbox"
										v-bind="deliveryState(row.delivery_status)"
										class="w-16 shrink-0 justify-center"
									/>
								</span>
							</span>
						</button>
					</li>
				</ul>
			</div>
		</section>
		<section
			class="min-w-0 flex-1 flex-col"
			:class="openThread || isComposing ? 'flex' : 'max-md:hidden md:flex'"
		>
			<template v-if="isComposing">
				<header class="flex h-12 shrink-0 items-center gap-2 border-b px-5">
					<Button
						class="md:hidden"
						icon="lucide-arrow-left"
						variant="ghost"
						:label="__('Back')"
						@click="stopComposing"
					/>
					<h2 class="text-lg-semibold">{{ __("New email") }}</h2>
				</header>
				<div class="flex-1 overflow-y-auto p-5">
					<EmailComposer @sent="onNewEmailSent" @discard="isComposing = false" />
				</div>
			</template>
			<template v-else-if="openThread">
				<header class="flex h-12 shrink-0 items-center gap-2 border-b px-5">
					<Button
						class="md:hidden"
						icon="lucide-arrow-left"
						variant="ghost"
						:label="__('Back')"
						@click="close"
					/>
					<h2 class="min-w-0 flex-1 truncate text-lg-semibold">{{ threadSubject }}</h2>
					<!-- A task would only open this same thread in its dialog, and an unlinked thread has no record. -->
					<Button
						v-if="!['Communication', 'Band Task'].includes(openThread.doctype)"
						variant="subtle"
						icon-right="lucide-arrow-up-right"
						:label="__('Open {0}', [__(openThread.doctype)])"
						:route="resultRoute(openThread)"
					/>
				</header>
				<div ref="pane" class="flex-1 overflow-y-auto px-5 pb-10 pt-5">
					<EmailThread
						:key="`${openThread.doctype}:${openThread.name}`"
						:doctype="openThread.doctype"
						:name="openThread.name"
						@loaded="onThreadLoaded"
					/>
				</div>
			</template>
			<div v-else class="flex flex-1 items-center justify-center p-6">
				<EmptyState
					icon="lucide-mail-open"
					:title="__('No email selected')"
					:description="__('Pick a conversation on the left, or move through them with J and K.')"
				/>
			</div>
		</section>
	</div>
</template>
