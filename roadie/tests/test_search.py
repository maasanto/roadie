import frappe
from frappe.tests import IntegrationTestCase

from roadie.api import search
from roadie.roadie.doctype.gig.test_gig import MEMBER, make_member

OUTSIDER = "outsider@example.com"


def results_by_type(groups):
	return {group["doctype"]: group["results"] for group in groups}


class TestSearch(IntegrationTestCase):
	def setUp(self):
		make_member(MEMBER, "John")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_matches_are_grouped_by_doc_type(self):
		frappe.set_user(MEMBER)
		frappe.get_doc({"doctype": "Gig", "title": "Zqx Summer Fest"}).insert()
		frappe.get_doc({"doctype": "Festival", "title": "Zqx Festival", "city": "Lyon"}).insert()

		groups = search("zqx")

		self.assertEqual([group["doctype"] for group in groups], ["Gig", "Festival"])
		self.assertEqual(results_by_type(groups)["Gig"][0]["title"], "Zqx Summer Fest")

	def test_an_empty_query_returns_nothing(self):
		frappe.set_user(MEMBER)
		frappe.get_doc({"doctype": "Gig", "title": "Zqempty"}).insert()

		self.assertEqual(search("   "), [])

	def test_matches_on_title_and_on_city(self):
		frappe.set_user(MEMBER)
		frappe.get_doc({"doctype": "Venue", "title": "Zqvenue Hall", "city": "Zqcity"}).insert()
		frappe.get_doc({"doctype": "Promoter", "title": "Zqpromo Live"}).insert()

		by_city = results_by_type(search("zqcity"))
		by_title = results_by_type(search("zqpromo"))

		self.assertEqual([row["title"] for row in by_city["Venue"]], ["Zqvenue Hall"])
		self.assertNotIn("Promoter", by_city)
		self.assertEqual([row["title"] for row in by_title["Promoter"]], ["Zqpromo Live"])

	def test_each_group_is_capped(self):
		frappe.set_user(MEMBER)
		for index in range(7):
			frappe.get_doc({"doctype": "Gig", "title": f"Zqcap {index}"}).insert()

		self.assertEqual(len(results_by_type(search("zqcap"))["Gig"]), 5)

	def test_a_user_without_a_band_role_sees_nothing(self):
		frappe.set_user("Administrator")
		frappe.get_doc({"doctype": "Gig", "title": "Zqperm"}).insert()
		if not frappe.db.exists("User", OUTSIDER):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": OUTSIDER,
					"first_name": "Out",
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)

		frappe.set_user(OUTSIDER)

		self.assertEqual(search("zqperm"), [])
