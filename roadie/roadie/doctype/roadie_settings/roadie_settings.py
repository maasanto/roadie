import frappe
from frappe import _
from frappe.model.document import Document


class RoadieSettings(Document):
	pass


def clean_columns(doctype, columns: list) -> list:
	"""Keep the columns the DocType can still show: a renamed or removed field would break the list reading it."""
	if not isinstance(columns, list):
		frappe.throw(_("Columns has to be a list of columns"))

	fields = {field.fieldname for field in frappe.get_meta(doctype).fields}

	return [
		{
			"fieldname": column["fieldname"],
			"label": column.get("label") or column["fieldname"],
			"format": column.get("format"),
		}
		for column in columns
		if isinstance(column, dict) and column.get("fieldname") in fields
	]
