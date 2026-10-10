<script setup>
import { computed, ref } from "vue";
import { Avatar, Button, ErrorMessage, TextEditor, useCall } from "frappe-ui";
import { formatDateTime } from "../email";

const props = defineProps({
	doctype: { type: String, required: true },
	name: { type: String, required: true },
});

const comments = useCall({
	url: "/api/v2/method/roadie.api.get_comments",
	params: () => ({ doctype: props.doctype, name: props.name }),
});
const members = useCall({ url: "/api/v2/method/roadie.api.get_members" });
const membersByEmail = computed(() => Object.fromEntries((members.data || []).map((member) => [member.name, member])));
const mentions = computed(() => (members.data || []).map((member) => ({ label: member.full_name, value: member.name })));

const draft = ref("");
const editorKey = ref(0);
const isDraftEmpty = computed(() => !draft.value.replace(/<[^>]*>/g, "").trim());

const post = useCall({
	url: "/api/v2/method/frappe.desk.form.utils.add_comment",
	method: "POST",
	immediate: false,
	onSuccess: () => {
		draft.value = "";
		editorKey.value++;
		comments.reload();
	},
});

function submit() {
	post.submit({
		reference_doctype: props.doctype,
		reference_name: props.name,
		content: draft.value,
		comment_email: window.user,
		comment_by: membersByEmail.value[window.user]?.full_name || window.user,
	});
}
</script>

<template>
	<section>
		<h2 class="text-lg-semibold">{{ __("Comments") }}</h2>
		<p class="text-p-sm text-ink-gray-5">{{ __("Internal to the band, never emailed. Type @ to mention a bandmate.") }}</p>
		<ul v-if="comments.data?.length" class="mt-3 space-y-3">
			<li v-for="comment in comments.data" :key="comment.name" class="flex items-start gap-2">
				<Avatar
					:label="comment.comment_by || comment.comment_email"
					:image="membersByEmail[comment.comment_email]?.user_image"
					size="md"
				/>
				<div class="min-w-0 flex-1 rounded-6 bg-surface-amber-1 px-3 py-2">
					<p class="flex items-baseline justify-between gap-2">
						<span class="truncate text-base-medium text-ink-gray-8">{{ comment.comment_by || comment.comment_email }}</span>
						<span class="shrink-0 text-sm text-ink-gray-5">{{ formatDateTime(comment.creation) }}</span>
					</p>
					<TextEditor :content="comment.content" :editable="false" :mentions="mentions" editor-class="prose-sm max-w-none" />
				</div>
			</li>
		</ul>
		<p v-else-if="comments.isFinished" class="mt-3 text-p-sm text-ink-gray-5">{{ __("No comments yet.") }}</p>
		<ErrorMessage class="mt-2" :message="comments.error" />
		<form v-if="members.data" data-draft class="mt-3 rounded-6 border border-outline-gray-2 px-3 pb-2" @submit.prevent="submit">
			<TextEditor
				:key="editorKey"
				:content="draft"
				:mentions="mentions"
				:placeholder="__('Write a comment…')"
				editor-class="prose-sm max-w-none min-h-16 py-2"
				@change="draft = $event"
			/>
			<ErrorMessage class="mt-1" :message="post.error" />
			<div class="flex justify-end">
				<Button type="submit" variant="solid" :label="__('Comment')" :loading="post.loading" :disabled="isDraftEmpty" />
			</div>
		</form>
	</section>
</template>

<style scoped>
:deep(.mention) {
	@apply rounded bg-surface-amber-3 px-0.5 font-medium text-ink-gray-9;
}
</style>
