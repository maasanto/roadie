import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class Gig(Document):
	def validate(self):
		if (
			self.application_opens
			and self.application_closes
			and getdate(self.application_opens) > getdate(self.application_closes)
		):
			frappe.throw(
				_("Application opens {0} after it closes {1}").format(
					self.application_opens, self.application_closes
				),
				title=_("Invalid dates"),
			)
