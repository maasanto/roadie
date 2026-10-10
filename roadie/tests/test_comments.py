import frappe
from frappe.desk.form.utils import add_comment
from frappe.tests import IntegrationTestCase
from frappe.utils import get_fullname

from roadie.api import get_comments
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
		self.assertTrue(notification.link.endswith("/roadie/directory"))
		self.assertFalse(frappe.db.exists("Email Queue Recipient", {"recipient": FESTIVAL_CONTACT}))

	def test_comments_are_only_listed_for_band_records(self):
		frappe.set_user(MEMBER)
		with self.assertRaises(frappe.ValidationError):
			get_comments("User", MEMBER)
