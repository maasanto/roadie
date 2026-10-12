import frappe
from frappe import _
from frappe.desk.doctype.notification_log.notification_log import (
	get_title,
	get_title_html,
	make_notification_logs,
)
from frappe.desk.notifications import extract_mentions
from frappe.utils import get_fullname, get_url

from roadie.api import COMMENT_DOCTYPES


def notify_mentioned_members(comment, method=None):
	"""Frappe only notifies mentioned System Users, and members are website users, so they are notified here."""
	if comment.comment_type != "Comment" or comment.reference_doctype not in COMMENT_DOCTYPES:
		return
	mentioned = extract_mentions(comment.content)
	if not mentioned:
		return
	members = frappe.get_all(
		"User",
		filters=[
			["name", "in", mentioned],
			["enabled", "=", 1],
			["user_type", "!=", "System User"],
			["Has Role", "role", "=", "Band Member"],
		],
		pluck="email",
		distinct=True,
	)
	if not members:
		return

	title = get_title(comment.reference_doctype, comment.reference_name)
	# Created in the request, as Frappe CRM does, rather than enqueued like Frappe's own mentions: a band is a
	# handful of members, and the bell then lights up whether or not a background worker runs.
	make_notification_logs(
		frappe._dict(
			{
				"type": "Mention",
				"document_type": comment.reference_doctype,
				"document_name": comment.reference_name,
				"source_doctype": comment.doctype,
				"source_name": comment.name,
				"link": get_url(_record_path(comment.reference_doctype, comment.reference_name)),
				"subject": _("{0} mentioned you in a comment in {1} {2}").format(
					frappe.bold(get_fullname(comment.owner)),
					frappe.bold(_(comment.reference_doctype)),
					get_title_html(title),
				),
				"from_user": comment.owner,
				"email_content": comment.content,
			}
		),
		members,
	)


def _record_path(doctype: str, name: str) -> str:
	"""Members can't open the Desk form Frappe links to by default. A gig opens its panel on the Pipeline, and each
	directory type has its own screen named after the DocType (frontend/src/directory.js), whose query opens the
	record as the search palette does (resultRoute in frontend/src/search.js)."""
	if doctype == "Gig":
		return f"/roadie?gig={name}"
	return f"/roadie/directory/{doctype.lower()}s?entry={doctype}:{name}"
