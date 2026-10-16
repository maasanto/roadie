import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import escape_html


class FestivalEdition(Document):
	def validate(self):
		self.validate_from_to_dates("start_date", "end_date")
		self.validate_from_to_dates("application_opens", "application_closes")
		self.validate_unique_year()

	def validate_unique_year(self):
		# Only on a new year, so a site that already holds a duplicate pair can still edit and use both.
		if not (self.is_new() or self.has_value_changed("year")):
			return
		if frappe.db.exists(
			"Festival Edition", {"festival": self.festival, "year": self.year, "name": ("!=", self.name)}
		):
			frappe.throw(
				_("{0} already has a {1} edition. Open that one, or pick another year.").format(
					escape_html(frappe.get_cached_value("Festival", self.festival, "title")), self.year
				)
			)
