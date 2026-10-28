from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from roadie.api import (
	DRIVE_ROLE,
	get_members,
	get_notifications,
	grant_drive_access,
	is_drive_installed,
	is_in_drive,
	mark_notifications_read,
	share_drive_link,
)
from roadie.roadie.doctype.gig.test_gig import make_member
from roadie.www import roadie as roadie_page

# Not the shared test MEMBER: these are Drive's own members, and they are made here for every case.
MEMBER = "drummer@example.com"
BANDMATE = "bassist@example.com"
MEMBER_WITHOUT_DRIVE = "keys@example.com"
MEMBER_WITH_ROLE_PROFILE = "guitarist@example.com"


def make_drive_member(email, first_name):
	make_member(email, first_name)
	frappe.get_doc("User", email).add_roles(DRIVE_ROLE)


def share_from_drive(item, user):
	"""Shares as Drive's share dialog does, then notifies as Drive's after-commit job would."""
	from suite.drive.api.notifications import notify_share

	item.share(user=user, read=1)
	notify_share(item.name, frappe.db.get_value("Drive Permission", {"entity": item.name, "user": user}))


def member_listing(email):
	return next(member for member in get_members() if member.name == email)


def make_band_folder(file_name):
	from suite.drive.utils import create_drive_file, get_root_folder

	# Not suite.drive.utils.files.FileManager: this inserts the File without reaching for storage.
	return create_drive_file(file_name, get_root_folder().name, "Folder", "")


class TestDriveLinkWithoutDrive(IntegrationTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

	def test_composer_hides_drive_links_and_sharing_refuses(self):
		if is_drive_installed():
			self.skipTest("Frappe Suite is installed on this site")
		make_member(MEMBER, "Sam")
		frappe.set_user(MEMBER)

		self.assertFalse(roadie_page.get_context().boot["can_link_drive_items"])
		with self.assertRaisesRegex(frappe.PermissionError, "Suite User role"):
			share_drive_link("anything")
		self.assertNotIn("has_drive_access", member_listing(MEMBER))
		with self.assertRaisesRegex(frappe.ValidationError, "needs Frappe Suite"):
			grant_drive_access(MEMBER)


class TestDriveLink(IntegrationTestCase):
	def setUp(self):
		if not is_drive_installed():
			self.skipTest("Frappe Suite is not installed on this site")
		make_drive_member(MEMBER, "Sam")
		frappe.set_user(MEMBER)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_sidebar_links_to_drive_without_any_site_config(self):
		with patch.dict(frappe.local.conf):
			frappe.local.conf.pop("band_drive_url", None)
			drive_url = roadie_page.get_context().boot["drive_url"]

		self.assertEqual(drive_url, "/drive")

	def test_member_shares_a_drive_folder_with_anyone_who_has_the_link(self):
		from suite.drive.api.permissions import get_user_access_for_user

		self.assertTrue(roadie_page.get_context().boot["can_link_drive_items"])
		folder = make_band_folder("Tech riders")

		link = share_drive_link(folder.name)

		self.assertEqual(link, frappe.utils.get_url(f"/drive/d/{folder.name}"))
		self.assertTrue(get_user_access_for_user(folder, "Guest")["read"])

	def test_a_promoter_with_a_folder_link_can_open_what_it_holds_now_and_later(self):
		from suite.drive.api.permissions import get_user_access_for_user
		from suite.drive.utils import create_drive_file

		press_kit = make_band_folder("Press kit")
		photos = create_drive_file("Photos", press_kit.name, "Folder", "")
		rider = create_drive_file("Tech rider.txt", photos.name, "Text", "")

		share_drive_link(press_kit.name)
		bio = create_drive_file("Bio.txt", press_kit.name, "Text", "")

		for item in (photos, rider, bio):
			self.assertTrue(get_user_access_for_user(item, "Guest")["read"], item.file_name)

	def test_a_member_cannot_publish_their_whole_home_folder(self):
		from suite.drive.api.permissions import get_user_access_for_user
		from suite.drive.utils import get_user_folder

		home = frappe.get_doc("File", get_user_folder().name)

		with self.assertRaisesRegex(frappe.ValidationError, "whole Drive"):
			share_drive_link(home.name)
		self.assertFalse(get_user_access_for_user(home, "Guest")["read"])

	def test_member_without_the_suite_user_role_is_not_offered_drive_links(self):
		frappe.set_user("Administrator")
		make_member(MEMBER_WITHOUT_DRIVE, "Kim")
		# Drive grants its role to users created after it is installed, not to the ones already there.
		frappe.get_doc("User", MEMBER_WITHOUT_DRIVE).remove_roles("Suite User")
		frappe.set_user(MEMBER_WITHOUT_DRIVE)

		with patch.dict(frappe.local.conf):
			frappe.local.conf.pop("band_drive_url", None)
			boot = roadie_page.get_context().boot
		self.assertFalse(boot["can_link_drive_items"])
		self.assertIsNone(boot["drive_url"])
		with self.assertRaisesRegex(frappe.PermissionError, "Suite User role"):
			share_drive_link("anything")

	def test_member_gives_drive_to_a_bandmate_who_joined_before_suite(self):
		frappe.set_user("Administrator")
		make_member(MEMBER_WITHOUT_DRIVE, "Kim")
		frappe.get_doc("User", MEMBER_WITHOUT_DRIVE).remove_roles("Suite User")
		frappe.set_user(MEMBER)
		self.assertFalse(member_listing(MEMBER_WITHOUT_DRIVE).has_drive_access)

		grant_drive_access(MEMBER_WITHOUT_DRIVE)

		self.assertTrue(member_listing(MEMBER_WITHOUT_DRIVE).has_drive_access)
		frappe.set_user(MEMBER_WITHOUT_DRIVE)
		self.assertTrue(roadie_page.get_context().boot["can_link_drive_items"])

	def test_drive_access_is_only_given_to_band_members(self):
		frappe.set_user("Administrator")
		make_member(MEMBER_WITHOUT_DRIVE, "Kim")
		outsider = frappe.get_doc("User", MEMBER_WITHOUT_DRIVE)
		outsider.remove_roles("Band Member", "Suite User")
		frappe.set_user(MEMBER)

		with self.assertRaisesRegex(frappe.PermissionError, "not a band member"):
			grant_drive_access(MEMBER_WITHOUT_DRIVE)
		frappe.set_user(MEMBER_WITHOUT_DRIVE)
		with self.assertRaises(frappe.PermissionError):
			grant_drive_access(MEMBER_WITHOUT_DRIVE)
		self.assertNotIn("Suite User", frappe.get_roles(MEMBER_WITHOUT_DRIVE))

	def test_a_role_profile_that_drops_drive_access_is_reported_not_hidden(self):
		frappe.set_user("Administrator")
		make_member(MEMBER_WITH_ROLE_PROFILE, "Robin")
		if not frappe.db.exists("Role Profile", "Band only"):
			frappe.get_doc(
				{"doctype": "Role Profile", "role_profile": "Band only", "roles": [{"role": "Band Member"}]}
			).insert()
		robin = frappe.get_doc("User", MEMBER_WITH_ROLE_PROFILE)
		robin.set("role_profiles", [{"role_profile": "Band only"}])
		robin.save()
		frappe.set_user(MEMBER)

		with self.assertRaisesRegex(frappe.ValidationError, "role profile"):
			grant_drive_access(MEMBER_WITH_ROLE_PROFILE)
		self.assertNotIn("Suite User", frappe.get_roles(MEMBER_WITH_ROLE_PROFILE))

	def test_bandmate_cannot_make_a_folder_they_do_not_own_public(self):
		from suite.drive.api.permissions import get_user_access_for_user

		folder = make_band_folder("Setlists")
		frappe.set_user("Administrator")
		make_drive_member(BANDMATE, "Alex")
		# Read reaches the folder, share does not: Drive grants the two separately.
		folder.share(user=BANDMATE, read=1)
		frappe.set_user(BANDMATE)

		with self.assertRaises(frappe.PermissionError):
			share_drive_link(folder.name)
		self.assertFalse(get_user_access_for_user(folder, "Guest")["read"])

	def test_linking_an_already_public_item_keeps_the_access_drive_gave_it(self):
		from suite.drive.api.permissions import get_user_access_for_user

		folder = make_band_folder("Press kit")
		folder.share(user="", read=1, comment=1)

		share_drive_link(folder.name)

		self.assertTrue(get_user_access_for_user(folder, "Guest")["comment"])

	def test_a_folder_outside_drive_is_not_a_drive_item(self):
		# Drive serves nothing outside its own roots, so a stray folder has no /drive/ URL to link to.
		stray = frappe.get_doc(
			{"doctype": "File", "file_name": "Elsewhere", "is_folder": 1, "is_private": 1}
		).insert(ignore_permissions=True)

		self.assertFalse(is_in_drive(stray))
		self.assertTrue(is_in_drive(make_band_folder("Tech riders")))

	def test_a_drive_share_opens_what_was_shared(self):
		from suite.drive.utils import create_drive_file, get_root_folder

		frappe.set_user("Administrator")
		frappe.db.delete("Notification Log", {"for_user": MEMBER})
		frappe.db.delete("Drive Notification", {"to_user": MEMBER})
		root = get_root_folder().name
		document = create_drive_file("Tour plan", root, "Document", "")
		folder = make_band_folder("Press kit")
		rider = create_drive_file("Rider.pdf", root, "PDF", "")
		for item in (document, folder, rider):
			share_from_drive(item, MEMBER)

		frappe.set_user(MEMBER)
		notifications = get_notifications()
		self.assertEqual(
			{notification.url for notification in notifications},
			{f"/writer/w/{document.name}", f"/drive/d/{folder.name}", f"/drive/f/{rider.name}"},
		)
		self.assertEqual(notifications[0].title, 'Administrator shared a file with you: "Rider.pdf"')

		mark_notifications_read([notifications[0].name])
		self.assertEqual(sum(not notification.read for notification in get_notifications()), 2)
