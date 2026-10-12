from unittest.mock import patch

import frappe
from frappe.push_notification import PushNotification
from frappe.tests import IntegrationTestCase
from frappe.utils import get_url

from roadie.push_notifications import send_push
from roadie.roadie.doctype.gig.test_gig import MEMBER, OTHER_MEMBER, make_member

SEND_PUSH = "roadie.push_notifications.send_push"
ICON_URL = "/assets/roadie/pwa/icon-192.png"
real_enqueue = frappe.enqueue


def enqueue_all_but_pushes(method, *args, **kwargs):
	"""Notification Logs are still created, but a push is never handed to a worker that would send it for real."""
	if method != SEND_PUSH:
		return real_enqueue(method, *args, **kwargs)


class TestPushNotifications(IntegrationTestCase):
	def setUp(self):
		make_member(MEMBER, "John")
		make_member(OTHER_MEMBER, "Jane")
		self.enqueue = self.start(patch("frappe.enqueue", side_effect=enqueue_all_but_pushes))
		self.send = self.start(patch.object(PushNotification, "send_notification_to_user", return_value=True))
		self.start(patch.object(PushNotification, "is_enabled", return_value=True))
		frappe.conf.push_relay_server_url = "https://push.example.com"
		self.addCleanup(frappe.conf.pop, "push_relay_server_url", None)

	def tearDown(self):
		frappe.set_user("Administrator")

	def start(self, patcher):
		self.addCleanup(patcher.stop)
		return patcher.start()

	def queued_pushes(self):
		return [
			call.kwargs["notification_log"]
			for call in self.enqueue.call_args_list
			if call.args == (SEND_PUSH,)
		]

	def test_an_assignment_is_pushed_to_the_assignee_and_opens_their_tasks(self):
		frappe.set_user(MEMBER)
		frappe.get_doc({"doctype": "Band Task", "title": "Send the rider", "assignee": OTHER_MEMBER}).insert()

		[notification_log] = self.queued_pushes()
		send_push(notification_log)

		self.send.assert_called_once_with(
			OTHER_MEMBER,
			title="John Doe assigned you a task: Send the rider",
			body="",
			link=get_url("/roadie/tasks"),
			icon=get_url(ICON_URL),
		)

	def test_a_mention_is_pushed_as_plain_text(self):
		notification_log = frappe.get_doc(
			{
				"doctype": "Notification Log",
				"for_user": MEMBER,
				"type": "Mention",
				"subject": "<strong>Jane Doe</strong> mentioned you in <span>Rock &amp; Roll</span>",
				"email_content": "<p>Can you call the venue?</p>",
				"link": get_url("/roadie/directory/festivals"),
			}
		).insert(ignore_permissions=True)

		send_push(notification_log.name)

		self.send.assert_called_once_with(
			MEMBER,
			title="Jane Doe mentioned you in Rock & Roll",
			body="Can you call the venue?",
			link=get_url("/roadie/directory/festivals"),
			icon=get_url(ICON_URL),
		)

	def test_nothing_is_queued_without_the_relay_url(self):
		# A backup restored elsewhere keeps the settings enabled but not the site config's relay URL.
		frappe.conf.pop("push_relay_server_url")
		frappe.set_user(MEMBER)
		frappe.get_doc({"doctype": "Band Task", "title": "Send the rider", "assignee": OTHER_MEMBER}).insert()

		self.assertEqual(self.queued_pushes(), [])
