import frappe
from frappe import _
from frappe.desk.doctype.notification_log.notification_log import (
	enqueue_create_notification,
	get_title,
	get_title_html,
)
from frappe.desk.notifications import extract_mentions
from frappe.utils import get_fullname

from band_crm.api import COMMENT_DOCTYPES


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
	enqueue_create_notification(
		members,
		{
			"type": "Mention",
			"document_type": comment.reference_doctype,
			"document_name": comment.reference_name,
			"source_doctype": comment.doctype,
			"source_name": comment.name,
			"subject": _("{0} mentioned you in a comment in {1} {2}").format(
				frappe.bold(get_fullname(comment.comment_email)),
				frappe.bold(_(comment.reference_doctype)),
				get_title_html(title),
			),
			"from_user": comment.comment_email,
			"email_content": comment.content,
		},
	)
