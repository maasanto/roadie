from unittest.mock import patch

import frappe
from frappe.desk.form.utils import add_comment
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from roadie.api import get_gig_activity, mark_thread_seen
from roadie.roadie.doctype.gig.test_gig import MEMBER, OTHER_MEMBER, make_member

VENUE = "venue@example.com"


def make_gig(title):
	return frappe.get_doc({"doctype": "Gig", "title": title}).insert()


def add_activity(gig):
	"""One of each: an open task overdue, an open task due later, a done task, a comment and an attachment."""
	for due_date, done in ((add_days(today(), -1), 0), (add_days(today(), 7), 0), (add_days(today(), -3), 1)):
		frappe.get_doc(
			{
				"doctype": "Band Task",
				"title": "Send the rider",
				"gig": gig,
				"due_date": due_date,
				"done": done,
			}
		).insert()
	add_comment("Gig", gig, "<p>Van booked</p>", "Administrator", "Administrator")
	frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"rider-{gig}.txt",
			"content": f"Rider for {gig}",
			"attached_to_doctype": "Gig",
			"attached_to_name": gig,
		}
	).insert()


def file_email(written_from=None, linked_to=None, seen=0, sent_or_received="Received"):
	"""An email written from a gig references it; one Frappe filed through a contact links to it."""
	return frappe.get_doc(
		{
			"doctype": "Communication",
			"communication_medium": "Email",
			"communication_type": "Communication",
			"sent_or_received": sent_or_received,
			"subject": "Re: tech rider",
			"sender": VENUE,
			"seen": seen,
			"reference_doctype": "Gig" if written_from else None,
			"reference_name": written_from,
			"timeline_links": [{"link_doctype": "Gig", "link_name": linked_to}] if linked_to else [],
		}
	).insert(ignore_permissions=True)


class TestGigActivity(IntegrationTestCase):
	def setUp(self):
		make_member(MEMBER, "John")
		make_member(OTHER_MEMBER, "Jane")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_cards_count_what_the_panel_shows_and_its_emails_still_unread(self):
		gig = make_gig("Le Petit Club residency").name
		add_activity(gig)
		file_email(written_from=gig)
		file_email(written_from=gig, linked_to=gig)
		file_email(linked_to=gig)
		file_email(written_from=gig, seen=1)
		file_email(written_from=gig, sent_or_received="Sent")

		frappe.set_user(MEMBER)
		activity = get_gig_activity()[gig]
		self.assertEqual(
			activity,
			{
				"emails": 5,
				"unread_emails": 3,
				"open_tasks": 2,
				"next_due": frappe.utils.getdate(add_days(today(), -1)),
				"comments": 1,
				"attachments": 1,
			},
		)

		mark_thread_seen("Gig", gig)
		activity = get_gig_activity()[gig]
		self.assertEqual((activity["emails"], activity["unread_emails"]), (5, 0))

	def test_a_gig_with_only_sent_mail_still_counts_it(self):
		gig = make_gig("Acme Festival 2027").name
		file_email(written_from=gig, sent_or_received="Sent")

		frappe.set_user(MEMBER)
		self.assertEqual(get_gig_activity()[gig], {"emails": 1, "unread_emails": 0})

	def test_member_gets_no_counts_for_a_gig_they_cannot_read(self):
		readable = make_gig("Acme Festival 2027").name
		hidden = make_gig("Private showcase").name
		add_activity(readable)
		add_activity(hidden)
		file_email(written_from=hidden)
		restriction = frappe.get_doc(
			{"doctype": "User Permission", "user": MEMBER, "allow": "Gig", "for_value": readable}
		).insert(ignore_permissions=True)
		self.addCleanup(restriction.delete, ignore_permissions=True)

		frappe.set_user(OTHER_MEMBER)
		self.assertIn(hidden, get_gig_activity())

		frappe.set_user(MEMBER)
		activity = get_gig_activity()
		self.assertIn(readable, activity)
		self.assertNotIn(hidden, activity)

	def test_more_gigs_with_activity_cost_no_more_queries(self):
		add_activity(make_gig("Le Petit Club residency").name)
		frappe.set_user(MEMBER)
		get_gig_activity()
		with patch.object(frappe.db, "sql", wraps=frappe.db.sql) as sql:
			get_gig_activity()
		queries_for_one_gig = sql.call_count

		frappe.set_user("Administrator")
		for title in ("Acme Festival 2027", "Private showcase"):
			gig = make_gig(title).name
			add_activity(gig)
			file_email(written_from=gig, linked_to=gig)
		frappe.set_user(MEMBER)
		get_gig_activity()
		with patch.object(frappe.db, "sql", wraps=frappe.db.sql) as sql:
			get_gig_activity()
		self.assertEqual(sql.call_count, queries_for_one_gig)
