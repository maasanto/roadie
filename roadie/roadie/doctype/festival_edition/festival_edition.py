from frappe.model.document import Document


class FestivalEdition(Document):
	def validate(self):
		self.validate_from_to_dates("start_date", "end_date")
		self.validate_from_to_dates("application_opens", "application_closes")
