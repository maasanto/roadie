import frappe
from frappe.tests import IntegrationTestCase

from roadie.api import share_drive_link
from roadie.roadie.doctype.gig.test_gig import make_member
from roadie.www import roadie as roadie_page

# Not the shared test MEMBER: Drive User is a desk role, so granting it would turn that member into a System User.
MEMBER = "drummer@example.com"
BANDMATE = "bassist@example.com"
MEMBER_WITHOUT_DRIVE = "keys@example.com"


def is_drive_installed():
	return "drive" in frappe.get_installed_apps()


def make_drive_member(email, first_name):
	make_member(email, first_name)
	frappe.get_doc("User", email).add_roles("Drive User")


def make_band_folder(file_name):
	from drive.api.product import create_team
	from drive.utils import create_drive_file, get_home_folder

	team = create_team(user=MEMBER, team_name="Acme Band")
	# Not drive.api.files.create_folder: on Drive develop it fails to create the on-disk folder.
	return create_drive_file(team, file_name, get_home_folder(team)["name"], "Folder", "")


class TestDriveLinkWithoutDrive(IntegrationTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

	def test_composer_hides_drive_links_and_sharing_refuses(self):
		if is_drive_installed():
			self.skipTest("Frappe Drive is installed on this site")
		make_member(MEMBER, "Sam")
		frappe.set_user(MEMBER)

		self.assertFalse(roadie_page.get_context().boot["can_link_drive_items"])
		with self.assertRaisesRegex(frappe.PermissionError, "Drive User role"):
			share_drive_link("anything")


class TestDriveLink(IntegrationTestCase):
	def setUp(self):
		if not is_drive_installed():
			self.skipTest("Frappe Drive is not installed on this site")
		make_drive_member(MEMBER, "Sam")
		frappe.set_user(MEMBER)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_member_shares_a_drive_folder_with_anyone_who_has_the_link(self):
		from drive.api.permissions import get_user_access

		self.assertTrue(roadie_page.get_context().boot["can_link_drive_items"])
		folder = make_band_folder("Tech riders")

		link = share_drive_link(folder.name)

		self.assertEqual(link, frappe.utils.get_url(f"/drive/d/{folder.name}"))
		self.assertTrue(get_user_access(folder, "Guest")["read"])

	def test_member_without_the_drive_user_role_is_not_offered_drive_links(self):
		frappe.set_user("Administrator")
		make_member(MEMBER_WITHOUT_DRIVE, "Kim")
		# Drive grants its role to users created after it is installed, not to the ones already there.
		frappe.get_doc("User", MEMBER_WITHOUT_DRIVE).remove_roles("Drive User")
		frappe.set_user(MEMBER_WITHOUT_DRIVE)

		self.assertFalse(roadie_page.get_context().boot["can_link_drive_items"])

	def test_bandmate_cannot_make_a_folder_they_do_not_own_public(self):
		from drive.api.permissions import get_user_access

		folder = make_band_folder("Setlists")
		frappe.set_user("Administrator")
		make_drive_member(BANDMATE, "Alex")
		team = frappe.get_doc("Drive Team", folder.team)
		team.append("users", {"user": BANDMATE, "access_level": 1})
		team.save(ignore_permissions=True)
		frappe.set_user(BANDMATE)

		with self.assertRaises(frappe.PermissionError):
			share_drive_link(folder.name)
		self.assertFalse(get_user_access(folder, "Guest")["read"])

	def test_linking_an_already_public_item_keeps_the_access_drive_gave_it(self):
		from drive.api.permissions import get_user_access

		folder = make_band_folder("Press kit")
		folder.share(user="", read=1, comment=1)

		share_drive_link(folder.name)

		self.assertTrue(get_user_access(folder, "Guest")["comment"])
