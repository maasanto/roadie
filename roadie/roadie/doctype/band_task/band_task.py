import frappe
from frappe import _
from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification
from frappe.model.document import Document
from frappe.utils import get_fullname, get_url, getdate

from roadie.mentions import record_path


class BandTask(Document):
	def validate(self):
		if self.start_date and self.due_date and getdate(self.start_date) > getdate(self.due_date):
			frappe.throw(
				_("Start date {0} is after due date {1}").format(self.start_date, self.due_date),
				title=_("Invalid dates"),
			)

	def on_update(self):
		# Frappe runs on_update on insert too, and has_value_changed is True for a new assignee.
		if self.has_value_changed("assignee"):
			self.notify_assignee()

	def notify_assignee(self):
		"""Frappe's built-in assignment notifications are Desk-only, and members never open the Desk, so the assignee is told here."""
		actor = frappe.session.user
		if not self.assignee or self.assignee == actor:
			return
		email = frappe.db.get_value("User", self.assignee, "email")
		if not email:
			return

		enqueue_create_notification(
			[email],
			{
				"type": "Alert",
				"document_type": self.doctype,
				"document_name": self.name,
				"from_user": actor,
				"subject": _("{0} assigned you a task: {1}").format(get_fullname(actor), self.title),
				"link": get_url(record_path(self.doctype, self.name)),
			},
		)
