import frappe
from frappe.tests import IntegrationTestCase

from roadie.api import get_directory_columns, set_directory_columns
from roadie.patches import add_relevance_column
from roadie.roadie.doctype.gig.test_gig import MEMBER, OTHER_MEMBER, make_member

DOCTYPE = "Festival"


class TestDirectoryColumns(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		make_member(MEMBER, "John")
		make_member(OTHER_MEMBER, "Jane")
		frappe.set_user(MEMBER)
		# A site-wide setting outlives a test the way a real setting does, so each test starts from no columns.
		frappe.db.set_single_value("Roadie Settings", "directory_columns", "")

	def tearDown(self):
		frappe.db.set_single_value("Roadie Settings", "directory_columns", "")
		frappe.set_user("Administrator")
		super().tearDown()

	def columns(self, doctype=DOCTYPE):
		return get_directory_columns().get(doctype) or []

	def test_a_saved_layout_comes_back_for_its_own_type(self):
		set_directory_columns(DOCTYPE, '[{"fieldname": "city", "label": "City"}]')

		self.assertEqual([column["fieldname"] for column in self.columns()], ["city"])
		self.assertEqual(self.columns("Venue"), [])

	def test_an_empty_layout_puts_the_type_back_on_its_defaults(self):
		set_directory_columns(DOCTYPE, '[{"fieldname": "city", "label": "City"}]')
		set_directory_columns(DOCTYPE, "[]")

		self.assertEqual(self.columns(), [])

	def test_a_column_naming_a_field_the_doctype_does_not_have_is_dropped(self):
		set_directory_columns(
			DOCTYPE, '[{"fieldname": "title", "label": "Name"}, {"fieldname": "gone", "label": "Gone"}]'
		)

		self.assertEqual([column["fieldname"] for column in self.columns()], ["title"])

	def test_columns_that_are_not_a_list_are_refused(self):
		with self.assertRaises(frappe.ValidationError):
			set_directory_columns(DOCTYPE, '{"fieldname": "title"}')

	def test_a_doctype_that_is_not_a_directory_list_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			set_directory_columns("Gig", "[]")

	def test_one_members_change_is_what_another_member_reads(self):
		"""The columns are edited globally: there is one layout, not one per member."""
		set_directory_columns(DOCTYPE, '[{"fieldname": "instagram", "label": "Instagram"}]')

		frappe.set_user(OTHER_MEMBER)
		self.assertEqual([column["fieldname"] for column in self.columns()], ["instagram"])

	def test_a_layout_saved_before_relevance_existed_gains_it_next_to_the_name(self):
		set_directory_columns(
			DOCTYPE, '[{"fieldname": "title", "label": "Name"}, {"fieldname": "city", "label": "City"}]'
		)
		set_directory_columns(
			"Venue", '[{"fieldname": "title"}, {"fieldname": "relevance", "format": "rating"}]'
		)

		add_relevance_column.execute()
		add_relevance_column.execute()

		self.assertEqual([column["fieldname"] for column in self.columns()], ["title", "relevance", "city"])
		self.assertEqual([column["fieldname"] for column in self.columns("Venue")], ["title", "relevance"])
		self.assertEqual(self.columns("Band"), [])

	def test_a_guest_reads_and_writes_nothing(self):
		frappe.set_user("Guest")

		with self.assertRaises(frappe.PermissionError):
			get_directory_columns()
		with self.assertRaises(frappe.PermissionError):
			set_directory_columns(DOCTYPE, "[]")
