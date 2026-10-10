from frappe.model.document import Document


class Gig(Document):
	def validate(self):
		self.validate_from_to_dates("application_opens", "application_closes")
