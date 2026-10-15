<script setup>
import { computed, inject, ref } from "vue";
import { Avatar, Button, ErrorMessage, toast, useCall } from "frappe-ui";
import { availabilityState } from "../availability";

const props = defineProps({ gig: { type: String, required: true } });

const gigDoc = useCall({ url: computed(() => `/api/v2/document/Gig/${props.gig}`) });
const members = useCall({ url: "/api/v2/method/roadie.api.get_members" });
// The strip above every screen asks the same question, so it is read again with the gig.
const pending = inject("pendingAvailability", null);
function reload() {
	gigDoc.reload();
	pending?.reload();
}

const rows = computed(() => gigDoc.data?.availability || []);
const memberOf = (row) => members.data?.find((member) => member.name === row.member);
const user = window.user;
const myRow = computed(() => rows.value.find((row) => row.member === user));

const request = useCall({
	url: "/api/v2/method/roadie.api.request_availability",
	method: "POST",
	immediate: false,
});
const answer = useCall({
	url: "/api/v2/method/roadie.api.answer_availability",
	method: "POST",
	immediate: false,
});

async function askBand() {
	const isReminder = rows.value.length > 0;
	await request.submit({ gig: props.gig });
	if (request.error) return;
	toast.success(isReminder ? __("Reminder sent") : __("The band has been asked"));
	reload();
}

const answering = ref("");

async function reply(value) {
	// A second submit on the same call would abort the first, leaving its answer unknown.
	if (answering.value) return;
	answering.value = value;
	await answer.submit({ gig: props.gig, answer: value });
	answering.value = "";
	if (answer.error) return;
	reload();
}

defineExpose({ rows, members, reload });
</script>

<template>
	<section>
		<div class="flex items-center justify-between gap-2">
			<h2 class="text-lg-semibold">{{ __("Availability") }}</h2>
			<!-- A member is never reminded by their own Remind, so their own pending answer doesn't offer one. -->
			<Button
				v-if="!rows.length || rows.some((row) => !row.answer && row.member !== user)"
				:icon-left="rows.length ? 'lucide-bell-ring' : 'lucide-calendar-check'"
				:label="rows.length ? __('Remind') : __('Request availability')"
				:disabled="!gigDoc.data?.gig_date"
				:loading="request.loading"
				@click="askBand"
			/>
		</div>
		<p v-if="gigDoc.data && !gigDoc.data.gig_date" class="mt-2 text-p-sm text-ink-gray-5">
			{{ __("Set the gig date to ask the band whether they can play it.") }}
		</p>
		<p v-else-if="gigDoc.data && !rows.length" class="mt-2 text-p-sm text-ink-gray-5">
			{{ __("Ask the band whether they can play this date. Managers aren't asked.") }}
		</p>
		<ul v-if="rows.length" class="mt-3 divide-y divide-outline-gray-1 rounded-6 border">
			<li v-for="row in rows" :key="row.member" class="flex items-center gap-3 px-3 py-2">
				<Avatar
					:label="memberOf(row)?.full_name || row.member"
					:image="memberOf(row)?.user_image"
					size="sm"
				/>
				<span class="min-w-0 flex-1 truncate text-base">{{
					memberOf(row)?.full_name || row.member
				}}</span>
				<span class="flex items-center gap-1.5 text-sm text-ink-gray-6">
					<span
						class="size-2 rounded-full"
						:class="availabilityState(row.answer).dot"
						aria-hidden="true"
					/>
					{{ availabilityState(row.answer).label }}
				</span>
			</li>
		</ul>
		<div v-if="myRow && gigDoc.data?.gig_date" class="mt-3 flex flex-wrap items-center gap-2">
			<span class="flex-1 text-base text-ink-gray-7">{{ __("Can you play?") }}</span>
			<Button
				icon-left="lucide-check"
				:label="__('Yes')"
				:variant="myRow.answer === 'Yes' ? 'solid' : 'subtle'"
				:loading="answering === 'Yes'"
				:disabled="answering === 'No'"
				@click="reply('Yes')"
			/>
			<Button
				icon-left="lucide-x"
				:label="__('No')"
				:variant="myRow.answer === 'No' ? 'solid' : 'subtle'"
				:loading="answering === 'No'"
				:disabled="answering === 'Yes'"
				@click="reply('No')"
			/>
		</div>
		<ErrorMessage class="mt-2" :message="gigDoc.error || request.error || answer.error" />
	</section>
</template>
