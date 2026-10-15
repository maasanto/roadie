import frappe
from frappe.desk.form.utils import add_comment
from frappe.tests import IntegrationTestCase

from roadie.api import EMAIL_DRAFT_FIELD, get_activity
from roadie.roadie.doctype.gig.test_gig import MEMBER, OTHER_MEMBER, make_member
from roadie.tests.test_gig_activity import file_email


def attach(gig, file_name, attached_to_field=None):
	return frappe.get_doc(
		{
			"doctype": "File",
			"file_name": file_name,
			"content": f"{file_name} for {gig}",
			"attached_to_doctype": "Gig",
			"attached_to_name": gig,
			"attached_to_field": attached_to_field,
		}
	).insert()


class TestRecordActivity(IntegrationTestCase):
	def setUp(self):
		make_member(MEMBER, "John")
		make_member(OTHER_MEMBER, "Jane")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_bandmate_reads_who_did_what_on_a_gig_in_order(self):
		frappe.set_user(MEMBER)
		venue = frappe.get_doc({"doctype": "Venue", "title": "Acme Hall"}).insert()
		gig = frappe.get_doc({"doctype": "Gig", "title": "Acme Hall 2027"}).insert()
		gig.update(
			{
				"status": "Contacted",
				"venue": venue.name,
				"gig_owner": OTHER_MEMBER,
				"notes": "Load-in 6pm\nParking at the back",
			}
		)
		# Frappe skips versions under test unless asked.
		gig.save(ignore_version=False)
		add_comment("Gig", gig.name, "<p>Van <b>booked</b></p>", MEMBER, "John Doe")
		attach(gig.name, "rider.txt")
		attach(gig.name, "unsent.txt", attached_to_field=EMAIL_DRAFT_FIELD).delete()
		file_email(written_from=gig.name)
		frappe.set_user("Administrator")
		pulled_from_sent_folder = file_email(written_from=gig.name, sent_or_received="Sent")

		frappe.set_user(OTHER_MEMBER)
		activity = get_activity("Gig", gig.name)

		self.assertEqual(
			[(entry["type"], entry["by"]) for entry in activity],
			[
				("created", "John Doe"),
				("changed", "John Doe"),
				("changed", "John Doe"),
				("changed", "John Doe"),
				("changed", "John Doe"),
				("commented", "John Doe"),
				("attached", "John Doe"),
				("emailed", "venue@example.com"),
				("emailed", pulled_from_sent_folder.sender),
			],
		)
		changes = {
			entry["label"]: (entry["from"], entry["to"]) for entry in activity if entry["type"] == "changed"
		}
		self.assertEqual(
			changes,
			{
				"Status": ("Idea", "Contacted"),
				"Venue": ("", "Acme Hall"),
				"Owner": ("John Doe", "Jane Doe"),
				"Notes": (None, "Load-in 6pm Parking at the back"),
			},
		)
		self.assertEqual(
			[entry.get("text") for entry in activity[-4:-1]], ["Van booked", "rider.txt", "Re: tech rider"]
		)

	def test_activity_is_only_listed_for_band_records(self):
		frappe.set_user(MEMBER)
		with self.assertRaises(frappe.ValidationError):
			get_activity("User", MEMBER)
