import frappe
from frappe.email.doctype.notification.notification import evaluate_alert
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from roadie.roadie.doctype.gig.test_gig import MEMBER, make_member

GIG_REMINDER = "Gig Application Closes in 7 Days"
TASK_REMINDER = "Band Task Due Today"


def run_daily_reminder(notification_name):
	"""trigger_daily_alerts without its per-document commit, which would leak test data."""
	notification = frappe.get_doc("Notification", notification_name)
	documents = notification.get_documents_for_today()
	for document in documents:
		evaluate_alert(document, notification, notification.event)
	return [document.name for document in documents]


def queued_reminders(reference_doctype, reference_name):
	return frappe.get_all(
		"Email Queue",
		filters={"reference_doctype": reference_doctype, "reference_name": reference_name},
		pluck="name",
	)


class TestReminders(IntegrationTestCase):
	def setUp(self):
		make_member(MEMBER, "John")
		frappe.set_user(MEMBER)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_owner_is_emailed_seven_days_before_the_application_closes(self):
		closing = frappe.get_doc(
			{"doctype": "Gig", "title": "Acme Festival 2027", "application_closes": add_days(today(), 7)}
		).insert()
		already_applied = frappe.get_doc(
			{
				"doctype": "Gig",
				"title": "Acme Open Air 2027",
				"status": "Applied",
				"application_closes": add_days(today(), 7),
			}
		).insert()
		later = frappe.get_doc(
			{"doctype": "Gig", "title": "Acme Winter 2027", "application_closes": add_days(today(), 8)}
		).insert()

		frappe.set_user("Administrator")
		run_daily_reminder(GIG_REMINDER)

		[queued] = queued_reminders("Gig", closing.name)
		self.assertEqual(
			frappe.get_all("Email Queue Recipient", {"parent": queued}, pluck="recipient"), [MEMBER]
		)
		self.assertIn(
			"Acme Festival 2027 closes in 7 days", frappe.db.get_value("Email Queue", queued, "message")
		)
		self.assertFalse(queued_reminders("Gig", already_applied.name))
		self.assertFalse(queued_reminders("Gig", later.name))

	def test_gig_reminder_is_translated_and_states_the_notification_lead_time(self):
		lead_time = frappe.db.get_value("Notification", GIG_REMINDER, "days_in_advance")
		self.addCleanup(frappe.db.set_value, "Notification", GIG_REMINDER, "days_in_advance", lead_time)
		frappe.db.set_value("Notification", GIG_REMINDER, "days_in_advance", 3)
		closing = frappe.get_doc(
			{"doctype": "Gig", "title": "Acme Festival 2027", "application_closes": add_days(today(), 3)}
		).insert()

		frappe.set_user("Administrator")
		frappe.local.lang = "fr"
		self.addCleanup(setattr, frappe.local, "lang", "en")
		run_daily_reminder(GIG_REMINDER)

		reminder = frappe.db.get_value(
			"Communication",
			{"reference_doctype": "Gig", "reference_name": closing.name},
			["subject", "content"],
			as_dict=True,
		)
		self.assertEqual(reminder.subject, "Les candidatures pour Acme Festival 2027 ferment dans 3 jours")
		self.assertIn("dans 3 jours, et le concert est toujours au statut « Idée »", reminder.content)

	def test_assignee_is_emailed_on_the_due_date_of_an_open_task(self):
		due = frappe.get_doc(
			{"doctype": "Band Task", "title": "Send the rider", "assignee": MEMBER, "due_date": today()}
		).insert()
		done = frappe.get_doc(
			{
				"doctype": "Band Task",
				"title": "Book the van",
				"assignee": MEMBER,
				"due_date": today(),
				"done": 1,
			}
		).insert()

		frappe.set_user("Administrator")
		run_daily_reminder(TASK_REMINDER)

		[queued] = queued_reminders("Band Task", due.name)
		self.assertEqual(
			frappe.get_all("Email Queue Recipient", {"parent": queued}, pluck="recipient"), [MEMBER]
		)
		self.assertFalse(queued_reminders("Band Task", done.name))
