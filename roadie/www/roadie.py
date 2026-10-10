import frappe
from frappe import _
from frappe.translate import get_translations_from_apps

from roadie.api import can_use_drive

no_cache = 1


def get_context():
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/roadie"
		raise frappe.Redirect

	if not frappe.has_permission("Gig", "read"):
		frappe.throw(_("Only band members can open Roadie"), frappe.PermissionError)

	return frappe._dict(
		boot={
			"csrf_token": frappe.sessions.get_csrf_token(),
			"user": frappe.session.user,
			"lang": frappe.local.lang,
			# Only this app's catalogue: every SPA string is ours, and the full one weighs megabytes.
			"translations": get_translations_from_apps(frappe.local.lang, apps=["roadie"]),
			"drive_url": frappe.conf.get("band_drive_url"),
			"can_link_drive_items": can_use_drive(),
		}
	)
