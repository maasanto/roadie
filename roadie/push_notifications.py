import re
from html import unescape
from urllib.parse import urlsplit

import frappe
from frappe.push_notification import PushNotification
from frappe.utils import get_url, strip_html

# The relay keys its Firebase credentials by project, so this must match the project registered there.
PUSH_PROJECT = "roadie"
SPA_ROUTE = "/roadie"
PUSH_ICON = "/assets/roadie/pwa/icon-192.png"
# Without a break, the paragraphs of a comment or a reminder run into one another once the tags are gone.
PARAGRAPH_BREAK = re.compile(r"<br\s*/?>|</(?:p|div|li)>", re.IGNORECASE)


def is_push_configured() -> bool:
	"""A restored backup keeps Push Notification Settings enabled but loses the relay URL, which lives in site config."""
	return bool(frappe.conf.push_relay_server_url) and PushNotification(PUSH_PROJECT).is_enabled()


def queue_push(notification_log, method=None):
	"""Every Notification Log is a row in the in-app panel, so each one also reaches the member's devices."""
	if is_push_configured():
		frappe.enqueue(
			"roadie.push_notifications.send_push",
			queue="short",
			enqueue_after_commit=True,
			notification_log=notification_log.name,
		)


def send_push(notification_log: str) -> None:
	notification = frappe.get_doc("Notification Log", notification_log)
	PushNotification(PUSH_PROJECT).send_notification_to_user(
		notification.for_user,
		title=_plain_text(notification.subject),
		body=_plain_text(notification.email_content),
		link=get_url(_spa_path(notification.link)),
		icon=get_url(PUSH_ICON),
		# Already plain: a second pass would delete text like "doors < 18h" that the first one unescaped
		strip_html=False,
	)


def _spa_path(link: str | None) -> str:
	"""Reminders link to the Desk form, which members can't open, so their push opens Roadie instead."""
	path = urlsplit(link or "").path
	return path if path.startswith(SPA_ROUTE) else SPA_ROUTE


def _plain_text(html: str | None) -> str:
	"""A system notification shows text verbatim, and subjects carry markup like <strong>John Doe</strong>."""
	paragraphs = PARAGRAPH_BREAK.sub("\n", html or "")
	return unescape(strip_html(paragraphs)).strip()
