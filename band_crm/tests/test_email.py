from email.message import EmailMessage

import frappe
from frappe.core.doctype.communication.email import make
from frappe.email.receive import InboundMail
from frappe.tests import IntegrationTestCase

from band_crm.api import get_emails, get_mailbox, mark_seen
from band_crm.band_crm.doctype.gig.test_gig import MEMBER, blank_pdf, make_member
from band_crm.install import grant_communication_access

MAILBOX = "band@example.com"
VENUE = "venue@example.com"


def shared_mailbox():
	if name := frappe.db.get_value("Email Account", {"email_id": MAILBOX}):
		return frappe.get_doc("Email Account", name)
	return frappe.get_doc(
		{
			"doctype": "Email Account",
			"email_account_name": "Band Mailbox Test",
			"email_id": MAILBOX,
			"enable_outgoing": 1,
			"default_outgoing": 1,
			"smtp_server": "localhost",
			"no_smtp_authentication": 1,
		}
	).insert(ignore_permissions=True)


def incoming_email(sender, subject, message_id):
	email = EmailMessage()
	email["From"] = sender
	email["To"] = MAILBOX
	email["Subject"] = subject
	email["Message-ID"] = f"<{message_id}@example.com>"
	email.set_content("Thanks, the tech sheet is attached.")
	return email


def venue_reply(sent, attachment_name=None):
	reply = incoming_email(f"Le Petit Club <{VENUE}>", f"Re: {sent.subject}", f"reply-{sent.name}")
	reply["In-Reply-To"] = f"<{sent.message_id}>"
	if attachment_name:
		reply.add_attachment(blank_pdf(), maintype="application", subtype="pdf", filename=attachment_name)
	return reply.as_string()


class TestEmail(IntegrationTestCase):
	def setUp(self):
		make_member(MEMBER, "John")
		grant_communication_access()
		self.mailbox = shared_mailbox()

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_sent_email_and_its_reply_thread_on_the_gig(self):
		frappe.set_user(MEMBER)
		gig = frappe.get_doc({"doctype": "Gig", "title": "Le Petit Club residency"}).insert()
		rider = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "rider.pdf",
				"content": blank_pdf(),
				"is_private": 1,
				"attached_to_doctype": "Gig",
				"attached_to_name": gig.name,
			}
		).insert()
		sent = make(
			doctype="Gig",
			name=gig.name,
			subject="Residency dates",
			content="<p>Our rider is attached.</p>",
			recipients=[VENUE],
			send_email=True,
			attachments=[rider.name],
		)

		frappe.set_user("Administrator")
		InboundMail(venue_reply(frappe.get_doc("Communication", sent["name"]), "tech-sheet.pdf"), self.mailbox).process()

		frappe.set_user(MEMBER)
		thread = get_emails("Gig", gig.name)

		self.assertEqual([email.sent_or_received for email in thread], ["Sent", "Received"])
		self.assertEqual([file.file_name for file in thread[0].attachments], ["rider.pdf"])
		self.assertEqual(thread[1].sender, VENUE)
		self.assertEqual([file.file_name for file in thread[1].attachments], ["tech-sheet.pdf"])
		received_file = frappe.get_doc("File", thread[1].attachments[0].name)
		self.assertTrue(received_file.is_downloadable())

	def test_email_to_a_venue_contact_threads_on_the_venue_and_splits_by_mailbox(self):
		frappe.set_user(MEMBER)
		venue = frappe.get_doc({"doctype": "Venue", "title": "Le Petit Club"}).insert()
		frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "Bob",
				"email_ids": [{"email_id": VENUE, "is_primary": 1}],
				"links": [{"link_doctype": "Venue", "link_name": venue.name}],
			}
		).insert()
		gig = frappe.get_doc({"doctype": "Gig", "title": "Le Petit Club residency"}).insert()
		sent = make(
			doctype="Gig", name=gig.name, subject="Residency dates", content="<p>Hi Bob</p>", recipients=[VENUE], send_email=True
		)

		frappe.set_user("Administrator")
		InboundMail(venue_reply(frappe.get_doc("Communication", sent["name"])), self.mailbox).process()
		reply = frappe.get_last_doc("Communication", filters={"in_reply_to": sent["name"]})

		frappe.set_user(MEMBER)
		self.assertEqual([email.name for email in get_emails("Venue", venue.name)], [sent["name"], reply.name])
		outbox = {email.name: email for email in get_mailbox("Sent")}
		inbox = {email.name: email for email in get_mailbox("Received")}
		self.assertIn(sent["name"], outbox)
		self.assertNotIn(sent["name"], inbox)
		self.assertNotIn(reply.name, outbox)
		self.assertEqual(inbox[reply.name].seen, 0)
		self.assertEqual(inbox[reply.name].thread, {"doctype": "Gig", "name": gig.name})

		mark_seen(reply.name)
		self.assertEqual(frappe.db.get_value("Communication", reply.name, "seen"), 1)

	def test_mail_linked_to_no_record_threads_on_itself(self):
		enquiry = incoming_email("Jane Doe <jane.promoter@example.com>", "Booking enquiry", "enquiry-1")
		InboundMail(enquiry.as_string(), self.mailbox).process()
		received = frappe.get_last_doc("Communication", filters={"subject": "Booking enquiry"})

		frappe.set_user(MEMBER)
		inbox = {email.name: email for email in get_mailbox("Received")}
		self.assertEqual(inbox[received.name].thread, {"doctype": "Communication", "name": received.name})
		reply = make(
			doctype="Communication",
			name=received.name,
			subject="Re: Booking enquiry",
			content="<p>We would love to.</p>",
			recipients=["jane.promoter@example.com"],
			send_email=True,
		)
		self.assertEqual(
			[email.name for email in get_emails("Communication", received.name)], [received.name, reply["name"]]
		)

	def test_emails_are_only_listed_for_email_doctypes(self):
		frappe.set_user(MEMBER)
		with self.assertRaises(frappe.ValidationError):
			get_emails("User", MEMBER)
