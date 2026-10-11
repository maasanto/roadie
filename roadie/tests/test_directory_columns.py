import json

import frappe
from frappe.tests import IntegrationTestCase

from roadie.api import delete_list_view
from roadie.roadie.doctype.gig.test_gig import MEMBER, OTHER_MEMBER, make_member
from roadie.roadie.doctype.roadie_list_view.roadie_list_view import ensure_unique_index, names_to_drop


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

	def test_a_system_manager_still_reads_only_their_own_layout(self):
		"""System Manager carries if_owner too: a member who is also one must not inherit everyone's rows."""
		frappe.set_user(MEMBER)
		self.make_view()
		frappe.set_user(OTHER_MEMBER)
		frappe.get_doc("User", OTHER_MEMBER).add_roles("System Manager")
		frappe.clear_cache(user=OTHER_MEMBER)
		theirs = self.make_view()

		views = frappe.get_list("Roadie List View", fields=["name"])

		self.assertEqual([view.name for view in views], [theirs.name])

	def test_deleting_a_layout_clears_this_members_rows_for_that_doctype(self):
		frappe.set_user(MEMBER)
		self.make_view("Festival")
		venue = self.make_view("Venue")
		frappe.set_user(OTHER_MEMBER)
		theirs = self.make_view("Festival")

		frappe.set_user(MEMBER)
		delete_list_view("Festival")

		self.assertEqual([view.dt for view in frappe.get_list("Roadie List View", fields=["dt"])], ["Venue"])
		frappe.set_user(OTHER_MEMBER)
		self.assertEqual(
			[view.name for view in frappe.get_list("Roadie List View", fields=["name"])], [theirs.name]
		)
		self.assertEqual(frappe.db.get_value("Roadie List View", venue.name, "name"), venue.name)

	def test_only_the_older_of_two_rows_for_one_layout_is_given_up(self):
		rows = [
			{"name": "newest", "dt": "Festival", "owner": MEMBER},
			{"name": "older", "dt": "Festival", "owner": MEMBER},
			{"name": "other-doctype", "dt": "Venue", "owner": MEMBER},
			{"name": "other-member", "dt": "Festival", "owner": OTHER_MEMBER},
		]

		self.assertEqual(names_to_drop(rows), ["older"])

	def test_the_database_refuses_a_second_row_for_the_same_doctype(self):
		"""validate is not the only guard: bypassing it must fail too, which is what stops two tabs each inserting."""
		frappe.set_user(MEMBER)
		self.make_view()

		duplicate = frappe.get_doc({"doctype": "Roadie List View", "dt": "Festival", "columns": "[]"})
		duplicate.name = "duplicate-layout"
		duplicate.owner = MEMBER

		with self.assertRaisesRegex(Exception, "Duplicate entry 'Festival-"):
			duplicate.db_insert()

	def test_the_constraint_can_be_asked_for_more_than_once(self):
		"""after_install asks on every install and the patch asks on every migrate, so the call has to be safe."""
		ensure_unique_index()
		ensure_unique_index()

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
