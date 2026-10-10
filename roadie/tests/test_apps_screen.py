import frappe
from frappe.apps import get_apps
from frappe.tests import IntegrationTestCase

OUTSIDER = "outsider@example.com"


class TestAppsScreen(IntegrationTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

	def test_tile_carries_the_logo_and_hides_from_desk_users_outside_the_band(self):
		self.assertIn(
			{"name": "roadie", "logo": "/assets/roadie/logo.svg", "title": "Roadie", "route": "/roadie"},
			self._apps_seen_by("Administrator"),
		)

		if not frappe.db.exists("User", OUTSIDER):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": OUTSIDER,
					"first_name": "Outsider",
					"roles": [{"role": "Website Manager"}],
				}
			).insert()
		self.assertNotIn("roadie", [app["name"] for app in self._apps_seen_by(OUTSIDER)])

	def _apps_seen_by(self, user):
		frappe.set_user(user)
		frappe.local.request_cache.clear()
		return get_apps()
