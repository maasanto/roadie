import json
from io import BytesIO

import frappe
from frappe.api.v2 import document_list
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.desk.reportview import delete_items
from frappe.tests import IntegrationTestCase
from frappe.utils import set_request
from frappe.website.path_resolver import resolve_redirect
from pypdf import PdfWriter

from roadie.api import get_attachments, get_members, get_pipeline_totals
from roadie.www import roadie as roadie_page

MEMBER = "john@example.com"
OTHER_MEMBER = "jane@example.com"


def make_member(email, first_name):
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": first_name,
				"last_name": "Doe",
				"send_welcome_email": 0,
			}
		).insert(ignore_permissions=True)
	frappe.get_doc("User", email).add_roles("Band Member")


def blank_pdf():
	writer = PdfWriter()
	writer.add_blank_page(width=595, height=842)
	buffer = BytesIO()
	writer.write(buffer)
	return buffer.getvalue()


class TestGig(IntegrationTestCase):
	def setUp(self):
		make_member(MEMBER, "John")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_member_lists_and_edits_gigs_without_desk(self):
		frappe.set_user(MEMBER)
		gig = frappe.get_doc({"doctype": "Gig", "title": "Acme Festival 2027"}).insert()

		self.assertEqual(frappe.db.get_value("User", MEMBER, "user_type"), "Website User")
		self.assertEqual(gig.status, "Idea")
		self.assertIn(gig.name, [row.name for row in frappe.get_list("Gig")])
		self.assertEqual(roadie_page.get_context().boot["user"], MEMBER)

	def test_application_window_cannot_close_before_it_opens(self):
		frappe.set_user(MEMBER)
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Gig",
					"title": "Acme 2027",
					"application_opens": "2027-03-01",
					"application_closes": "2027-02-01",
				}
			).insert()

	def test_members_lists_only_band_members(self):
		frappe.set_user(MEMBER)
		members = [member.name for member in get_members()]

		self.assertIn(MEMBER, members)
		self.assertNotIn("Administrator", members)

	def test_rider_attached_by_one_member_opens_for_another(self):
		make_member(OTHER_MEMBER, "Jane")
		frappe.set_user(OTHER_MEMBER)
		gig = frappe.get_doc({"doctype": "Gig", "title": "Acme Festival 2027"}).insert()
		frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "rider.pdf",
				"content": blank_pdf(),
				"is_private": 1,
				"attached_to_doctype": "Gig",
				"attached_to_name": gig.name,
			}
		).insert()

		frappe.set_user(MEMBER)
		attachments = get_attachments(gig.name)

		self.assertEqual([file.file_name for file in attachments], ["rider.pdf"])
		self.assertTrue(frappe.get_doc("File", attachments[0].name).is_downloadable())

	def test_guest_is_sent_to_login_and_back_to_the_record_they_asked_for(self):
		frappe.set_user("Guest")
		set_request(method="GET", path="/roadie/directory/festivals", query_string="entry=Festival:abc")
		self.addCleanup(setattr, frappe.local, "request", None)
		with self.assertRaises(frappe.Redirect):
			roadie_page.get_context()
		self.assertEqual(
			frappe.local.flags.redirect_location,
			"/login?redirect-to=%2Froadie%2Fdirectory%2Ffestivals%3Fentry%3DFestival%3Aabc",
		)

	def test_board_reads_fees_in_the_site_currency(self):
		self.addCleanup(frappe.db.set_default, "currency", frappe.db.get_default("currency"))
		frappe.db.set_default("currency", "EUR")
		frappe.set_user(MEMBER)
		self.assertEqual(roadie_page.get_context().boot["currency"], "EUR")

	def test_list_api_leaves_out_a_fee_above_the_members_permlevel(self):
		"""The pipeline always asks for the fee and relies on this to keep it from a member who cannot read it."""
		gig = frappe.get_doc({"doctype": "Gig", "title": "Acme Festival 2027", "fee": 1500}).insert()
		restriction = make_property_setter("Gig", "fee", "permlevel", 1, "Int")
		self.addCleanup(frappe.clear_cache, doctype="Gig")
		self.addCleanup(frappe.delete_doc, "Property Setter", restriction.name, ignore_permissions=True)

		frappe.set_user(MEMBER)
		self.addCleanup(setattr, frappe.local, "form_dict", frappe.local.form_dict)
		frappe.local.form_dict = frappe._dict(
			fields=json.dumps(["name", "fee"]), filters=json.dumps({"name": gig.name})
		)

		self.assertEqual(document_list("Gig"), [{"name": gig.name}])

	def test_pipeline_totals_count_and_sum_every_matching_gig_by_status(self):
		"""Past its row limit the board reads its column counts and fees from here, not from the cards it loaded."""
		frappe.set_user(MEMBER)
		for title, status, fee in (
			("Acme Totals 1", "Contacted", 2600),
			("Acme Totals 2", "Contacted", 2600),
			("Acme Totals 3", "Booked", 1500),
			("Acme Other", "Contacted", 9999),
		):
			frappe.get_doc({"doctype": "Gig", "title": title, "status": status, "fee": fee}).insert()

		totals = get_pipeline_totals(json.dumps({"title": ["like", "Acme Totals%"]}))

		self.assertCountEqual(
			totals,
			[{"status": "Contacted", "count": 2, "fee": 5200}, {"status": "Booked", "count": 1, "fee": 1500}],
		)

	def test_pipeline_totals_leave_out_a_fee_above_the_members_permlevel(self):
		gig = frappe.get_doc({"doctype": "Gig", "title": "Acme Festival 2027", "fee": 1500}).insert()
		restriction = make_property_setter("Gig", "fee", "permlevel", 1, "Int")
		self.addCleanup(frappe.clear_cache, doctype="Gig")
		self.addCleanup(frappe.delete_doc, "Property Setter", restriction.name, ignore_permissions=True)

		frappe.set_user(MEMBER)

		self.assertEqual(
			get_pipeline_totals(json.dumps({"name": gig.name})), [{"status": "Idea", "count": 1}]
		)

	def test_old_band_links_land_on_roadie(self):
		frappe.cache.delete_value("website_redirects")
		for old_path, new_path in (("band", "/roadie"), ("band/tasks", "/roadie/tasks")):
			with self.assertRaises(frappe.Redirect):
				resolve_redirect(old_path)
			self.assertEqual(frappe.flags.redirect_location, new_path)


# A class of its own: delete_items commits, which would keep whatever the other tests left for the class rollback.
class TestDeleteGigsFromTheList(IntegrationTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

	def test_member_deletes_a_dead_gig_and_keeps_one_with_tasks(self):
		"""The list's Delete posts a batch to delete_items as below and keeps the names it returns selected."""
		make_member(MEMBER, "John")
		frappe.set_user(MEMBER)
		dead = frappe.get_doc({"doctype": "Gig", "title": "Acme Winter 2026"}).insert()
		busy = frappe.get_doc({"doctype": "Gig", "title": "Acme Summer 2027"}).insert()
		frappe.get_doc({"doctype": "Band Task", "gig": busy.name, "title": "Send the rider"}).insert()
		# delete_items rolls back on a refusal, which would otherwise undo this setup.
		frappe.db.commit()  # nosemgrep
		self.addCleanup(frappe.db.commit)  # nosemgrep
		self.addCleanup(frappe.db.delete, "Gig", {"name": ("in", [dead.name, busy.name])})
		self.addCleanup(frappe.db.delete, "Band Task", {"gig": busy.name})

		self.addCleanup(setattr, frappe.local, "form_dict", frappe.local.form_dict)
		frappe.local.form_dict = frappe._dict(doctype="Gig", items=json.dumps([dead.name, busy.name]))

		self.assertEqual(delete_items(), [busy.name])
		self.assertFalse(frappe.db.exists("Gig", dead.name))
		self.assertTrue(frappe.db.exists("Gig", busy.name))
