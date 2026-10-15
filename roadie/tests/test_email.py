from email import message_from_string
from email.message import EmailMessage
from email.utils import parseaddr
from unittest.mock import patch

import frappe
from frappe.core.doctype.communication.email import make
from frappe.email.doctype.email_account.email_account import EmailAccount
from frappe.email.receive import InboundMail
from frappe.tests import IntegrationTestCase

from roadie.api import (
	EMAIL_DRAFT_FIELD,
	delete_draft_attachment,
	delete_email,
	delete_threads,
	get_attachments,
	get_emails,
	get_mailbox,
	link_thread,
	mark_threads_read,
	mark_threads_unread,
)
from roadie.install import grant_communication_access
from roadie.roadie.doctype.gig.test_gig import MEMBER, OTHER_MEMBER, blank_pdf, make_member
from roadie.www import roadie as roadie_page

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


def sent_by_band(subject, message_id):
	email = EmailMessage()
	email["From"] = f"Acme Band <{MAILBOX}>"
	email["To"] = VENUE
	email["Subject"] = subject
	email["Message-ID"] = f"<{message_id}>"
	email.set_content("Here is our tech rider.")
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
		InboundMail(
			venue_reply(frappe.get_doc("Communication", sent["name"]), "tech-sheet.pdf"), self.mailbox
		).process()

		frappe.set_user(MEMBER)
		thread = get_emails("Gig", gig.name)

		self.assertEqual([email.sent_or_received for email in thread], ["Sent", "Received"])
		self.assertEqual([file.file_name for file in thread[0].attachments], ["rider.pdf"])
		self.assertEqual(thread[1].sender, VENUE)
		self.assertEqual(thread[1].account_email, MAILBOX)
		self.assertEqual([file.file_name for file in thread[1].attachments], ["tech-sheet.pdf"])
		received_file = frappe.get_doc("File", thread[1].attachments[0].name)
		self.assertTrue(received_file.is_downloadable())

	def test_member_forwards_a_received_attachment(self):
		frappe.set_user(MEMBER)
		gig = frappe.get_doc({"doctype": "Gig", "title": "Le Petit Club residency"}).insert()
		sent = make(
			doctype="Gig",
			name=gig.name,
			subject="Stage plan",
			content="<p>Could you send your stage plan?</p>",
			recipients=[VENUE],
			send_email=True,
		)
		frappe.set_user("Administrator")
		reply = incoming_email(f"Le Petit Club <{VENUE}>", "Re: Stage plan", f"stage-plan-{sent['name']}")
		reply["In-Reply-To"] = f"<{frappe.db.get_value('Communication', sent['name'], 'message_id')}>"
		# Its own content: Frappe dedupes files by hash, and make() commits, so a shared blank PDF leaks into other tests.
		reply.add_attachment(f"Stage plan {sent['name']}", filename="stage-plan.txt")
		InboundMail(reply.as_string(), self.mailbox).process()

		frappe.set_user(MEMBER)
		original_file = get_emails("Gig", gig.name)[1].attachments[0]
		make(
			doctype="Gig",
			name=gig.name,
			subject="Fwd: Re: Stage plan",
			content="<p>For the sound engineer</p>",
			recipients=["agent@example.com"],
			send_email=True,
			attachments=[original_file.name],
		)

		forward = get_emails("Gig", gig.name)[2]
		self.assertEqual(forward.subject, "Fwd: Re: Stage plan")
		self.assertEqual([file.file_url for file in forward.attachments], [original_file.file_url])
		self.assertTrue(frappe.get_doc("File", forward.attachments[0].name).is_downloadable())

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
			doctype="Gig",
			name=gig.name,
			subject="Residency dates",
			content="<p>Hi Bob</p>",
			recipients=[VENUE],
			send_email=True,
		)

		frappe.set_user("Administrator")
		InboundMail(venue_reply(frappe.get_doc("Communication", sent["name"])), self.mailbox).process()
		reply = frappe.get_last_doc("Communication", filters={"in_reply_to": sent["name"]})

		frappe.set_user(MEMBER)
		self.assertEqual(
			[email.name for email in get_emails("Venue", venue.name)], [sent["name"], reply.name]
		)
		outbox = {email.name: email for email in get_mailbox("Sent")}
		inbox = {email.name: email for email in get_mailbox("Received")}
		self.assertIn(sent["name"], outbox)
		self.assertNotIn(sent["name"], inbox)
		self.assertNotIn(reply.name, outbox)
		self.assertEqual(inbox[reply.name].seen, 0)
		self.assertEqual(inbox[reply.name].thread, {"doctype": "Gig", "name": gig.name})

		mark_threads_read([{"doctype": "Gig", "name": gig.name}])
		self.assertEqual(frappe.db.get_value("Communication", reply.name, "seen"), 1)
		# The venue's page shows the reply too, but the mailbox files it under the gig it answers.
		mark_threads_unread([{"doctype": "Venue", "name": venue.name}])
		self.assertEqual(frappe.db.get_value("Communication", reply.name, "seen"), 1)

	def test_inbox_lists_one_row_per_thread_with_its_latest_email(self):
		frappe.set_user(MEMBER)
		gig = frappe.get_doc({"doctype": "Gig", "title": "Acme Festival 2027"}).insert()
		sent = make(
			doctype="Gig",
			name=gig.name,
			subject="Acme Festival 2027",
			content="<p>Are you still booking?</p>",
			recipients=[VENUE],
			send_email=True,
		)
		frappe.set_user("Administrator")
		sent_message_id = frappe.db.get_value("Communication", sent["name"], "message_id")
		# Unique per run: make() commits, so a fixed Message-ID would be a duplicate the next time the suite runs.
		for message_id in (f"first-reply-{sent['name']}", f"second-reply-{sent['name']}"):
			reply = incoming_email(f"Le Petit Club <{VENUE}>", "Re: Acme Festival 2027", message_id)
			reply["In-Reply-To"] = f"<{sent_message_id}>"
			InboundMail(reply.as_string(), self.mailbox).process()
		replies = frappe.get_all(
			"Communication", filters={"in_reply_to": sent["name"]}, order_by="creation asc", pluck="name"
		)
		frappe.db.set_value("Communication", replies[1], "communication_date", frappe.utils.add_days(None, 1))

		frappe.set_user(MEMBER)
		rows = [row for row in get_mailbox("Received") if row.thread == {"doctype": "Gig", "name": gig.name}]
		self.assertEqual([(row.name, row.count, row.unread) for row in rows], [(replies[1], 2, 2)])

		thread = {"doctype": "Gig", "name": gig.name}
		mark_threads_read([thread])
		row = next(row for row in get_mailbox("Received") if row.name == replies[1])
		self.assertEqual(row.unread, 0)

		mark_threads_unread([thread])
		row = next(row for row in get_mailbox("Received") if row.name == replies[1])
		self.assertEqual(row.unread, 1)
		self.assertEqual(frappe.db.get_value("Communication", replies[1], "seen"), 0)

	def test_bulk_delete_clears_an_unlinked_conversation_but_never_a_gigs_mail(self):
		enquiry = incoming_email("Jane Doe <jane.promoter@example.com>", "Spam?", frappe.generate_hash())
		InboundMail(enquiry.as_string(), self.mailbox).process()
		received = frappe.get_last_doc("Communication", filters={"subject": "Spam?"})
		frappe.set_user(MEMBER)
		reply = make(
			doctype="Communication",
			name=received.name,
			subject="Re: Spam?",
			content="<p>No thanks.</p>",
			recipients=["jane.promoter@example.com"],
			send_email=True,
		)
		gig = frappe.get_doc({"doctype": "Gig", "title": "Acme Festival 2027"}).insert()
		gig_email = make(
			doctype="Gig",
			name=gig.name,
			subject="Dates",
			content="<p>Hi</p>",
			recipients=[VENUE],
			send_email=True,
		)

		delete_threads([received.name])
		self.assertFalse(frappe.db.exists("Communication", received.name))
		self.assertFalse(frappe.db.exists("Communication", reply["name"]))
		with self.assertRaises(frappe.ValidationError):
			delete_threads([gig_email["name"]])
		self.assertTrue(frappe.db.exists("Communication", gig_email["name"]))

	def test_deleting_a_conversations_first_email_hands_it_to_the_next(self):
		enquiry = incoming_email(
			"Jane Doe <jane.promoter@example.com>", "Summer dates", frappe.generate_hash()
		)
		InboundMail(enquiry.as_string(), self.mailbox).process()
		first = frappe.get_last_doc("Communication", filters={"subject": "Summer dates"})
		frappe.set_user(MEMBER)
		replies = [
			make(
				doctype="Communication",
				name=first.name,
				subject="Re: Summer dates",
				content=f"<p>{text}</p>",
				recipients=["jane.promoter@example.com"],
				send_email=True,
			)["name"]
			for text in ("July works.", "August too.")
		]
		frappe.db.set_value("Communication", replies[1], "communication_date", frappe.utils.add_days(None, 1))

		self.assertEqual(delete_email(first.name), {"promoted": replies[0]})
		self.assertFalse(frappe.db.exists("Email Queue", {"reference_name": first.name}))
		self.assertEqual([email.name for email in get_emails("Communication", replies[0])], replies)
		outbox = {row.name: row for row in get_mailbox("Sent")}
		self.assertEqual(outbox[replies[1]].thread, {"doctype": "Communication", "name": replies[0]})

		follow_up = make(
			doctype="Communication",
			name=replies[0],
			subject="Re: Summer dates",
			content="<p>September is free as well.</p>",
			recipients=["jane.promoter@example.com"],
			send_email=True,
		)["name"]
		self.assertIn(follow_up, [email.name for email in get_emails("Communication", replies[0])])

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
			[email.name for email in get_emails("Communication", received.name)],
			[received.name, reply["name"]],
		)

	def test_search_and_a_higher_limit_reach_mail_older_than_the_latest(self):
		# Unique per run: InboundMail commits, so earlier runs' emails are still on the site.
		sender, subject = frappe.generate_hash(), frappe.generate_hash()
		enquiry = incoming_email(f"Sunny Fest <{sender}@sunnyfest.example.com>", f"Line-up {subject}", sender)
		InboundMail(enquiry.as_string(), self.mailbox).process()
		march = frappe.get_last_doc("Communication", filters={"subject": f"Line-up {subject}"})
		frappe.db.set_value("Communication", march.name, "communication_date", "2000-03-12 09:00:00")
		newer = incoming_email("Jane Roe <jane.roe@example.com>", "Photos", subject)
		InboundMail(newer.as_string(), self.mailbox).process()
		every_email = frappe.db.count(
			"Communication",
			{
				"communication_medium": "Email",
				"communication_type": "Communication",
				"sent_or_received": "Received",
			},
		)

		def listed(**kwargs):
			return {row.name for row in get_mailbox("Received", **kwargs)}

		frappe.set_user(MEMBER)
		self.assertNotIn(march.name, listed(limit=1))
		self.assertIn(march.name, listed(limit=every_email))
		self.assertEqual(listed(query=f" {sender}@SUNNYFEST ", limit=1), {march.name})
		self.assertEqual(listed(query=f"line-up {subject}"), {march.name})
		self.assertEqual(listed(query=f"nothing like {subject}"), set())

	def test_linked_thread_and_its_later_replies_file_under_the_gig(self):
		enquiry = incoming_email(
			"Jane Doe <jane.promoter@example.com>", "Summer booking", f"enquiry-{frappe.generate_hash()}"
		)
		InboundMail(enquiry.as_string(), self.mailbox).process()
		received = frappe.get_last_doc("Communication", filters={"subject": "Summer booking"})

		frappe.set_user(MEMBER)
		gig = frappe.get_doc({"doctype": "Gig", "title": "Acme summer festival"}).insert()
		reply = make(
			doctype="Communication",
			name=received.name,
			subject="Re: Summer booking",
			content="<p>We would love to.</p>",
			recipients=["jane.promoter@example.com"],
			send_email=True,
		)
		link_thread(received.name, "Gig", gig.name)

		frappe.set_user("Administrator")
		answer = incoming_email(
			"Jane Doe <jane.promoter@example.com>", "Re: Summer booking", f"answer-{frappe.generate_hash()}"
		)
		answer["In-Reply-To"] = f"<{frappe.db.get_value('Communication', reply['name'], 'message_id')}>"
		InboundMail(answer.as_string(), self.mailbox).process()
		answered = frappe.get_last_doc("Communication", filters={"in_reply_to": reply["name"]})

		frappe.set_user(MEMBER)
		self.assertEqual(
			[email.name for email in get_emails("Gig", gig.name)],
			[received.name, reply["name"], answered.name],
		)
		inbox = {row.name: row.thread for row in get_mailbox("Received")}
		self.assertEqual(inbox[answered.name], {"doctype": "Gig", "name": gig.name})
		self.assertNotIn(received.name, inbox)
		other_gig = frappe.get_doc({"doctype": "Gig", "title": "Acme winter festival"}).insert()
		with self.assertRaises(frappe.ValidationError):
			link_thread(received.name, "Gig", other_gig.name)

	def test_new_email_from_the_inbox_needs_no_record(self):
		frappe.set_user(MEMBER)
		# Its own content: Frappe dedupes files by hash, and make() commits, so a shared blank PDF leaks into other tests.
		flyer = frappe.get_doc(
			{"doctype": "File", "file_name": "flyer.txt", "content": "Spring tour flyer", "is_private": 1}
		).insert()
		sent = make(
			subject="Booking enquiry for spring",
			content="<p>Would the band fit your programme?</p>",
			recipients=["jane.roe@example.com"],
			send_email=True,
			attachments=[flyer.name],
		)

		outbox = {row.name: row for row in get_mailbox("Sent")}
		self.assertEqual(outbox[sent["name"]].thread, {"doctype": "Communication", "name": sent["name"]})
		thread = get_emails("Communication", sent["name"])
		self.assertEqual([file.file_name for file in thread[0].attachments], ["flyer.txt"])

	def test_composer_signs_with_the_members_signature_else_the_band_mailboxs(self):
		for account in frappe.get_all("Email Account", {"default_outgoing": 1}, pluck="name"):
			frappe.db.set_value("Email Account", account, "default_outgoing", 0)
			self.addCleanup(frappe.db.set_value, "Email Account", account, "default_outgoing", 1)
		self.mailbox.db_set(
			{"enable_outgoing": 1, "default_outgoing": 1, "add_signature": 0, "signature": "<p>Acme Band</p>"}
		)
		self.addCleanup(self.mailbox.db_set, {"add_signature": 0, "signature": None})
		# Desk saves a cleared signature as an empty editor, not as nothing.
		frappe.db.set_value(
			"User", MEMBER, "email_signature", '<div class="ql-editor read-mode"><p><br></p></div>'
		)
		self.addCleanup(frappe.db.set_value, "User", MEMBER, "email_signature", None)
		frappe.set_user(MEMBER)

		def signature():
			return roadie_page.get_context().boot["email_signature"]

		self.assertIsNone(signature())
		self.mailbox.db_set("add_signature", 1)
		self.assertEqual(signature(), "<p>Acme Band</p>")
		frappe.db.set_value("User", MEMBER, "email_signature", "<p>John, drums</p>")
		self.assertEqual(signature(), "<p>John, drums</p>")

	def test_inbox_email_and_its_follow_up_take_replies_to_the_band_mailbox(self):
		for account in frappe.get_all("Email Account", {"default_outgoing": 1}, pluck="name"):
			frappe.db.set_value("Email Account", account, "default_outgoing", 0)
			self.addCleanup(frappe.db.set_value, "Email Account", account, "default_outgoing", 1)
		self.mailbox.db_set({"enable_outgoing": 1, "default_outgoing": 1, "add_reply_to_header": 1})
		frappe.set_user(MEMBER)
		sender = roadie_page.get_context().boot["email_sender"]

		first = make(
			sender=sender, subject="Booking enquiry", content="<p>Hi</p>", recipients=[VENUE], send_email=True
		)
		follow_up = make(
			sender=sender,
			subject="Re: Booking enquiry",
			content="<p>Any news?</p>",
			recipients=[VENUE],
			in_reply_to=first["name"],
			send_email=True,
		)

		for sent in (first, follow_up):
			queued = frappe.get_last_doc("Email Queue", filters={"communication": sent["name"]})
			headers = message_from_string(queued.message)
			self.assertEqual(parseaddr(headers["From"])[1], MAILBOX)
			self.assertEqual(parseaddr(headers["Reply-To"])[1], MAILBOX)

	def test_sent_folder_fills_the_outbox_but_skips_what_frappe_sent(self):
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
		from_roadie = make(
			subject="Residency dates", content="<p>Hi Bob</p>", recipients=[VENUE], send_email=True
		)

		frappe.set_user("Administrator")
		roadie_message_id = frappe.db.get_value("Communication", from_roadie["name"], "message_id")
		reset_subject = f"Password Reset {frappe.generate_hash()}"
		sent_by_frappe = [
			sent_by_band("Residency dates", roadie_message_id),
			sent_by_band(reset_subject, f"reset-{frappe.generate_hash()}@example.com"),
		]
		for email in sent_by_frappe:
			email["X-Frappe-Site"] = frappe.utils.get_url()
		from_webmail = sent_by_band("Tech rider", f"webmail-{frappe.generate_hash()}@example.com")
		pulled = [
			InboundMail(email.as_string(), self.mailbox, uid, "SEEN", imap_folder="Sent")
			for uid, email in enumerate([from_webmail, *sent_by_frappe], start=1)
		]
		# receive() commits after every email, which would leave this test's mail on the site.
		with (
			patch.object(EmailAccount, "get_inbound_mails", return_value=pulled),
			patch.object(frappe.db, "commit"),
		):
			self.mailbox.receive()
		webmail_sent = frappe.get_last_doc("Communication", filters={"subject": "Tech rider"})

		frappe.set_user(MEMBER)
		outbox = {row.name: row for row in get_mailbox("Sent")}
		self.assertEqual(outbox[webmail_sent.name].delivery_status, "Sent")
		self.assertEqual(outbox[webmail_sent.name].thread, {"doctype": "Venue", "name": venue.name})
		self.assertNotIn(webmail_sent.name, {row.name for row in get_mailbox("Received")})
		self.assertFalse(frappe.db.exists("Email Queue", {"communication": webmail_sent.name}))
		self.assertEqual(frappe.db.count("Communication", {"message_id": roadie_message_id}), 1)
		self.assertFalse(frappe.db.exists("Communication", {"subject": reset_subject}))

	def test_reminders_stay_out_of_the_gig_thread(self):
		frappe.set_user(MEMBER)
		gig = frappe.get_doc({"doctype": "Gig", "title": "Acme Festival 2027"}).insert()
		reminder = frappe.get_doc(
			{
				"doctype": "Communication",
				"communication_medium": "Email",
				"communication_type": "Automated Message",
				"sent_or_received": "Sent",
				"subject": "Acme Festival 2027 application closes in 7 days",
				"recipients": MEMBER,
				"reference_doctype": "Gig",
				"reference_name": gig.name,
			}
		).insert(ignore_permissions=True)

		self.assertEqual(get_emails("Gig", gig.name), [])
		with self.assertRaises(frappe.ValidationError):
			delete_email(reminder.name)

	def test_draft_only_deletes_its_own_unsent_uploads(self):
		make_member(OTHER_MEMBER, "Jane")
		frappe.set_user(MEMBER)
		gig = frappe.get_doc({"doctype": "Gig", "title": "Acme Festival 2028"}).insert()

		def upload(file_name, content=None, attached_to_field=EMAIL_DRAFT_FIELD):
			# Unique by default: make() commits, and Frappe dedupes files by hash across runs.
			return frappe.get_doc(
				{
					"doctype": "File",
					"file_name": file_name,
					"content": content or f"{file_name} {frappe.generate_hash()}",
					"is_private": 1,
					"attached_to_doctype": "Gig",
					"attached_to_name": gig.name,
					"attached_to_field": attached_to_field,
				}
			).insert()

		dropped = upload("dropped-from-draft.txt")
		already_on_gig = upload("stage-plan.txt", attached_to_field=None)
		rider = f"Acme rider {frappe.generate_hash()}"
		sent_file = upload("rider.txt", rider)
		make(
			doctype="Gig",
			name=gig.name,
			subject="Rider",
			content="<p>Our rider is attached.</p>",
			recipients=[VENUE],
			send_email=True,
			attachments=[sent_file.name],
		)
		frappe.set_user(OTHER_MEMBER)
		other_members_draft = upload("their-draft.txt")

		frappe.set_user(MEMBER)
		# The same bytes as the sent rider, so Frappe hands this draft upload the sent copy's URL.
		rider_attached_again = upload("rider-again.txt", rider)
		self.assertEqual(rider_attached_again.file_url, sent_file.file_url)
		delete_draft_attachment(dropped.name)
		delete_draft_attachment(rider_attached_again.name)
		for kept in (already_on_gig, sent_file, other_members_draft):
			with self.assertRaises(frappe.PermissionError):
				delete_draft_attachment(kept.name)

		self.assertCountEqual(
			[file.name for file in get_attachments(gig.name)],
			[already_on_gig.name, sent_file.name, other_members_draft.name],
		)

	def test_emails_are_only_listed_for_email_doctypes(self):
		frappe.set_user(MEMBER)
		with self.assertRaises(frappe.ValidationError):
			get_emails("User", MEMBER)
