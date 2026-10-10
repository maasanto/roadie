import frappe
from frappe.tests import IntegrationTestCase

from roadie.api import get_contacts, unlink_contact
from roadie.install import grant_contact_access
from roadie.roadie.doctype.gig.test_gig import MEMBER, make_member


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
		make_member(MEMBER, "John")

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

	def test_removing_a_contact_from_a_venue_keeps_it_on_its_promoter(self):
		frappe.set_user(MEMBER)
		venue = frappe.get_doc({"doctype": "Venue", "title": "Le Petit Club"}).insert()
		promoter = frappe.get_doc({"doctype": "Promoter", "title": "Acme Live"}).insert()
		bob = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "Bob",
				"links": [
					{"link_doctype": "Venue", "link_name": venue.name},
					{"link_doctype": "Promoter", "link_name": promoter.name},
				],
			}
		).insert()

		unlink_contact(bob.name, "Venue", venue.name)

		self.assertEqual(get_contacts("Venue", venue.name), [])
		self.assertEqual([contact.name for contact in get_contacts("Promoter", promoter.name)], [bob.name])

	def test_festival_refuses_an_application_window_that_closes_before_it_opens(self):
		frappe.set_user(MEMBER)
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Festival",
					"title": "Acme Festival",
					"application_opens": "2027-03-01",
					"application_closes": "2027-01-31",
				}
			).insert()

	def test_contacts_are_only_listed_for_directory_doctypes(self):
		frappe.set_user(MEMBER)
		with self.assertRaises(frappe.ValidationError):
			get_contacts("User", MEMBER)
