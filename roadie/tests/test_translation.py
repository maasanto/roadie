import re
from pathlib import Path

import frappe
from babel.messages.pofile import read_po
from frappe.tests import IntegrationTestCase

from roadie.roadie.doctype.gig.test_gig import MEMBER, make_member
from roadie.www import roadie as roadie_page

APP_ROOT = Path(frappe.get_app_path("roadie")).parent
SPA_STRING = re.compile(r"""__\(\s*(["'])(.+?)\1""")


class TestTranslation(IntegrationTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.local.lang = "en"

	def test_every_spa_string_has_a_french_translation(self):
		with open(APP_ROOT / "roadie/locale/fr.po", "rb") as po_file:
			french = {message.id: message.string for message in read_po(po_file) if message.id}

		spa_strings = {
			match.group(2)
			for source in (APP_ROOT / "frontend/src").rglob("*")
			if source.suffix in (".vue", ".js")
			for match in SPA_STRING.finditer(source.read_text())
		}
		self.assertIn("My tasks", spa_strings)
		self.assertEqual([text for text in sorted(spa_strings) if not french.get(text)], [])

	def test_french_member_gets_the_french_catalogue_and_drive_link_in_the_page_boot(self):
		make_member(MEMBER, "John")
		frappe.set_user(MEMBER)
		frappe.local.lang = "fr"
		frappe.local.conf.band_drive_url = "https://drive.example.com/acme-band"
		try:
			boot = roadie_page.get_context().boot
		finally:
			del frappe.local.conf.band_drive_url

		self.assertEqual(boot["lang"], "fr")
		self.assertEqual(boot["translations"]["My tasks"], "Mes tâches")
		self.assertEqual(boot["drive_url"], "https://drive.example.com/acme-band")
