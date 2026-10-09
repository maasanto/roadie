app_name = "band_crm"
app_title = "Band CRM"
app_publisher = "Antoine Maas"
app_description = "Track the people, places and deadlines that get the band booked"
app_email = "antoine.maas@gmail.com"
app_license = "mit"

use_json_request_body = True
require_type_annotated_api_methods = True

website_route_rules = [{"from_route": "/band/<path:app_path>", "to_route": "band"}]

# Members are website users: logging in lands them on the SPA, never on Desk
role_home_page = {"Band Member": "band"}

after_install = "band_crm.install.after_install"

doc_events = {"Comment": {"after_insert": "band_crm.mentions.notify_mentioned_members"}}

fixtures =[
	{"dt": "Role", "filters": [["name", "=", "Band Member"]]},
	{"dt": "Notification", "filters": [["module", "=", "Band CRM"]]},
]
