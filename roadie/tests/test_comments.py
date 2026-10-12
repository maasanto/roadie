import frappe
from frappe.desk.form.utils import add_comment
from frappe.tests import IntegrationTestCase
from frappe.utils import get_fullname

from roadie.api import get_comments, get_notifications
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
		self.assertEqual(notification.title, "John Doe mentioned you in a comment in Gig Acme Festival 2027")
		self.assertEqual(notification.description, "@Jane Doe & @John Doe can you book the van? Thanks!")
		self.assertTrue(notification.link.endswith(f"/roadie?gig={gig.name}"))
		self.assertFalse(notification.read)

		frappe.set_user(MEMBER)
		self.assertFalse([n for n in get_notifications() if n.document_name == gig.name])

	def test_comments_are_only_listed_for_band_records(self):
		frappe.set_user(MEMBER)
		with self.assertRaises(frappe.ValidationError):
			get_comments("User", MEMBER)
