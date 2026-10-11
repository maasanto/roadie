import frappe
from frappe.tests import IntegrationTestCase

from roadie.api import get_directory_quick_filters, set_directory_quick_filters
from roadie.roadie.doctype.gig.test_gig import MEMBER, OTHER_MEMBER, make_member

DOCTYPE = "Festival"


class TestDirectoryQuickFilters(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		make_member(MEMBER, "John")
		make_member(OTHER_MEMBER, "Jane")
		frappe.set_user(MEMBER)
		# A site-wide setting outlives a test the way a real setting does, so each test starts from none saved.
		frappe.db.set_single_value("Roadie Settings", "directory_quick_filters", "")

	def tearDown(self):
		frappe.db.set_single_value("Roadie Settings", "directory_quick_filters", "")
		frappe.set_user("Administrator")
		super().tearDown()

	def test_one_members_quick_filters_are_what_another_member_reads(self):
		set_directory_quick_filters(DOCTYPE, '["city", "relevance"]')

		frappe.set_user(OTHER_MEMBER)
		self.assertEqual(get_directory_quick_filters(), {DOCTYPE: ["city", "relevance"]})

	def test_saving_one_type_leaves_the_others_quick_filters_alone(self):
		set_directory_quick_filters("Venue", '["capacity"]')
		set_directory_quick_filters(DOCTYPE, '["city"]')

		self.assertEqual(get_directory_quick_filters(), {"Venue": ["capacity"], DOCTYPE: ["city"]})

	def test_an_empty_list_is_kept_so_a_type_can_have_no_quick_filters(self):
		set_directory_quick_filters(DOCTYPE, "[]")

		self.assertEqual(get_directory_quick_filters(), {DOCTYPE: []})

	def test_unknown_and_repeated_fields_are_dropped(self):
		set_directory_quick_filters(DOCTYPE, '["city", "gone", {"fieldname": "title"}, "city"]')

		self.assertEqual(get_directory_quick_filters()[DOCTYPE], ["city"])

	def test_quick_filters_that_are_not_a_list_are_refused(self):
		with self.assertRaises(frappe.ValidationError):
			set_directory_quick_filters(DOCTYPE, '"city"')

	def test_a_doctype_that_is_not_a_directory_list_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			set_directory_quick_filters("Gig", "[]")

	def test_a_guest_reads_and_writes_nothing(self):
		frappe.set_user("Guest")

		with self.assertRaises(frappe.PermissionError):
			get_directory_quick_filters()
		with self.assertRaises(frappe.PermissionError):
			set_directory_quick_filters(DOCTYPE, "[]")
