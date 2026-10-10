import frappe
from frappe.permissions import add_permission, reset_perms, rights, update_permission_property

ROLE = "Band Member"
GRANTED_DOCTYPES = ("Contact", "Communication")


def after_install():
	grant_contact_access()
	grant_communication_access()


def after_uninstall():
	for doctype in GRANTED_DOCTYPES:
		revoke_member_access(doctype)


def revoke_member_access(doctype):
	"""Granting access copied the standard rules into Custom DocPerm, which override them from then on. Once the
	member rule is gone, an untouched copy is dropped so the standard rules apply again; an edited one stays."""
	frappe.db.delete("Custom DocPerm", {"parent": doctype, "role": ROLE})
	if _permission_rules("Custom DocPerm", doctype) == _permission_rules("DocPerm", doctype):
		reset_perms(doctype)
	frappe.clear_cache(doctype=doctype)


def _permission_rules(perm_doctype, doctype):
	return set(
		frappe.get_all(
			perm_doctype,
			filters={"parent": doctype},
			fields=["role", "permlevel", "if_owner", *rights],
			as_list=True,
		)
	)


def grant_contact_access():
	"""Contacts are a core DocType, so members get a custom rule on top of its standard ones."""
	if frappe.db.exists("Custom DocPerm", {"parent": "Contact", "role": ROLE, "permlevel": 0}):
		return
	add_permission("Contact", ROLE)
	for ptype in ("write", "create", "delete"):
		update_permission_property("Contact", ROLE, 0, ptype, 1)


def grant_communication_access():
	"""Read defers to the linked record, so members open received attachments. Write and email let them reply to
	mail linked to no record, which Frappe threads on the first Communication itself."""
	if not frappe.db.exists("Custom DocPerm", {"parent": "Communication", "role": ROLE, "permlevel": 0}):
		add_permission("Communication", ROLE)
	for ptype in ("write", "email"):
		update_permission_property("Communication", ROLE, 0, ptype, 1)
