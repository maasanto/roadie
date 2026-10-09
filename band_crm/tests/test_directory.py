import frappe
from frappe.tests import IntegrationTestCase

from band_crm.api import get_contacts
from band_crm.install import grant_contact_access

MEMBER = "john@example.com"


def make_contact(first_name, email, festival):
	return frappe.get_doc(
		{
			"doctype": "Contact",
			"first_name": first_name,
			"email_ids": [{"email_id": email, "is_primary": 1}],
			"links": [{"link_doctype": "Festival", "link_name": festival}],
		}
	).insert()


class TestDirectory(IntegrationTestCase):
	def setUp(self):
		grant_contact_access()
		if not frappe.db.exists("User", MEMBER):
			frappe.get_doc(
				{"doctype": "User", "email": MEMBER, "first_name": "John", "last_name": "Doe", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.get_doc("User", MEMBER).add_roles("Band Member")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_member_creates_festival_with_contacts_shared_with_the_band(self):
		other_festival = frappe.get_doc({"doctype": "Festival", "title": "Other Fest"}).insert()
		make_contact("Mallory", "mallory@example.com", other_festival.name)

		frappe.set_user(MEMBER)
		festival = frappe.get_doc({"doctype": "Festival", "title": "Acme Festival", "city": "Lyon"}).insert()
		make_contact("Jane", "jane@example.com", festival.name)
		frappe.set_user("Administrator")
		make_contact("Bob", "bob@example.com", festival.name)

		frappe.set_user(MEMBER)
		contacts = get_contacts("Festival", festival.name)

		self.assertEqual([c.email_id for c in contacts], ["jane@example.com", "bob@example.com"])
		bob = frappe.get_doc("Contact", contacts[1].name)
		bob.first_name = "Robert"
		bob.save()

	def test_contacts_are_only_listed_for_directory_doctypes(self):
		frappe.set_user(MEMBER)
		with self.assertRaises(frappe.ValidationError):
			get_contacts("User", MEMBER)
