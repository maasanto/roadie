import frappe
from frappe.tests import IntegrationTestCase

from band_crm.api import get_members
from band_crm.www import band

MEMBER = "john@example.com"


class TestGig(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("User", MEMBER):
			frappe.get_doc(
				{"doctype": "User", "email": MEMBER, "first_name": "John", "last_name": "Doe", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.get_doc("User", MEMBER).add_roles("Band Member")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_member_lists_and_edits_gigs_without_desk(self):
		frappe.set_user(MEMBER)
		gig = frappe.get_doc({"doctype": "Gig", "title": "Acme Festival 2027"}).insert()

		self.assertEqual(frappe.db.get_value("User", MEMBER, "user_type"), "Website User")
		self.assertEqual(gig.status, "Idea")
		self.assertIn(gig.name, [row.name for row in frappe.get_list("Gig")])
		self.assertEqual(band.get_context().boot["user"], MEMBER)

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

	def test_members_lists_only_band_members(self):
		frappe.set_user(MEMBER)
		members = [member.name for member in get_members()]

		self.assertIn(MEMBER, members)
		self.assertNotIn("Administrator", members)

	def test_guest_is_sent_to_login(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.Redirect):
			band.get_context()
		self.assertEqual(frappe.local.flags.redirect_location, "/login?redirect-to=/band")
