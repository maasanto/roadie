import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, get_url, today

from roadie.api import get_notifications, mark_notifications_read
from roadie.roadie.doctype.gig.test_gig import MEMBER, OTHER_MEMBER, make_member
from roadie.tests.test_reminders import GIG_REMINDER, TASK_REMINDER, run_daily_reminder


def notifications_for(user, document_name):
	return frappe.get_all(
		"Notification Log",
		filters={"for_user": user, "document_name": document_name},
		fields=["name", "subject", "read"],
	)


class TestNotifications(IntegrationTestCase):
	def setUp(self):
		make_member(MEMBER, "John")
		make_member(OTHER_MEMBER, "Jane")
		# A test class shares one transaction, so notifications from the earlier tests would show up in the later ones.
		frappe.db.delete("Notification Log", {"for_user": ["in", (MEMBER, OTHER_MEMBER)]})

	def tearDown(self):
		frappe.set_user("Administrator")

	def enable_in_app(self, notification):
		"""The fixture drives this on a fresh site; set it here so the test does not depend on when the fixtures last synced."""
		current = frappe.db.get_value("Notification", notification, "send_system_notification")
		frappe.db.set_value("Notification", notification, "send_system_notification", 1)
		self.addCleanup(
			frappe.db.set_value, "Notification", notification, "send_system_notification", current
		)

	def test_assigning_a_task_to_another_member_notifies_them(self):
		frappe.set_user(MEMBER)
		task = frappe.get_doc(
			{"doctype": "Band Task", "title": "Send the rider", "assignee": OTHER_MEMBER}
		).insert()

		[notification] = notifications_for(OTHER_MEMBER, task.name)
		self.assertIn("Send the rider", notification.subject)
		self.assertFalse(notification.read)

	def test_self_assignment_does_not_notify(self):
		frappe.set_user(MEMBER)
		task = frappe.get_doc(
			{"doctype": "Band Task", "title": "Send the rider", "assignee": MEMBER}
		).insert()

		self.assertFalse(notifications_for(MEMBER, task.name))

	def test_reassigning_a_task_notifies_the_new_assignee(self):
		frappe.set_user(MEMBER)
		task = frappe.get_doc(
			{"doctype": "Band Task", "title": "Send the rider", "assignee": MEMBER}
		).insert()
		task.assignee = OTHER_MEMBER
		task.save()

		[notification] = notifications_for(OTHER_MEMBER, task.name)
		self.assertIn("Send the rider", notification.subject)

	def test_a_task_due_today_notifies_its_assignee(self):
		self.enable_in_app(TASK_REMINDER)
		frappe.set_user(MEMBER)
		task = frappe.get_doc(
			{"doctype": "Band Task", "title": "Send the rider", "assignee": MEMBER, "due_date": today()}
		).insert()

		frappe.set_user("Administrator")
		run_daily_reminder(TASK_REMINDER)

		[notification] = notifications_for(MEMBER, task.name)
		self.assertEqual(notification.subject, "Due today: Send the rider")

	def test_a_gig_closing_in_seven_days_notifies_its_owner(self):
		self.enable_in_app(GIG_REMINDER)
		frappe.set_user(MEMBER)
		gig = frappe.get_doc(
			{"doctype": "Gig", "title": "Acme Festival 2027", "application_closes": add_days(today(), 7)}
		).insert()

		frappe.set_user("Administrator")
		run_daily_reminder(GIG_REMINDER)

		[notification] = notifications_for(MEMBER, gig.name)
		self.assertIn("Acme Festival 2027", notification.subject)

	def test_get_notifications_returns_only_the_current_users_entries(self):
		frappe.set_user(MEMBER)
		frappe.get_doc({"doctype": "Band Task", "title": "Send the rider", "assignee": MEMBER}).insert()
		frappe.get_doc({"doctype": "Band Task", "title": "Book the van", "assignee": OTHER_MEMBER}).insert()

		frappe.set_user(OTHER_MEMBER)
		notifications = get_notifications()

		self.assertEqual([n.subject for n in notifications], ["John Doe assigned you a task: Book the van"])
		self.assertEqual([n.route for n in notifications], ["/tasks"])

	def test_a_route_never_repeats_the_base_the_router_already_carries(self):
		# A mention carries a site path in its link and has no entry in NOTIFICATION_ROUTES.
		frappe.set_user(MEMBER)
		festival = frappe.get_doc({"doctype": "Festival", "title": "Acme Festival"}).insert()
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"for_user": MEMBER,
				"type": "Mention",
				"document_type": "Festival",
				"document_name": festival.name,
				"subject": "Jane Doe mentioned you in a comment",
				"link": get_url("/roadie/directory"),
			}
		).insert(ignore_permissions=True)

		[notification] = get_notifications()
		self.assertEqual(notification.route, "/directory")

	def test_mark_notifications_read_clears_unread(self):
		frappe.set_user(MEMBER)
		frappe.get_doc({"doctype": "Band Task", "title": "Book the van", "assignee": OTHER_MEMBER}).insert()

		frappe.set_user(OTHER_MEMBER)
		[notification] = get_notifications()
		mark_notifications_read([notification.name])

		self.assertEqual([n.name for n in get_notifications() if not n.read], [])
