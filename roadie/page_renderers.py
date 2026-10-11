from pathlib import Path

import frappe
from frappe.website.page_renderers.base_renderer import BaseRenderer
from werkzeug.wrappers import Response

SERVICE_WORKER_ROUTE = "/roadie/sw.js"
BUILT_SERVICE_WORKER = Path(__file__).parent / "public" / "frontend" / "sw.js"


class RoadieServiceWorker(BaseRenderer):
	"""Serves the built service worker from /roadie/ rather than /assets/: a worker only controls
	pages under the path it is served from, and the SPA lives at /roadie."""

	def can_render(self):
		# website_route_rules rewrite /roadie/* to the SPA endpoint before renderers run, so match the
		# original path too; the endpoint check stops it answering an error page resolved mid-request
		request = getattr(frappe.local, "request", None)
		return self.path == "roadie" and bool(request) and request.path == SERVICE_WORKER_ROUTE

	def render(self):
		return Response(
			BUILT_SERVICE_WORKER.read_bytes(),
			mimetype="text/javascript",
			# Widens the scope from /roadie/ to /roadie, which is where the SPA's home page lives
			headers={"Service-Worker-Allowed": "/roadie"},
		)
