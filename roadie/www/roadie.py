from urllib.parse import urlencode

import frappe
from frappe import _
from frappe.translate import get_translations_from_apps
from frappe.utils import strip_html
from frappe.utils.data import Weekday

from roadie.api import PROTECTED_FIELDS, can_use_drive
from roadie.push_notifications import is_push_configured

no_cache = 1


def get_context():
	if frappe.session.user == "Guest":
		# The full path, so a link from a mention email still opens its record once the member has signed in.
		frappe.local.flags.redirect_location = "/login?" + urlencode(
			{"redirect-to": frappe.request.full_path}
		)
		raise frappe.Redirect

	if not frappe.has_permission("Gig", "read"):
		frappe.throw(_("Only band members can open Roadie"), frappe.PermissionError)

	can_link_drive_items = can_use_drive()
	# The System Settings default, as Desk's own date pickers read it.
	first_day_of_the_week = frappe.defaults.get_user_default("first_day_of_the_week") or "Sunday"
	return frappe._dict(
		boot={
			"csrf_token": frappe.sessions.get_csrf_token(),
			"user": frappe.session.user,
			"user_full_name": frappe.utils.get_fullname(frappe.session.user),
			"user_image": frappe.db.get_value("User", frappe.session.user, "user_image"),
			"lang": frappe.local.lang,
			"week_start": Weekday[first_day_of_the_week].value,
			"currency": frappe.db.get_default("currency"),
			# Only this app's catalogue: every SPA string is ours, and the full one weighs megabytes.
			"translations": get_translations_from_apps(frappe.local.lang, apps=["roadie"]),
			"drive_url": frappe.conf.get("band_drive_url") or ("/drive" if can_link_drive_items else None),
			"protected_fields": PROTECTED_FIELDS,
			"can_link_drive_items": can_link_drive_items,
			"push_relay_server_url": frappe.conf.push_relay_server_url if is_push_configured() else None,
			"email_signature": get_email_signature(),
			"email_sender": get_email_sender(),
		}
	)


# Frappe sends as the member and sets Reply-To to them, so replies would skip the band's mailbox.
def get_email_sender():
	band_email = frappe.db.get_value("Email Account", {"enable_outgoing": 1, "default_outgoing": 1}, "email_id")
	return band_email and frappe.utils.get_formatted_email(frappe.session.user, mail=band_email)


# Desk's precedence, from Communication.set_signature_in_email_content: an account signs only when told to, and
# here only one that can send. Desk saves a cleared signature as an empty editor, hence the check on its text.
def get_email_signature():
	signatures = (
		frappe.db.get_value("User", frappe.session.user, "email_signature"),
		frappe.db.get_value(
			"Email Account", {"enable_outgoing": 1, "default_outgoing": 1, "add_signature": 1}, "signature"
		),
	)
	return next((signature for signature in signatures if strip_html(signature or "").strip()), None)
