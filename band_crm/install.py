import frappe
from frappe.permissions import add_permission, update_permission_property

ROLE = "Band Member"


def after_install():
	grant_contact_access()


def grant_contact_access():
	"""Contacts are a core DocType, so members get a custom rule on top of its standard ones."""
	if frappe.db.exists("Custom DocPerm", {"parent": "Contact", "role": ROLE, "permlevel": 0}):
		return
	add_permission("Contact", ROLE)
	for ptype in ("write", "create", "delete"):
		update_permission_property("Contact", ROLE, 0, ptype, 1)
