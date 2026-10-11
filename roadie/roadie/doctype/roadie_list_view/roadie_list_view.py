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


UNIQUE_INDEX = "unique_list_view_per_member"


def ensure_unique_index():
	"""Hold one layout per member per DocType in the database, not only in `validate`.

	Called by the patch that backfills existing sites and by `after_install`, because installing an app marks
	its patches as completed instead of running them: on a fresh site the install hook is the only caller.
	`add_unique` is idempotent, so both paths can ask without checking.
	"""
	frappe.db.add_unique("Roadie List View", ["dt", "owner"], constraint_name=UNIQUE_INDEX)


def drop_duplicates():
	"""Two tabs could insert a layout each before the constraint existed; the screen reads the newest row."""
	rows = frappe.get_all("Roadie List View", fields=["name", "dt", "owner"], order_by="modified desc")

	for name in names_to_drop(rows):
		frappe.db.delete("Roadie List View", {"name": name})


def names_to_drop(rows):
	"""The rows repeating a `dt`/`owner` pair already seen in `rows`, which are ordered newest first."""
	seen = set()
	repeated = []
	for row in rows:
		key = (row["dt"], row["owner"])
		if key in seen:
			repeated.append(row["name"])
		else:
			seen.add(key)
	return repeated
