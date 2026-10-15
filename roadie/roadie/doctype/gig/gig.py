import frappe
from frappe import _
from frappe.model.document import Document


class Gig(Document):
	def validate(self):
		self.validate_from_to_dates("application_opens", "application_closes")
		self.validate_festival_edition()

	def validate_festival_edition(self):
		if not self.festival_edition:
			return
		edition_festival, year = frappe.db.get_value(
			"Festival Edition", self.festival_edition, ["festival", "year"]
		)
		if edition_festival != self.festival:
			frappe.throw(
				_(
					"The {0} edition belongs to another festival. Pick an edition of this gig's festival."
				).format(year)
			)
