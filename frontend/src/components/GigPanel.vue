<script setup>
import { computed, ref } from "vue";
import { Button, call, toast } from "frappe-ui";
import CommentThread from "./CommentThread.vue";
import EmailThread from "./EmailThread.vue";
import EntryForm from "./EntryForm.vue";
import GigAttachments from "./GigAttachments.vue";
import GigAvailability from "./GigAvailability.vue";
import GigTasks from "./GigTasks.vue";
import { confirmBooking } from "../availability";
import { confirmDiscardDraft } from "../draft";
import { isUnread } from "../email";
import { onKey } from "../keyboard";

const props = defineProps({
	name: { type: String, default: null },
	controls: { type: Object, required: true },
	// A callback rather than an event: marking the mail seen can land after the panel closed, and Vue drops events
	// from an unmounted component.
	onMailSeen: { type: Function, default: null },
});
const emit = defineEmits(["close", "saved"]);

const entryForm = ref(null);
// A gig created here never reaches the address, so the panel is what knows which gig it shows.
defineExpose({ entryName: computed(() => entryForm.value?.entryName) });

const availability = ref(null);

const confirmSave = (values) =>
	values.status !== "Booked" ||
	confirmBooking(entryForm.value.form.title, availability.value?.rows, availability.value?.members.data);

// A new date sends the band's answers back to pending, the member's own included.
function onSaved() {
	availability.value?.reload();
	emit("saved");
}

function close() {
	if (confirmDiscardDraft()) emit("close");
}

onKey("Escape", close);

// As the Inbox does, or the board's unread badge would outlive the member reading the mail here.
async function markSeen(gig, thread) {
	if (!thread.some(isUnread)) return;
	try {
		await call("roadie.api.mark_thread_seen", { doctype: "Gig", name: gig });
		props.onMailSeen?.();
	} catch (error) {
		toast.error(error.messages?.join("\n") || error.message);
	}
}
</script>

<template>
	<aside
		class="fixed inset-y-0 right-0 z-20 flex w-[34rem] max-w-full flex-col border-l bg-surface-base shadow-xl"
	>
		<header class="flex min-h-12 items-center justify-between gap-2 border-b px-5">
			<h2 class="truncate text-lg-semibold">
				{{ entryForm?.entryName ? entryForm.form.title || __("Gig") : __("New gig") }}
			</h2>
			<Button icon="lucide-x" variant="ghost" :label="__('Close')" @click="close" />
		</header>
		<div class="flex-1 overflow-y-auto px-5 pb-10 pt-5">
			<EntryForm
				:key="name"
				ref="entryForm"
				doctype="Gig"
				:name="name"
				:controls="controls"
				:confirm-save="confirmSave"
				@saved="onSaved"
			>
				<template #default="{ entryName }">
					<GigAvailability ref="availability" :gig="entryName" />
					<GigTasks :gig="entryName" @saved="emit('saved')" />
					<GigAttachments :gig="entryName" />
					<CommentThread doctype="Gig" :name="entryName" />
					<EmailThread doctype="Gig" :name="entryName" @loaded="markSeen(entryName, $event)" />
				</template>
			</EntryForm>
		</div>
	</aside>
</template>
