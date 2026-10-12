from html import unescape

import frappe
from frappe.push_notification import PushNotification
from frappe.utils import get_url, strip_html

from roadie.api import SPA_BASE, notification_route

# The relay keys its Firebase credentials by project, so this must match the project registered there.
PUSH_PROJECT = "roadie"
PUSH_ICON = "/assets/roadie/pwa/icon-192.png"


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
	route = notification_route(notification) or "/"
	PushNotification(PUSH_PROJECT).send_notification_to_user(
		notification.for_user,
		title=_plain_text(notification.subject),
		body=_plain_text(notification.email_content),
		link=get_url(SPA_BASE + route),
		icon=get_url(PUSH_ICON),
	)


def _plain_text(html: str | None) -> str:
	"""A system notification shows text verbatim, and subjects carry markup like <strong>John Doe</strong>."""
	return unescape(strip_html(html or "")).strip()
