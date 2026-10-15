<script>
import { computed, ref, watch } from "vue";

// Module scope: a delete still waiting on its toast must outlive this screen, which remounts on every switch
// between Inbox and Outbox. A thread stays hidden once deleted, its key never comes back.
const deletedKeys = ref(new Set());
</script>

<script setup>
import { useRoute, useRouter } from "vue-router";
import { Avatar, Badge, Button, ErrorMessage, FormControl, Tooltip, call, toast, useCall } from "frappe-ui";
import EmailComposer from "../components/EmailComposer.vue";
import EmailThread from "../components/EmailThread.vue";
import EmptyState from "../components/EmptyState.vue";
import ListSkeleton from "../components/ListSkeleton.vue";
import SearchPalette from "../components/SearchPalette.vue";
import { directoryTypes } from "../directory";
import { confirmDiscardDraft, hasEditedDraft } from "../draft";
import { deliveryState, formatListDate, isUnread } from "../email";
import { onKey, onShortcut } from "../keyboard";
import { refreshWhileVisible, unreadEmailCount } from "../mailbox";
import { resultRoute } from "../search";
import { toastWithUndo } from "../undo";

const props = defineProps({
	sentOrReceived: { type: String, required: true },
});
const isInbox = computed(() => props.sentOrReceived === "Received");
const route = useRoute();
const router = useRouter();

const EMAILS_PER_PAGE = 200;
const query = ref("");
const emailLimit = ref(EMAILS_PER_PAGE);
watch(query, () => (emailLimit.value = EMAILS_PER_PAGE));
// What the listed rows answer. It trails the search box and the limit while their request is on its way.
const loaded = ref({ query: "", limit: EMAILS_PER_PAGE });

const mailbox = useCall({
	url: "/api/v2/method/roadie.api.get_mailbox",
	params: () => ({ sent_or_received: props.sentOrReceived, query: query.value, limit: emailLimit.value }),
	refetch: true,
	onSuccess: () => {
		loaded.value = { query: query.value, limit: emailLimit.value };
		// Alongside the list, so the badge never disagrees with the rows the member is looking at.
		if (isInbox.value) unreadEmailCount.reload();
	},
});
// A search or a Load more aborts the request in flight, and frappe-ui reports that abort as the mailbox's error.
const loadError = computed(() =>
	mailbox.loading || mailbox.error?.name === "AbortError" ? null : mailbox.error
);
// Every email read counts in exactly one thread, so threads adding up to the limit mean older emails are left.
const hasOlderEmails = computed(
	() => (mailbox.data || []).reduce((emails, row) => emails + row.count, 0) >= loaded.value.limit
);

refreshWhileVisible(() => mailbox.reload());

const isUnreadOnly = ref(false);
const isComposing = ref(false);
const openThread = computed(() =>
	route.params.doctype ? { doctype: route.params.doctype, name: route.params.name } : null
);
const threadKey = (thread) => `${thread.doctype}:${thread.name}`;
const isOpen = (row) => Boolean(openThread.value) && threadKey(row.thread) === threadKey(openThread.value);
// The open thread stays listed once read, or it would vanish under the reader and j/k would lose their place.
const rows = computed(() =>
	(mailbox.data || []).filter(
		(row) =>
			!deletedKeys.value.has(threadKey(row.thread)) &&
			(!isUnreadOnly.value || row.unread || isOpen(row))
	)
);

// frappe-ui's Checkbox reports no shift key, which range selection needs, so a native one wears its classes.
const CHECKBOX_CLASS =
	"size-3.5 rounded-sm border-outline-gray-4 bg-surface-base text-ink-gray-9 hover:border-outline-gray-7 focus:ring-0 focus:ring-offset-0";
const selectedKeys = ref(new Set());
const isSelected = (row) => selectedKeys.value.has(threadKey(row.thread));
const selectedRows = computed(() => rows.value.filter(isSelected));
const isEveryRowSelected = computed(() => selectedRows.value.length === rows.value.length);
// A gig's or a venue's mail is deleted one email at a time, from the thread, never in bulk.
const canDeleteSelection = computed(() =>
	selectedRows.value.every((row) => row.thread.doctype === "Communication" && !row.holds_filed_mail)
);
let selectionAnchor = null;

function toggleSelection(row, event) {
	const index = rows.value.indexOf(row);
	const anchor = rows.value.findIndex((each) => threadKey(each.thread) === selectionAnchor);
	const range =
		event.shiftKey && anchor !== -1
			? rows.value.slice(Math.min(anchor, index), Math.max(anchor, index) + 1)
			: [row];
	const isSelecting = !isSelected(row);
	const next = new Set(selectedKeys.value);
	for (const each of range) {
		if (isSelecting) next.add(threadKey(each.thread));
		else next.delete(threadKey(each.thread));
	}
	selectedKeys.value = next;
	selectionAnchor = threadKey(row.thread);
}

const clearSelection = () => (selectedKeys.value = new Set());
// A selection the search hides would come back with the next search and be acted on unseen.
watch(query, clearSelection);

function toggleEveryRow() {
	selectedKeys.value = isEveryRowSelected.value
		? new Set()
		: new Set(rows.value.map((row) => threadKey(row.thread)));
}

const showError = (error) => toast.error(error.messages?.join("\n") || error.message);

// One request per action: a shared useCall would abort the previous one, opening a thread included.
async function changeSeen(method, args) {
	try {
		await call(`roadie.api.${method}`, args);
	} catch (error) {
		showError(error);
	}
	mailbox.reload();
}

function markSelection(method) {
	changeSeen(method, { threads: selectedRows.value.map((row) => row.thread) });
	clearSelection();
}

async function deleteSelection() {
	const threads = selectedRows.value.map((row) => row.thread);
	const keys = threads.map(threadKey);
	// A refused close is a kept draft, whose thread must not be deleted from under it.
	if (selectedRows.value.some(isOpen) && (await close())) return;
	keys.forEach((key) => deletedKeys.value.add(key));
	clearSelection();
	toastWithUndo(
		threads.length === 1 ? __("Conversation deleted") : __("{0} conversations deleted", [threads.length]),
		{
			undo: () => keys.forEach((key) => deletedKeys.value.delete(key)),
			commit: () => deleteForGood(threads),
		}
	);
}

async function deleteForGood(threads) {
	try {
		await call("roadie.api.delete_threads", { names: threads.map(({ name }) => name) });
	} catch (error) {
		showError(error);
		threads.forEach((thread) => deletedKeys.value.delete(threadKey(thread)));
	}
	mailbox.reload();
}

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
let scrolledThreadKey = null;

function onThreadLoaded(thread) {
	threadSubject.value = thread.at(-1)?.subject || threadSubject.value;
	if (isInbox.value && thread.some(isUnread)) changeSeen("mark_thread_seen", openThread.value);
	// Once per thread: the reload after a reply or a delete leaves the reader where they were.
	if (scrolledThreadKey === threadKey(openThread.value)) return;
	scrolledThreadKey = threadKey(openThread.value);
	pane.value?.querySelector("[data-email]:last-child")?.scrollIntoView({ block: "start" });
}

// A thread reopened after the pane closed is a fresh pane, which should land on its latest email again.
watch(openThread, (thread) => {
	if (!thread) scrolledThreadKey = null;
});

// Deleting the email an unlinked conversation is keyed on hands the conversation to the next one. Each such move
// is remembered: a second delete queued before the first landed still reports the conversation's old key.
const movedThreads = new Map();

// The delete lands once its toast closes, by which time the reader may have opened another thread.
function onEmailDeleted({ thread, name, promoted, remaining }) {
	mailbox.reload();
	let key = threadKey(thread);
	while (movedThreads.has(key)) key = movedThreads.get(key);
	if (!openThread.value || key !== threadKey(openThread.value)) return;
	if (!remaining) return close();
	if (!promoted || openThread.value.name !== name) return;
	movedThreads.set(key, threadKey({ doctype: "Communication", name: promoted }));
	scrolledThreadKey = movedThreads.get(key);
	router.replace({ name: route.name, params: { doctype: "Communication", name: promoted } });
}

function step(offset) {
	const index = rows.value.findIndex(isOpen);
	const next = index === -1 ? rows.value[0] : rows.value[index + offset];
	if (next) open(next);
}

const LINKABLE_DOCTYPES = ["Gig", ...directoryTypes.map((type) => type.doctype)];
const recordPicker = ref(null);

function pickRecord() {
	if (hasEditedDraft()) return toast.error(__("Send or discard your email first."));
	recordPicker.value.open();
}

async function fileThreadUnder(record) {
	const communication = openThread.value.name;
	try {
		await call("roadie.api.link_thread", { communication, doctype: record.doctype, name: record.name });
	} catch (error) {
		showError(error);
		return;
	}
	toast.success(__("Filed under {0}", [record.title]));
	mailbox.reload();
	// The member may have moved on while the thread was being filed.
	if (openThread.value?.name === communication)
		router.replace({ name: route.name, params: { doctype: record.doctype, name: record.name } });
}

// No arrow keys: they scroll the reading pane. And no modifier, which would steal Ctrl+J and the like.
onShortcut({ key: "j" }, () => step(1));
onShortcut({ key: "k" }, () => step(-1));
onShortcut({ key: "x" }, () => {
	const row = rows.value.find(isOpen);
	if (row) toggleSelection(row, {});
});
onKey("Escape", close);
</script>

<template>
	<div class="flex h-full">
		<section
			class="flex min-w-0 flex-1 flex-col md:max-w-md md:border-r"
			:class="{ 'max-md:hidden': openThread || isComposing }"
		>
			<header v-if="selectedRows.length" class="flex h-12 shrink-0 items-center gap-1 px-4">
				<input
					type="checkbox"
					:class="CHECKBOX_CLASS"
					:checked="isEveryRowSelected"
					:indeterminate="!isEveryRowSelected"
					:aria-label="__('Select all')"
					@click="toggleEveryRow"
				/>
				<span class="ml-2 flex-1 text-base-medium text-ink-gray-8">
					{{ __("{0} selected", [selectedRows.length]) }}
				</span>
				<template v-if="isInbox">
					<Button
						icon="lucide-mail-open"
						variant="ghost"
						:label="__('Mark as read')"
						:tooltip="__('Mark as read')"
						@click="markSelection('mark_threads_read')"
					/>
					<Button
						icon="lucide-mail"
						variant="ghost"
						:label="__('Mark as unread')"
						:tooltip="__('Mark as unread')"
						@click="markSelection('mark_threads_unread')"
					/>
				</template>
				<!-- A disabled button fires no hover, so the tooltip hangs on a wrapper. -->
				<Tooltip
					:text="
						canDeleteSelection
							? __('Delete')
							: __(
									'Only conversations linked to no gig, task or directory entry can be deleted together'
							  )
					"
				>
					<span>
						<Button
							icon="lucide-trash-2"
							variant="ghost"
							:label="__('Delete')"
							:disabled="!canDeleteSelection"
							@click="deleteSelection"
						/>
					</span>
				</Tooltip>
				<Button
					icon="lucide-x"
					variant="ghost"
					:label="__('Clear selection')"
					@click="clearSelection"
				/>
			</header>
			<header v-else class="flex h-12 shrink-0 items-center gap-2 px-4">
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
			<div class="px-4 pb-3">
				<FormControl
					v-model="query"
					type="search"
					:debounce="300"
					:placeholder="__('Search subject, sender or recipient')"
					:aria-label="__('Search subject, sender or recipient')"
				/>
			</div>
			<div ref="list" class="flex-1 overflow-y-auto border-t">
				<ListSkeleton v-if="mailbox.loading && !mailbox.data" class="m-4" />
				<ErrorMessage v-else-if="loadError" class="m-4" :message="loadError" />
				<EmptyState
					v-else-if="loaded.query && !mailbox.data?.length"
					class="m-4"
					icon="lucide-search-x"
					:title="__('No emails match “{0}”', [loaded.query])"
				>
					<Button icon-left="lucide-x" :label="__('Clear search')" @click="query = ''" />
				</EmptyState>
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
					<Button :label="__('Open the gigs')" route="/" />
				</EmptyState>
				<p v-else-if="!rows.length && isUnreadOnly" class="m-4 text-p-sm text-ink-gray-5">
					{{ __("No unread emails.") }}
				</p>
				<ul v-else class="divide-y divide-outline-gray-1">
					<li
						v-for="row in rows"
						:key="threadKey(row.thread)"
						class="group flex items-start hover:bg-surface-gray-2"
						:class="{ 'bg-surface-gray-2': isOpen(row) || isSelected(row) }"
					>
						<label class="flex shrink-0 cursor-pointer items-start gap-3 py-3 pl-4">
							<span
								class="mt-3 size-2 shrink-0 rounded-full"
								:class="isInbox && row.unread ? 'bg-surface-blue-7' : 'bg-transparent'"
								:aria-label="isInbox && row.unread ? __('Unread') : undefined"
							/>
							<span class="grid size-8 place-items-center">
								<Avatar
									:class="selectedRows.length ? 'hidden' : 'group-hover:hidden'"
									:label="isInbox ? row.sender_full_name || row.sender : row.recipients"
									size="md"
								/>
								<input
									type="checkbox"
									:class="[
										CHECKBOX_CLASS,
										selectedRows.length ? '' : 'hidden group-hover:block',
									]"
									:checked="isSelected(row)"
									:aria-label="__('Select {0}', [row.subject])"
									@click="toggleSelection(row, $event)"
								/>
							</span>
						</label>
						<button
							class="flex min-w-0 flex-1 items-start py-3 pl-3 pr-4 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-outline-gray-3"
							:aria-current="isOpen(row) || undefined"
							@click="open(row)"
						>
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
				<div v-if="hasOlderEmails" class="flex justify-center p-4">
					<Button
						:label="__('Load more')"
						:loading="mailbox.loading && emailLimit > loaded.limit"
						@click="emailLimit += EMAILS_PER_PAGE"
					/>
				</div>
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
					<Button
						v-if="openThread.doctype === 'Communication'"
						variant="subtle"
						icon-left="lucide-link"
						:label="__('Link to…')"
						@click="pickRecord"
					/>
					<!-- A task would only open this same thread in its dialog. -->
					<Button
						v-else-if="openThread.doctype !== 'Band Task'"
						variant="subtle"
						icon-right="lucide-arrow-up-right"
						:label="__('Open {0}', [__(openThread.doctype)])"
						:route="resultRoute(openThread)"
					/>
				</header>
				<div ref="pane" class="flex-1 overflow-y-auto px-5 pb-10 pt-5">
					<EmailThread
						:key="threadKey(openThread)"
						:doctype="openThread.doctype"
						:name="openThread.name"
						@loaded="onThreadLoaded"
						@deleted="onEmailDeleted"
					/>
				</div>
				<SearchPalette
					ref="recordPicker"
					:doctypes="LINKABLE_DOCTYPES"
					:placeholder="__('Search the gig or directory entry to file this thread under')"
					@select="fileThreadUnder"
				/>
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
