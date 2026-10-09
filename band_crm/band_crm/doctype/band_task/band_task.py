import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class BandTask(Document):
	def validate(self):
		if self.start_date and self.due_date and getdate(self.start_date) > getdate(self.due_date):
			frappe.throw(
				_("Start date {0} is after due date {1}").format(self.start_date, self.due_date),
				title=_("Invalid dates"),
			)
