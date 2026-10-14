import frappe
from frappe.client import set_value
from frappe.tests import IntegrationTestCase

from roadie.roadie.doctype.gig.test_gig import MEMBER, OTHER_MEMBER, make_member


class TestBandTask(IntegrationTestCase):
	def setUp(self):
		make_member(MEMBER, "John")
		make_member(OTHER_MEMBER, "Jane")

	def tearDown(self):
		frappe.set_user("Administrator")

	def my_open_tasks(self):
		return frappe.get_list(
			"Band Task",
			filters={"assignee": frappe.session.user, "done": 0},
			fields=["name", "title", "gig.title as gig_title"],
		)

	def test_task_assigned_by_a_teammate_shows_in_my_tasks_until_ticked(self):
		frappe.set_user(OTHER_MEMBER)
		gig = frappe.get_doc({"doctype": "Gig", "title": "Acme Festival 2027"}).insert()
		task = frappe.get_doc(
			{
				"doctype": "Band Task",
				"title": "Send the rider",
				"assignee": MEMBER,
				"gig": gig.name,
				"due_date": "2027-01-15",
			}
		).insert()

		frappe.set_user(MEMBER)
		self.assertIn(
			{"name": task.name, "title": "Send the rider", "gig_title": "Acme Festival 2027"},
			self.my_open_tasks(),
		)

		set_value("Band Task", task.name, "done", 1)

		self.assertEqual(frappe.db.get_value("Band Task", task.name, "done"), 1)
		self.assertNotIn(task.name, [row.name for row in self.my_open_tasks()])

	def test_member_sees_unassigned_and_teammates_tasks_outside_mine(self):
		unassigned = frappe.get_doc({"doctype": "Band Task", "title": "Book the hotel"}).insert()
		teammates = frappe.get_doc(
			{"doctype": "Band Task", "title": "Pick up the PA", "assignee": OTHER_MEMBER}
		).insert()

		frappe.set_user(MEMBER)
		unassigned_scope = frappe.get_list("Band Task", filters={"assignee": ["is", "not set"]}, pluck="name")
		everyone_scope = frappe.get_list("Band Task", pluck="name")

		self.assertIn(unassigned.name, unassigned_scope)
		self.assertNotIn(teammates.name, unassigned_scope)
		self.assertIn(unassigned.name, everyone_scope)
		self.assertIn(teammates.name, everyone_scope)

	def test_start_date_after_due_date_is_rejected(self):
		task = frappe.get_doc(
			{
				"doctype": "Band Task",
				"title": "Book the van",
				"start_date": "2027-02-01",
				"due_date": "2027-01-15",
			}
		)
		self.assertRaises(frappe.ValidationError, task.insert)
