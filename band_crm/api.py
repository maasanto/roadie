import frappe
from frappe import _

DIRECTORY_DOCTYPES = ("Festival", "Venue", "Promoter", "Band")


@frappe.whitelist()
def get_contacts(doctype: str, name: str) -> list[dict]:
	if doctype not in DIRECTORY_DOCTYPES:
		frappe.throw(
			_("Contacts can only be listed for {0}, not {1}").format(", ".join(DIRECTORY_DOCTYPES), doctype)
		)
	frappe.get_doc(doctype, name).check_permission("read")

	return frappe.get_list(
		"Contact",
		filters=[["Dynamic Link", "link_doctype", "=", doctype], ["Dynamic Link", "link_name", "=", name]],
		fields=["name", "full_name", "email_id", "phone", "mobile_no"],
		order_by="creation asc",
	)


@frappe.whitelist()
def get_attachments(gig: str) -> list[dict]:
	"""Members are website users, and File only lists those to the uploader, so the gig grants access."""
	frappe.get_doc("Gig", gig).check_permission("read")

	return frappe.get_all(
		"File",
		filters={"attached_to_doctype": "Gig", "attached_to_name": gig},
		fields=["name", "file_name", "file_url", "file_size", "owner", "creation"],
		order_by="creation asc",
	)


@frappe.whitelist()
def get_members() -> list[dict]:
	frappe.only_for(("Band Member", "System Manager"))

	return frappe.get_all(
		"User",
		filters=[["Has Role", "role", "=", "Band Member"], ["enabled", "=", 1]],
		fields=["name", "full_name", "user_image"],
		order_by="full_name asc",
		distinct=True,
	)
