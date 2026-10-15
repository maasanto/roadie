<script setup>
import { ref } from "vue";
import { Avatar, Badge, Button, ErrorMessage, FormControl, toast, useCall } from "frappe-ui";
import { user } from "../user";

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

const grantDrive = useCall({
	url: "/api/v2/method/roadie.api.grant_drive_access",
	method: "POST",
	immediate: false,
});
const grantingMember = ref("");

const setManager = useCall({
	url: "/api/v2/method/roadie.api.set_band_manager",
	method: "POST",
	immediate: false,
});

const managerHint = __("Managers aren't asked whether they can play a gig");
const inviteManagerLabel = __("Invite as a manager, who isn't asked whether they can play a gig");

const savingManager = ref("");

async function toggleManager(member, isManager) {
	// frappe-ui's checkbox emits every change twice, and any second submit would abort the first.
	if (savingManager.value) return;
	savingManager.value = member.name;
	await setManager.submit({ member: member.name, is_manager: isManager });
	savingManager.value = "";
	if (!setManager.error) member.is_manager = isManager;
}

const email = ref("");
const isInvitingManager = ref(false);
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
		roles: isInvitingManager.value ? ["Band Member", "Band Manager"] : ["Band Member"],
		redirect_to_path: "/roadie",
		app_name: APP_NAME,
	});
	if (invite.error) return;
	if (result.invited_emails.length) {
		toast.success(__("Invitation sent to {0}", [address]));
		email.value = "";
		isInvitingManager.value = false;
		invitations.reload();
	} else if (result.pending_invite_emails.length) {
		notInvited.value = __("{0} is already invited", [address]);
	} else if (result.disabled_user_emails.length) {
		notInvited.value = __("{0} has a disabled account", [address]);
	} else {
		notInvited.value = __("{0} already accepted an invitation", [address]);
	}
}

async function grantDriveAccess(member) {
	grantingMember.value = member.name;
	await grantDrive.submit({ member: member.name });
	grantingMember.value = "";
	if (grantDrive.error) return;
	// The page boot decides whether the sidebar links to Drive, so a member granting themselves needs a fresh one.
	if (member.name === user.name) {
		window.location.reload();
		return;
	}
	toast.success(__("{0} can now open Drive", [member.full_name]));
	members.reload();
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
				<FormControl
					type="checkbox"
					:label="__('Manager')"
					:title="managerHint"
					:model-value="member.is_manager"
					:disabled="Boolean(savingManager)"
					@update:model-value="toggleManager(member, $event)"
				/>
				<Button
					v-if="member.has_drive_access === false"
					icon-left="lucide-hard-drive"
					:label="__('Give Drive access')"
					:loading="grantingMember === member.name"
					@click="grantDriveAccess(member)"
				/>
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
		<ErrorMessage
			class="mt-2"
			:message="
				members.error ||
				invitations.error ||
				cancelInvitation.error ||
				grantDrive.error ||
				setManager.error
			"
		/>
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
		<FormControl v-model="isInvitingManager" class="mt-2" type="checkbox" :label="inviteManagerLabel" />
		<ErrorMessage class="mt-2" :message="notInvited || invite.error" />
		<p class="mt-2 text-p-sm text-ink-gray-5">
			{{ __("They get an email with a link to join the band.") }}
		</p>
	</section>
</template>
