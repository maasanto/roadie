import frappe

from roadie.api import DIRECTORY_DOCTYPES

RELEVANCE_COLUMN = {"fieldname": "relevance", "label": "Relevance", "format": "rating"}


def execute():
	"""A saved layout replaces the defaults, so without this a site that saved its columns would sort every
	directory by a relevance it never shows."""
	layouts = (
		frappe.parse_json(frappe.db.get_single_value("Roadie Settings", "directory_columns") or "{}") or {}
	)
	for doctype in DIRECTORY_DOCTYPES:
		columns = layouts.get(doctype) or []
		if columns and not any(column.get("fieldname") == "relevance" for column in columns):
			# Next to the name, where the defaults put it.
			columns.insert(1, dict(RELEVANCE_COLUMN))

	frappe.db.set_single_value("Roadie Settings", "directory_columns", frappe.as_json(layouts))
