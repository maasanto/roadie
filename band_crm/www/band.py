import frappe
from frappe import _

no_cache = 1


def get_context():
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/band"
		raise frappe.Redirect

	if not frappe.has_permission("Gig", "read"):
		frappe.throw(_("Only band members can open the band CRM"), frappe.PermissionError)

	return frappe._dict(
		boot={
			"csrf_token": frappe.sessions.get_csrf_token(),
			"user": frappe.session.user,
		}
	)
