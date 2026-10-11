import frappe

from roadie.roadie.doctype.roadie_list_view.roadie_list_view import drop_duplicates, ensure_unique_index


def execute():
	"""Existing sites: the rows a race inserted before the constraint existed go first, then the constraint."""
	drop_duplicates()
	ensure_unique_index()
