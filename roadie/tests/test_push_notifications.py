from unittest.mock import patch

import frappe
from frappe.frappeclient import FrappeException
from frappe.push_notification import PushNotification
from frappe.tests import IntegrationTestCase
from frappe.utils import get_url

from roadie.api import is_drive_installed
from roadie.push_notifications import send_drive_push, send_push
from roadie.roadie.doctype.gig.test_gig import MEMBER, OTHER_MEMBER, make_member
from roadie.tests.test_drive_link import share_from_drive
from roadie.tests.test_notifications import SHEET_SHARE_NOTIFICATION

SEND_PUSH = "roadie.push_notifications.send_push"
SEND_DRIVE_PUSH = "roadie.push_notifications.send_drive_push"
ICON_URL = "/assets/roadie/pwa/icon-192.png"
real_enqueue = frappe.enqueue


def enqueue_all_but_pushes(method, *args, **kwargs):
	"""Notification Logs are still created, but a push is never handed to a worker that would send it for real."""
	if method not in (SEND_PUSH, SEND_DRIVE_PUSH):
		return real_enqueue(method, *args, **kwargs)


class TestPushNotifications(IntegrationTestCase):
	def setUp(self):
		make_member(MEMBER, "John")
		make_member(OTHER_MEMBER, "Jane")
		self.enqueue = self.start(patch("frappe.enqueue", side_effect=enqueue_all_but_pushes))
		self.send = self.start(patch.object(PushNotification, "send_notification_to_user", return_value=True))
		self.start(patch.object(PushNotification, "is_enabled", return_value=True))
		self.start(patch.dict(frappe.conf, {"push_relay_server_url": "https://push.example.com"}))

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

	def test_an_assignment_is_pushed_to_the_assignee_and_opens_the_task(self):
		frappe.set_user(MEMBER)
		task = frappe.get_doc(
			{"doctype": "Band Task", "title": "Send the rider", "assignee": OTHER_MEMBER}
		).insert()

		[notification_log] = self.queued_pushes()
		send_push(notification_log)

		self.send.assert_called_once_with(
			OTHER_MEMBER,
			title="John Doe assigned you a task: Send the rider",
			body="",
			link=get_url(f"/roadie/tasks?task={task.name}"),
			icon=get_url(ICON_URL),
			strip_html=False,
		)

	def test_a_mention_is_pushed_as_plain_text(self):
		notification_log = frappe.get_doc(
			{
				"doctype": "Notification Log",
				"for_user": MEMBER,
				"type": "Mention",
				"subject": "<strong>Jane Doe</strong> mentioned you in <span>Rock &amp; Roll</span>",
				"email_content": "<p>Can you call the venue?</p><p>Doors &lt; 18h</p>",
				"link": get_url("/roadie/directory/festivals"),
			}
		).insert(ignore_permissions=True)

		send_push(notification_log.name)

		self.send.assert_called_once_with(
			MEMBER,
			title="Jane Doe mentioned you in Rock & Roll",
			body="Can you call the venue?\nDoors < 18h",
			link=get_url("/roadie/directory/festivals"),
			icon=get_url(ICON_URL),
			strip_html=False,
		)

	def test_a_reminder_linking_to_the_desk_opens_roadie(self):
		notification_log = frappe.get_doc(
			{
				"doctype": "Notification Log",
				"for_user": MEMBER,
				"subject": "Due today: Send the rider",
				"link": get_url("/app/band-task/send-the-rider"),
			}
		).insert(ignore_permissions=True)

		send_push(notification_log.name)

		self.assertEqual(self.send.call_args.kwargs["link"], get_url("/roadie"))

	def test_a_reminder_about_a_task_opens_the_task(self):
		frappe.set_user(MEMBER)
		task = frappe.get_doc(
			{"doctype": "Band Task", "title": "Send the rider", "assignee": MEMBER}
		).insert()
		frappe.set_user("Administrator")
		# Frappe's own notifications name the record but give no link the SPA can open.
		notification_log = frappe.get_doc(
			{
				"doctype": "Notification Log",
				"for_user": MEMBER,
				"subject": "Due today: Send the rider",
				"document_type": "Band Task",
				"document_name": task.name,
			}
		).insert(ignore_permissions=True)

		send_push(notification_log.name)

		self.assertEqual(self.send.call_args.kwargs["link"], get_url(f"/roadie/tasks?task={task.name}"))

	def test_a_shared_sheet_opens_in_suite(self):
		notification_log = frappe.get_doc(SHEET_SHARE_NOTIFICATION).insert(
			ignore_permissions=True, ignore_links=True
		)

		send_push(notification_log.name)

		self.assertEqual(self.send.call_args.kwargs["link"], get_url("/sheets/a1b2c3d4e5"))

	def test_a_drive_share_opens_the_shared_document(self):
		if not is_drive_installed():
			self.skipTest("Frappe Suite is not installed on this site")
		from suite.drive.utils import create_drive_file, get_root_folder

		frappe.get_doc("User", MEMBER).add_roles("Suite User")
		document = create_drive_file("Tour plan", get_root_folder().name, "Document", "")
		share_from_drive(document, MEMBER)

		[drive_notification] = [
			call.kwargs["drive_notification"]
			for call in self.enqueue.call_args_list
			if call.args == (SEND_DRIVE_PUSH,)
		]
		send_drive_push(drive_notification)

		self.assertEqual(self.send.call_args.args, (MEMBER,))
		self.assertEqual(self.send.call_args.kwargs["link"], get_url(f"/writer/w/{document.name}"))

	def test_a_member_without_a_device_is_skipped_quietly(self):
		notification_log = frappe.get_doc(
			{"doctype": "Notification Log", "for_user": MEMBER, "subject": "Due today: Send the rider"}
		).insert(ignore_permissions=True)
		self.send.side_effect = FrappeException(
			{"message": f"user {MEMBER} not subscribed to push notifications", "status_code": 404}
		)

		send_push(notification_log.name)

		self.send.side_effect = FrappeException({"message": "invalid credentials", "status_code": 401})
		with self.assertRaises(FrappeException):
			send_push(notification_log.name)

	def test_nothing_is_queued_without_the_relay_url(self):
		# A backup restored elsewhere keeps the settings enabled but not the site config's relay URL.
		frappe.conf.pop("push_relay_server_url")
		frappe.set_user(MEMBER)
		frappe.get_doc({"doctype": "Band Task", "title": "Send the rider", "assignee": OTHER_MEMBER}).insert()

		self.assertEqual(self.queued_pushes(), [])
