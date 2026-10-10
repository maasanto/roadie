import json

import frappe
from frappe.tests import IntegrationTestCase

from roadie.roadie.doctype.gig.test_gig import MEMBER, OTHER_MEMBER, make_member


class TestDirectoryColumns(IntegrationTestCase):
	def setUp(self):
		make_member(MEMBER, "John")
		make_member(OTHER_MEMBER, "Jane")
		# The runner rolls back once per class, not per test, so rows an earlier test left behind are still here.
		frappe.db.delete("Roadie List View")

	def tearDown(self):
		frappe.set_user("Administrator")

	def make_view(self, dt="Festival", columns='[{"fieldname": "title"}]'):
		return frappe.get_doc({"doctype": "Roadie List View", "dt": dt, "columns": columns}).insert()

	def test_a_member_lists_only_their_own_layout(self):
		frappe.set_user(MEMBER)
		mine = self.make_view()
		frappe.set_user(OTHER_MEMBER)
		self.make_view()

		frappe.set_user(MEMBER)
		views = frappe.get_list("Roadie List View", fields=["name"])

		self.assertEqual([view.name for view in views], [mine.name])

	def test_a_member_cannot_read_another_members_layout(self):
		frappe.set_user(OTHER_MEMBER)
		theirs = self.make_view()

		frappe.set_user(MEMBER)
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc("Roadie List View", theirs.name).check_permission("read")

	def test_a_second_layout_for_the_same_doctype_is_refused(self):
		frappe.set_user(MEMBER)
		self.make_view()

		with self.assertRaises(frappe.ValidationError):
			self.make_view()

	def test_each_doctype_keeps_its_own_layout(self):
		frappe.set_user(MEMBER)
		self.make_view("Festival")
		self.make_view("Venue")

		views = frappe.get_list("Roadie List View", fields=["dt"])

		self.assertEqual(sorted(view.dt for view in views), ["Festival", "Venue"])

	def test_a_column_naming_a_field_the_doctype_does_not_have_is_dropped(self):
		frappe.set_user(MEMBER)
		view = self.make_view(
			"Festival",
			json.dumps(
				[
					{"fieldname": "title", "label": "Name"},
					{"fieldname": "field_renamed_in_desk", "label": "Gone"},
				]
			),
		)

		self.assertEqual(json.loads(view.columns), [{"fieldname": "title", "label": "Name"}])

	def test_columns_that_are_not_a_list_of_columns_are_refused(self):
		frappe.set_user(MEMBER)

		with self.assertRaises(frappe.ValidationError):
			self.make_view("Festival", '{"fieldname": "title"}')
