import frappe
from frappe.tests import IntegrationTestCase

from roadie.api import is_in_drive, share_drive_link
from roadie.roadie.doctype.gig.test_gig import make_member
from roadie.www import roadie as roadie_page

# Not the shared test MEMBER: these are Drive's own members, and they are made here for every case.
MEMBER = "drummer@example.com"
BANDMATE = "bassist@example.com"
MEMBER_WITHOUT_DRIVE = "keys@example.com"


def is_suite_installed():
	return "suite" in frappe.get_installed_apps()


def make_drive_member(email, first_name):
	make_member(email, first_name)
	frappe.get_doc("User", email).add_roles("Suite User")


def make_band_folder(file_name):
	from suite.drive.utils import create_drive_file, get_root_folder

	# Not suite.drive.utils.files.FileManager: this inserts the File without reaching for storage.
	return create_drive_file(file_name, get_root_folder().name, "Folder", "")


class TestDriveLinkWithoutDrive(IntegrationTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

	def test_composer_hides_drive_links_and_sharing_refuses(self):
		if is_suite_installed():
			self.skipTest("Frappe Suite is installed on this site")
		make_member(MEMBER, "Sam")
		frappe.set_user(MEMBER)

		self.assertFalse(roadie_page.get_context().boot["can_link_drive_items"])
		with self.assertRaisesRegex(frappe.PermissionError, "Suite User role"):
			share_drive_link("anything")


class TestDriveLink(IntegrationTestCase):
	def setUp(self):
		if not is_suite_installed():
			self.skipTest("Frappe Suite is not installed on this site")
		make_drive_member(MEMBER, "Sam")
		frappe.set_user(MEMBER)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_member_shares_a_drive_folder_with_anyone_who_has_the_link(self):
		from suite.drive.api.permissions import get_user_access_for_user

		self.assertTrue(roadie_page.get_context().boot["can_link_drive_items"])
		folder = make_band_folder("Tech riders")

		link = share_drive_link(folder.name)

		self.assertEqual(link, frappe.utils.get_url(f"/drive/d/{folder.name}"))
		self.assertTrue(get_user_access_for_user(folder, "Guest")["read"])

	def test_member_without_the_suite_user_role_is_not_offered_drive_links(self):
		frappe.set_user("Administrator")
		make_member(MEMBER_WITHOUT_DRIVE, "Kim")
		# Drive grants its role to users created after it is installed, not to the ones already there.
		frappe.get_doc("User", MEMBER_WITHOUT_DRIVE).remove_roles("Suite User")
		frappe.set_user(MEMBER_WITHOUT_DRIVE)

		self.assertFalse(roadie_page.get_context().boot["can_link_drive_items"])

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
