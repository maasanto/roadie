import email
import re
from unittest.mock import patch

import frappe
from frappe.core.api.user_invitation import (
	_accept_invitation,
	cancel_invitation,
	get_pending_invitations,
	invite_by_email,
)
from frappe.tests import IntegrationTestCase

from roadie.roadie.doctype.gig.test_gig import MEMBER, make_member
from roadie.tests.test_email import shared_mailbox

INVITEE = "jane.doe@example.com"
OUTSIDER = "joe.doe@example.com"


def invite(address, roles=("Band Member",), redirect_to_path="/roadie"):
	return invite_by_email(address, list(roles), redirect_to_path, "roadie")


def emailed_invitation_key(recipient):
	[queued] = frappe.get_all(
		"Email Queue",
		filters=[["Email Queue Recipient", "recipient", "=", recipient]],
		fields=["message"],
		order_by="creation desc",
		limit=1,
	)
	html = next(
		part.get_payload(decode=True).decode()
		for part in email.message_from_string(queued.message).walk()
		if part.get_content_type() == "text/html"
	)
	return re.search(r"accept_invitation\?key=(\w+)", html).group(1)


class TestInvitations(IntegrationTestCase):
	def setUp(self):
		# Accepting commits, which would leave the invitee and the test mailbox on the site.
		self.enterContext(patch.object(frappe.db, "commit"))
		shared_mailbox()
		make_member(MEMBER, "John")
		frappe.db.delete("User Invitation", {"email": INVITEE})
		frappe.delete_doc_if_exists("User", INVITEE, force=True)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_member_invites_someone_who_joins_as_a_member(self):
		frappe.set_user(MEMBER)
		self.assertEqual(invite(INVITEE)["invited_emails"], [INVITEE])

		frappe.set_user("Guest")
		_accept_invitation(emailed_invitation_key(INVITEE), True)

		self.assertIn("/update-password?key=", frappe.local.response.location)
		self.assertTrue(frappe.local.response.location.endswith("&redirect_to=/roadie"))
		self.assertIn("Band Member", frappe.get_roles(INVITEE))
		self.assertTrue(frappe.has_permission("Gig", "read", user=INVITEE))
		# Frappe creates invitees as System Users; a member must still never reach Desk.
		self.assertEqual(frappe.db.get_value("User", INVITEE, "user_type"), "Website User")

	def test_an_invitee_always_lands_on_roadie(self):
		frappe.set_user(MEMBER)
		invite(INVITEE, redirect_to_path="https://phishing.example.com/login")

		self.assertEqual(
			frappe.db.get_value("User Invitation", {"email": INVITEE}, "redirect_to_path"), "/roadie"
		)

	def test_member_sees_and_cancels_a_pending_invitation(self):
		frappe.set_user(MEMBER)
		invite(INVITEE)
		[pending] = [row for row in get_pending_invitations("roadie") if row["email"] == INVITEE]

		self.assertTrue(cancel_invitation(pending["name"], "roadie")["cancelled_now"])
		self.assertNotIn(INVITEE, [row["email"] for row in get_pending_invitations("roadie")])

	def test_member_cannot_hand_out_another_role(self):
		frappe.set_user(MEMBER)
		with self.assertRaises(frappe.ValidationError):
			invite(INVITEE, roles=["System Manager"])

	def test_only_members_can_invite(self):
		make_member(OUTSIDER, "Joe")
		frappe.get_doc("User", OUTSIDER).remove_roles("Band Member")
		frappe.set_user(OUTSIDER)
		with self.assertRaises(frappe.PermissionError):
			invite(INVITEE)
