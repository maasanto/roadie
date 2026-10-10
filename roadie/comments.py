import frappe
from frappe.utils import get_fullname

from roadie.api import COMMENT_DOCTYPES


def set_author(comment, method=None):
	"""add_comment takes the author from the client, so a member could post under a bandmate's name."""
	if comment.comment_type != "Comment" or comment.reference_doctype not in COMMENT_DOCTYPES:
		return
	comment.comment_email = frappe.session.user
	comment.comment_by = get_fullname(frappe.session.user)
