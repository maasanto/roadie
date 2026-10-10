import json

import frappe
from frappe import _
from frappe.model.document import Document


class RoadieListView(Document):
	def validate(self):
		self.check_one_view_per_doctype()
		self.drop_unknown_columns()

	def check_one_view_per_doctype(self):
		"""A second row for the same DocType would split one member's layout in two, and the SPA reads one."""
		if frappe.db.exists(
			"Roadie List View",
			{"dt": self.dt, "owner": frappe.session.user, "name": ["!=", self.name]},
		):
			frappe.throw(_("You already have a saved column layout for {0}").format(_(self.dt)))

	def drop_unknown_columns(self):
		"""A column naming a field the DocType no longer has would break the list it belongs to, so it goes on
		the way in: the row is a Code field anyone can hand-edit in Desk."""
		columns = frappe.parse_json(self.columns) if self.columns else []
		if not isinstance(columns, list):
			frappe.throw(_("Columns has to be a list of columns"))

		fields = {field.fieldname for field in frappe.get_meta(self.dt).fields}
		kept = [
			column for column in columns if isinstance(column, dict) and column.get("fieldname") in fields
		]
		self.columns = json.dumps(kept)
