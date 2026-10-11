import tempfile
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import set_request
from frappe.website.serve import get_response


class TestServiceWorker(IntegrationTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

	def test_guest_gets_the_built_worker_scoped_to_the_spa(self):
		with tempfile.TemporaryDirectory() as build_dir:
			built_worker = Path(build_dir) / "sw.js"
			built_worker.write_text("self.skipWaiting();")
			response = self._fetch_as_guest(built_worker)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.mimetype, "text/javascript")
		self.assertEqual(response.get_data(as_text=True), "self.skipWaiting();")
		self.assertEqual(response.headers["Service-Worker-Allowed"], "/roadie")

	def _fetch_as_guest(self, built_worker):
		frappe.set_user("Guest")
		self.addCleanup(setattr, frappe.local, "request", getattr(frappe.local, "request", None))
		set_request(method="GET", path="/roadie/sw.js")
		with patch("roadie.page_renderers.BUILT_SERVICE_WORKER", built_worker):
			return get_response()
