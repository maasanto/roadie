<script setup>
import { ref } from "vue";
import { Button, ErrorMessage, toast, useCall } from "frappe-ui";
import { formatDate } from "../gig";
import { resultRoute } from "../search";

const props = defineProps({ pending: { type: Object, required: true } });

const answer = useCall({
	url: "/api/v2/method/roadie.api.answer_availability",
	method: "POST",
	immediate: false,
});
const answering = ref("");

async function reply(gig, value) {
	// A second submit on the same call would abort the first, leaving its answer unknown.
	if (answering.value) return;
	answering.value = `${gig.name}:${value}`;
	await answer.submit({ gig: gig.name, answer: value });
	answering.value = "";
	if (answer.error) {
		toast.error(answer.error.messages?.join("\n") || answer.error.message);
		return;
	}
	props.pending.reload();
}
</script>

<template>
	<!-- Above the screens rather than in their scroll, so it stays in view and full-height screens keep their height. -->
	<aside v-if="pending.data?.length" class="border-b bg-surface-amber-1" :aria-label="__('Availability')">
		<ul class="divide-y divide-outline-gray-1">
			<li
				v-for="gig in pending.data"
				:key="gig.name"
				class="flex flex-wrap items-center gap-2 px-6 py-2"
			>
				<span class="lucide-calendar-check size-4 text-ink-gray-6" aria-hidden="true" />
				<router-link
					:to="resultRoute({ doctype: 'Gig', name: gig.name })"
					class="min-w-0 flex-1 text-base text-ink-gray-8 underline-offset-2 hover:underline"
				>
					{{ __("Can you play {0} on {1}?", [gig.title, formatDate(gig.gig_date)]) }}
				</router-link>
				<Button
					icon-left="lucide-check"
					:label="__('Yes')"
					:loading="answering === `${gig.name}:Yes`"
					:disabled="Boolean(answering) && answering !== `${gig.name}:Yes`"
					@click="reply(gig, 'Yes')"
				/>
				<Button
					icon-left="lucide-x"
					:label="__('No')"
					:loading="answering === `${gig.name}:No`"
					:disabled="Boolean(answering) && answering !== `${gig.name}:No`"
					@click="reply(gig, 'No')"
				/>
			</li>
		</ul>
	</aside>
	<ErrorMessage v-else-if="pending.error" class="border-b px-6 py-2" :message="pending.error" />
</template>
