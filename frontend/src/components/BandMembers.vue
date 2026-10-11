<script setup>
import { ref } from "vue";
import { Avatar, Badge, Button, ErrorMessage, FormControl, toast, useCall } from "frappe-ui";

// Frappe's own User Invitation flow; roadie's `user_invitation` hook decides who may invite and with which role.
const INVITATION_API = "/api/v2/method/frappe.core.api.user_invitation";
const APP_NAME = "roadie";

const members = useCall({ url: "/api/v2/method/roadie.api.get_members" });
const invitations = useCall({
	url: `${INVITATION_API}.get_pending_invitations`,
	params: { app_name: APP_NAME },
});
const invite = useCall({ url: `${INVITATION_API}.invite_by_email`, method: "POST", immediate: false });
const cancelInvitation = useCall({
	url: `${INVITATION_API}.cancel_invitation`,
	method: "POST",
	immediate: false,
});

const email = ref("");
const notInvited = ref("");

async function sendInvitation() {
	// Frappe matches pending and accepted invitations case-sensitively, so it would miss "Jane@example.com".
	const address = email.value.trim().toLowerCase();
	notInvited.value = "";
	// Frappe only knows members who joined through an invitation, so it would invite earlier ones again.
	if (members.data?.some((member) => member.name === address)) {
		notInvited.value = __("{0} is already a member", [address]);
		return;
	}
	const result = await invite.submit({
		emails: address,
		roles: ["Band Member"],
		redirect_to_path: "/roadie",
		app_name: APP_NAME,
	});
	if (invite.error) return;
	if (result.invited_emails.length) {
		toast.success(__("Invitation sent to {0}", [address]));
		email.value = "";
		invitations.reload();
	} else if (result.pending_invite_emails.length) {
		notInvited.value = __("{0} is already invited", [address]);
	} else if (result.disabled_user_emails.length) {
		notInvited.value = __("{0} has a disabled account", [address]);
	} else {
		notInvited.value = __("{0} already accepted an invitation", [address]);
	}
}

async function cancel(invitation) {
	await cancelInvitation.submit({ name: invitation.name, app_name: APP_NAME });
	// Reloaded either way: a failed cancel usually means the invitation was accepted meanwhile.
	invitations.reload();
	if (!cancelInvitation.error) toast.success(__("Invitation to {0} cancelled", [invitation.email]));
}
</script>

<template>
	<section>
		<h2 class="text-lg-semibold">{{ __("Members") }}</h2>
		<ul class="mt-3 divide-y divide-outline-gray-1 rounded-6 border">
			<li v-for="member in members.data" :key="member.name" class="flex items-center gap-3 px-3 py-2">
				<Avatar :image="member.user_image" :label="member.full_name" size="sm" />
				<span class="min-w-0 flex-1 truncate text-base">{{ member.full_name }}</span>
				<span class="truncate text-sm text-ink-gray-5">{{ member.name }}</span>
			</li>
			<li
				v-for="invitation in invitations.data"
				:key="invitation.name"
				class="flex items-center gap-3 px-3 py-2"
			>
				<Avatar :label="invitation.email" size="sm" />
				<span class="min-w-0 flex-1 truncate text-base">{{ invitation.email }}</span>
				<Badge :label="__('Invited')" theme="orange" />
				<Button
					icon="lucide-x"
					variant="ghost"
					:label="__('Cancel invitation')"
					@click="cancel(invitation)"
				/>
			</li>
		</ul>
		<ErrorMessage class="mt-2" :message="members.error || invitations.error || cancelInvitation.error" />
		<form class="mt-3 flex items-end gap-2" @submit.prevent="sendInvitation">
			<FormControl
				v-model="email"
				class="flex-1"
				type="email"
				:label="__('Invite someone to the band')"
				placeholder="jane@example.com"
			/>
			<Button
				type="submit"
				icon-left="lucide-send"
				:label="__('Invite')"
				:disabled="!email"
				:loading="invite.loading"
			/>
		</form>
		<ErrorMessage class="mt-2" :message="notInvited || invite.error" />
		<p class="mt-2 text-p-sm text-ink-gray-5">
			{{ __("They get an email with a link to join the band.") }}
		</p>
	</section>
</template>
