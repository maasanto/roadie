import frappe
from frappe.model.document import Document


class Festival(Document):
	def on_trash(self):
		# Roadie has no screen to delete an edition, so a festival takes its own along; one a gig still points at
		# refuses, which keeps the festival too.
		for edition in frappe.get_all("Festival Edition", filters={"festival": self.name}, pluck="name"):
			frappe.delete_doc("Festival Edition", edition, ignore_permissions=True)
