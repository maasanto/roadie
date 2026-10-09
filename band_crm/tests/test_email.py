from email.message import EmailMessage

import frappe
from frappe.core.doctype.communication.email import make
from frappe.email.receive import InboundMail
from frappe.tests import IntegrationTestCase

from band_crm.api import get_emails
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


def venue_reply(sent, attachment_name):
	reply = EmailMessage()
	reply["From"] = f"Le Petit Club <{VENUE}>"
	reply["To"] = MAILBOX
	reply["Subject"] = f"Re: {sent.subject}"
	reply["Message-ID"] = "<venue-reply-1@example.com>"
	reply["In-Reply-To"] = f"<{sent.message_id}>"
	reply.set_content("Thanks, the tech sheet is attached.")
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

	def test_emails_are_only_listed_for_email_doctypes(self):
		frappe.set_user(MEMBER)
		with self.assertRaises(frappe.ValidationError):
			get_emails("User", MEMBER)
