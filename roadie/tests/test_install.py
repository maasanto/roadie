import frappe
from frappe.permissions import update_permission_property
from frappe.tests import IntegrationTestCase

from roadie.install import GRANTED_DOCTYPES, ROLE, after_install, after_uninstall


class TestInstall(IntegrationTestCase):
	def setUp(self):
		for doctype in GRANTED_DOCTYPES:
			frappe.db.delete("Custom DocPerm", {"parent": doctype})
		after_install()
		self.addCleanup(after_install)

	def test_uninstall_gives_back_the_standard_permissions(self):
		after_uninstall()

		for doctype in GRANTED_DOCTYPES:
			self.assertFalse(frappe.db.exists("Custom DocPerm", {"parent": doctype}), doctype)

	def test_uninstall_keeps_an_admin_customisation(self):
		update_permission_property("Contact", "System Manager", 0, "export", 0)

		after_uninstall()

		self.assertFalse(frappe.db.exists("Custom DocPerm", {"parent": "Contact", "role": ROLE}))
		self.assertEqual(
			frappe.db.get_value("Custom DocPerm", {"parent": "Contact", "role": "System Manager"}, "export"),
			0,
		)
		self.assertFalse(frappe.db.exists("Custom DocPerm", {"parent": "Communication"}))
