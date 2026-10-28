from unittest.mock import patch

import frappe
from frappe.desk.form.utils import add_comment
from frappe.tests import IntegrationTestCase
from frappe.utils import get_fullname

from roadie.api import (
	are_mention_emails_enabled,
	get_comments,
	get_notifications,
	set_mention_emails_enabled,
)
from roadie.roadie.doctype.gig.test_gig import MEMBER, make_member

BANDMATE = "jane@example.com"
FESTIVAL_CONTACT = "booking@example.com"


class TestComments(IntegrationTestCase):
	def setUp(self):
		make_member(MEMBER, "John")
		make_member(BANDMATE, "Jane")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_mention_on_a_festival_notifies_the_bandmate_and_emails_no_contact(self):
		frappe.set_user(MEMBER)
		festival = frappe.get_doc({"doctype": "Festival", "title": "Acme Festival"}).insert()
		frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "Bob",
				"email_ids": [{"email_id": FESTIVAL_CONTACT, "is_primary": 1}],
				"links": [{"link_doctype": "Festival", "link_name": festival.name}],
			}
		).insert()
		content = (
			f'<p><span class="mention" data-type="mention" data-id="{BANDMATE}" data-label="Jane Doe">@Jane Doe</span>'
			" can you call them about the deadline?</p>"
		)
		comment = add_comment("Festival", festival.name, content, "mallory@example.com", "Mallory")

		frappe.set_user(BANDMATE)
		[shown] = get_comments("Festival", festival.name)
		self.assertEqual(shown.name, comment.name)
		self.assertEqual((shown.comment_email, shown.comment_by), (MEMBER, get_fullname(MEMBER)))
		notification = frappe.db.get_value(
			"Notification Log",
			{
				"for_user": BANDMATE,
				"type": "Mention",
				"document_type": "Festival",
				"document_name": festival.name,
			},
			["from_user", "link"],
			as_dict=True,
		)
		self.assertEqual(notification.from_user, MEMBER)
		self.assertTrue(
			notification.link.endswith(f"/roadie/directory/festivals?entry=Festival:{festival.name}")
		)
		self.assertFalse(frappe.db.exists("Email Queue Recipient", {"recipient": FESTIVAL_CONTACT}))

	def test_a_member_who_turns_off_mention_emails_is_still_notified_in_app(self):
		frappe.set_user(BANDMATE)
		set_mention_emails_enabled(False)
		self.assertFalse(are_mention_emails_enabled())

		frappe.set_user(MEMBER)
		gig = frappe.get_doc({"doctype": "Gig", "title": "Acme Festival 2027"}).insert()
		self.assertEqual(self.emails_sent_by_mentioning_bandmate(gig), 0)
		self.assertTrue(
			frappe.db.exists(
				"Notification Log", {"for_user": BANDMATE, "type": "Mention", "document_name": gig.name}
			)
		)

		frappe.set_user(BANDMATE)
		set_mention_emails_enabled(True)
		self.assertTrue(are_mention_emails_enabled())

		frappe.set_user(MEMBER)
		self.assertEqual(self.emails_sent_by_mentioning_bandmate(gig), 1)

	def test_mention_emails_alone_come_back_when_every_email_was_off(self):
		frappe.set_user(BANDMATE)
		set_mention_emails_enabled(False)
		frappe.db.set_value("Notification Settings", BANDMATE, "enable_email_notifications", 0)

		set_mention_emails_enabled(True)

		settings = frappe.get_doc("Notification Settings", BANDMATE)
		self.assertTrue(settings.enable_email_notifications)
		self.assertEqual([row.notification_type for row in settings.email_notification_types], ["Mention"])

	def emails_sent_by_mentioning_bandmate(self, gig):
		# In tests the notification email goes out synchronously, and a test site has no outgoing account.
		with patch(
			"frappe.desk.doctype.notification_log.notification_log.send_notification_email"
		) as send_email:
			add_comment(
				"Gig",
				gig.name,
				f'<p><span class="mention" data-type="mention" data-id="{BANDMATE}" data-label="Jane Doe">@Jane Doe</span>'
				" can you book the van?</p>",
				MEMBER,
				"John Doe",
			)
		return len([call for call in send_email.call_args_list if call.args[0].for_user == BANDMATE])

	def test_mentioned_member_sees_the_comment_in_their_panel_and_the_author_gets_nothing(self):
		frappe.set_user(MEMBER)
		gig = frappe.get_doc({"doctype": "Gig", "title": "Acme Festival 2027"}).insert()
		add_comment(
			"Gig",
			gig.name,
			f'<p><span class="mention" data-type="mention" data-id="{BANDMATE}" data-label="Jane Doe">@Jane Doe</span>'
			f' &amp; <span class="mention" data-type="mention" data-id="{MEMBER}" data-label="John Doe">@John Doe</span>'
			" can you book the van?</p><p>Thanks!</p>",
			MEMBER,
			"John Doe",
		)

		frappe.set_user(BANDMATE)
		[notification] = [n for n in get_notifications() if n.document_name == gig.name]
		self.assertEqual(notification.type, "Mention")
		self.assertEqual(
			notification.title,
			"<strong>John Doe</strong> mentioned you in a comment in <strong>Gig</strong> <b>Acme Festival 2027</b>",
		)
		self.assertEqual(notification.from_user_name, "John Doe")
		self.assertEqual(notification.description, "@Jane Doe & @John Doe can you book the van? Thanks!")
		self.assertTrue(notification.link.endswith(f"/roadie?gig={gig.name}"))
		self.assertFalse(notification.read)

		frappe.set_user(MEMBER)
		self.assertFalse([n for n in get_notifications() if n.document_name == gig.name])

	def test_comments_are_only_listed_for_band_records(self):
		frappe.set_user(MEMBER)
		with self.assertRaises(frappe.ValidationError):
			get_comments("User", MEMBER)
