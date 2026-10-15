from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from roadie.api import (
	answer_availability,
	get_activity,
	get_gig_activity,
	get_members,
	get_pending_availability,
	request_availability,
	set_band_manager,
)
from roadie.roadie.doctype.gig.test_gig import MEMBER, OTHER_MEMBER, make_member
from roadie.tests.test_notifications import notifications_for

MANAGER = "max@example.com"
NEWCOMER = "nina@example.com"


def answers(gig_name):
	return {row.member: row.answer for row in frappe.get_doc("Gig", gig_name).availability}


class TestAvailability(IntegrationTestCase):
	def setUp(self):
		make_member(MEMBER, "John")
		make_member(OTHER_MEMBER, "Jane")
		make_member(MANAGER, "Max")
		frappe.get_doc("User", MANAGER).add_roles("Band Manager")
		# A test class shares one transaction, so a member made manager by an earlier test would stay one.
		frappe.get_doc("User", OTHER_MEMBER).remove_roles("Band Manager")
		frappe.db.delete("Notification Log", {"for_user": ["in", (MEMBER, OTHER_MEMBER, MANAGER, NEWCOMER)]})

		frappe.set_user(MANAGER)
		self.gig = frappe.get_doc(
			{"doctype": "Gig", "title": "Acme Festival 2027", "gig_date": add_days(today(), 30)}
		).insert()

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_the_manager_asks_every_member_but_managers(self):
		request_availability(self.gig.name)

		asked = answers(self.gig.name)
		self.assertEqual((asked.get(MEMBER), asked.get(OTHER_MEMBER)), ("", ""))
		self.assertNotIn(MANAGER, asked)
		[notification] = notifications_for(MEMBER, self.gig.name)
		self.assertIn("can you play Acme Festival 2027", notification.subject)
		self.assertFalse(notifications_for(MANAGER, self.gig.name))

	def test_a_gig_without_a_date_cannot_be_asked_about_or_answered(self):
		request_availability(self.gig.name)
		self.gig.db_set("gig_date", None)
		with self.assertRaises(frappe.ValidationError):
			request_availability(self.gig.name)
		frappe.set_user(MEMBER)
		with self.assertRaises(frappe.ValidationError):
			answer_availability(self.gig.name, "Yes")

	def test_an_answer_reaches_the_owner_and_the_card(self):
		request_availability(self.gig.name)

		frappe.set_user(MEMBER)
		self.assertIn(self.gig.name, [gig.name for gig in get_pending_availability()])
		answer_availability(self.gig.name, "No")

		self.assertNotIn(self.gig.name, [gig.name for gig in get_pending_availability()])
		[notification] = notifications_for(MANAGER, self.gig.name)
		self.assertEqual(
			notification.subject,
			f"John Doe can't play Acme Festival 2027 on {frappe.utils.formatdate(self.gig.gig_date)}",
		)
		card = {row.member: row.answer for row in get_gig_activity()[self.gig.name]["availability"]}
		self.assertEqual((card[MEMBER], card[OTHER_MEMBER]), ("No", ""))

	def test_a_member_changes_their_answer_and_the_activity_tells_it(self):
		# Frappe skips versions under test, and the controller saves without asking for one.
		self.enterContext(patch.object(frappe, "in_test", False))
		request_availability(self.gig.name)
		frappe.set_user(MEMBER)
		answer_availability(self.gig.name, "Yes")
		answer_availability(self.gig.name, "No")

		self.assertEqual(answers(self.gig.name)[MEMBER], "No")
		activity = [
			(entry["type"], entry["by"], entry.get("answer"))
			for entry in get_activity("Gig", self.gig.name)
			if entry["type"] in ("availability_requested", "answered")
		]
		self.assertEqual(
			activity,
			[
				("availability_requested", "Max Doe", None),
				("answered", "John Doe", "Yes"),
				("answered", "John Doe", "No"),
			],
		)

	def test_someone_never_asked_cannot_answer(self):
		request_availability(self.gig.name)
		frappe.set_user(MANAGER)
		with self.assertRaises(frappe.ValidationError):
			answer_availability(self.gig.name, "Yes")

	def test_a_reminder_asks_only_who_has_not_answered_and_newcomers(self):
		request_availability(self.gig.name)
		frappe.set_user(MEMBER)
		answer_availability(self.gig.name, "Yes")
		frappe.set_user("Administrator")
		make_member(NEWCOMER, "Nina")
		frappe.db.delete("Notification Log", {"for_user": ["in", (MEMBER, OTHER_MEMBER)]})

		frappe.set_user(MANAGER)
		request_availability(self.gig.name)

		self.assertEqual(answers(self.gig.name)[MEMBER], "Yes")
		self.assertFalse(notifications_for(MEMBER, self.gig.name))
		self.assertTrue(notifications_for(OTHER_MEMBER, self.gig.name))
		self.assertTrue(notifications_for(NEWCOMER, self.gig.name))

	def test_a_performer_is_not_told_about_their_own_request_or_answer(self):
		frappe.set_user(MEMBER)
		self.gig.db_set("gig_owner", MEMBER)
		request_availability(self.gig.name)
		answer_availability(self.gig.name, "Yes")

		self.assertFalse(notifications_for(MEMBER, self.gig.name))
		self.assertTrue(notifications_for(OTHER_MEMBER, self.gig.name))

	def test_a_new_date_asks_the_band_as_it_is_now(self):
		request_availability(self.gig.name)
		frappe.set_user("Administrator")
		frappe.get_doc("User", OTHER_MEMBER).add_roles("Band Manager")
		make_member(NEWCOMER, "Nina")
		frappe.db.delete("Notification Log", {"for_user": OTHER_MEMBER})

		frappe.set_user(MANAGER)
		gig = frappe.get_doc("Gig", self.gig.name)
		gig.gig_date = add_days(today(), 31)
		gig.save()

		asked = answers(self.gig.name)
		self.assertNotIn(OTHER_MEMBER, asked)
		self.assertIn(NEWCOMER, asked)
		self.assertFalse(notifications_for(OTHER_MEMBER, self.gig.name))

	def test_a_member_made_manager_is_no_longer_waited_on(self):
		request_availability(self.gig.name)

		frappe.set_user(MEMBER)
		set_band_manager(OTHER_MEMBER, True)

		self.assertNotIn(OTHER_MEMBER, answers(self.gig.name))
		frappe.set_user(OTHER_MEMBER)
		self.assertNotIn(self.gig.name, [gig.name for gig in get_pending_availability()])

	def test_a_new_date_asks_everyone_again(self):
		request_availability(self.gig.name)
		frappe.set_user(MEMBER)
		answer_availability(self.gig.name, "Yes")
		frappe.db.delete("Notification Log", {"for_user": MEMBER})

		frappe.set_user(MANAGER)
		gig = frappe.get_doc("Gig", self.gig.name)
		gig.gig_date = add_days(today(), 31)
		gig.save()

		self.assertEqual(answers(self.gig.name)[MEMBER], "")
		[notification] = notifications_for(MEMBER, self.gig.name)
		self.assertIn("can you still play it?", notification.subject)

	def test_a_dropped_gig_stops_asking(self):
		request_availability(self.gig.name)
		frappe.db.set_value("Gig", self.gig.name, "status", "Dropped")

		frappe.set_user(MEMBER)
		self.assertNotIn(self.gig.name, [gig.name for gig in get_pending_availability()])

	def test_a_member_makes_someone_a_manager_and_back(self):
		frappe.set_user(MEMBER)
		set_band_manager(OTHER_MEMBER, True)
		self.assertTrue(next(m for m in get_members() if m.name == OTHER_MEMBER).is_manager)

		set_band_manager(OTHER_MEMBER, False)
		self.assertFalse(next(m for m in get_members() if m.name == OTHER_MEMBER).is_manager)
