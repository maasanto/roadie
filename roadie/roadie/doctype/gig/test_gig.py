from io import BytesIO

import frappe
from frappe.tests import IntegrationTestCase
from frappe.website.path_resolver import resolve_redirect
from pypdf import PdfWriter

from roadie.api import get_attachments, get_members
from roadie.www import roadie as roadie_page

MEMBER = "john@example.com"
OTHER_MEMBER = "jane@example.com"


def make_member(email, first_name):
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": first_name, "last_name": "Doe", "send_welcome_email": 0}
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

	def test_gig_takes_the_festival_window_unless_already_set(self):
		festival = frappe.get_doc(
			{
				"doctype": "Festival",
				"title": "Acme Festival",
				"application_opens": "2027-01-10",
				"application_closes": "2027-02-15",
			}
		).insert()

		frappe.set_user(MEMBER)
		copied = frappe.get_doc({"doctype": "Gig", "title": "Acme 2027", "festival": festival.name}).insert()
		edited = frappe.get_doc(
			{"doctype": "Gig", "title": "Acme 2027 late", "festival": festival.name, "application_closes": "2027-03-01"}
		).insert()

		self.assertEqual(str(copied.application_opens), "2027-01-10")
		self.assertEqual(str(copied.application_closes), "2027-02-15")
		self.assertEqual(str(edited.application_closes), "2027-03-01")
		self.assertEqual(copied.gig_owner, MEMBER)

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

	def test_guest_is_sent_to_login(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.Redirect):
			roadie_page.get_context()
		self.assertEqual(frappe.local.flags.redirect_location, "/login?redirect-to=/roadie")

	def test_old_band_links_land_on_roadie(self):
		frappe.cache.delete_value("website_redirects")
		for old_path, new_path in (("band", "/roadie"), ("band/tasks", "/roadie/tasks")):
			with self.assertRaises(frappe.Redirect):
				resolve_redirect(old_path)
			self.assertEqual(frappe.flags.redirect_location, new_path)
