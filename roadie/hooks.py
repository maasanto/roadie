app_name = "roadie"
app_title = "Roadie"
app_publisher = "Antoine Maas"
app_description = "Track the people, places and deadlines that get the band booked"
app_email = "antoine.maas@okte.io"
app_license = "agpl-3.0"
app_logo_url = "/assets/roadie/logo.svg"

add_to_apps_screen = [
	{
		"name": app_name,
		"logo": app_logo_url,
		"title": app_title,
		"route": "/roadie",
		"has_permission": "roadie.api.has_app_permission",
	}
]

use_json_request_body = True
require_type_annotated_api_methods = True

website_route_rules = [{"from_route": "/roadie/<path:app_path>", "to_route": "roadie"}]
page_renderer = ["roadie.page_renderers.RoadieServiceWorker"]

# The app was called Band CRM and served at /band: keep old bookmarks working
website_redirects = [{"source": r"/band(/.*)?", "target": r"/roadie\1", "forward_query_parameters": True}]

# Members are website users: logging in lands them on the SPA, never on Desk
role_home_page = {"Band Member": "roadie"}

# A band has no admin: any member brings in the next one, who joins as a member and nothing more
user_invitation = {"allowed_roles": {"Band Member": ["Band Member"], "System Manager": ["Band Member"]}}

after_install = "roadie.install.after_install"
after_uninstall = "roadie.install.after_uninstall"

# Read by the dokos_ai app to serve the agent skill in roadie/roadie/skills; inert on a site without it
dokos_ai_skills = ["roadie"]

doc_events = {
	"Comment": {
		"before_insert": "roadie.comments.set_author",
		"after_insert": "roadie.mentions.notify_mentioned_members",
	},
	"User Invitation": {"before_insert": "roadie.invitations.keep_invitee_in_roadie"},
}

fixtures = [
	{"dt": "Role", "filters": [["name", "=", "Band Member"]]},
	{"dt": "Notification", "filters": [["module", "=", "Roadie"]]},
]
