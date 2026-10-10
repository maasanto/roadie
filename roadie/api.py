from urllib.parse import urlsplit

import frappe
from frappe import _

DIRECTORY_DOCTYPES = ("Festival", "Venue", "Promoter", "Band")
EMAIL_DOCTYPES = ("Gig", "Band Task", *DIRECTORY_DOCTYPES)
COMMENT_DOCTYPES = ("Gig", *DIRECTORY_DOCTYPES)
# Frappe roots a thread linked to no record on its first Communication, so that Communication is a thread too.
THREAD_DOCTYPES = (*EMAIL_DOCTYPES, "Communication")
EMAIL_SUMMARY_FIELDS = [
	"name",
	"subject",
	"sender",
	"sender_full_name",
	"recipients",
	"cc",
	"sent_or_received",
	"delivery_status",
	"communication_date",
]


@frappe.whitelist()
def get_contacts(doctype: str, name: str) -> list[dict]:
	if doctype not in DIRECTORY_DOCTYPES:
		frappe.throw(
			_("Contacts can only be listed for {0}, not {1}").format(", ".join(DIRECTORY_DOCTYPES), doctype)
		)
	frappe.get_doc(doctype, name).check_permission("read")

	return frappe.get_list(
		"Contact",
		filters=[["Dynamic Link", "link_doctype", "=", doctype], ["Dynamic Link", "link_name", "=", name]],
		fields=["name", "full_name", "email_id", "phone", "mobile_no"],
		order_by="creation asc",
	)


@frappe.whitelist(methods=["POST"])
def unlink_contact(contact: str, doctype: str, name: str) -> None:
	"""A contact can belong to several records, so removing it from one only drops that link."""
	contact_doc = frappe.get_doc("Contact", contact)
	contact_doc.links = [
		link for link in contact_doc.links if (link.link_doctype, link.link_name) != (doctype, name)
	]
	contact_doc.save()


@frappe.whitelist()
def get_attachments(gig: str) -> list[dict]:
	"""Members are website users, and File only lists those to the uploader, so the gig grants access."""
	frappe.get_doc("Gig", gig).check_permission("read")

	return frappe.get_all(
		"File",
		filters={"attached_to_doctype": "Gig", "attached_to_name": gig},
		fields=["name", "file_name", "file_url", "file_size", "owner", "creation"],
		order_by="creation asc",
	)


@frappe.whitelist()
def get_emails(doctype: str, name: str) -> list[dict]:
	"""A record's thread, oldest first: emails written from it, plus those Frappe linked to it through a contact."""
	if doctype not in THREAD_DOCTYPES:
		frappe.throw(
			_("Emails can only be listed for {0}, not {1}").format(", ".join(THREAD_DOCTYPES), doctype)
		)
	frappe.get_doc(doctype, name).check_permission("read")

	referencing = frappe.get_all(
		"Communication", filters={"reference_doctype": doctype, "reference_name": name}, pluck="name"
	)
	linked = frappe.get_all(
		"Communication Link",
		filters={"parenttype": "Communication", "link_doctype": doctype, "link_name": name},
		pluck="parent",
	)
	thread_root = [name] if doctype == "Communication" else []
	emails = frappe.get_all(
		"Communication",
		filters={
			"communication_medium": "Email",
			"communication_type": "Communication",
			"name": ["in", [*thread_root, *referencing, *linked]],
		},
		# Reply all leaves out the shared account's own address
		fields=[*EMAIL_SUMMARY_FIELDS, "content", "email_account.email_id as account_email"],
		order_by="communication_date asc",
	)
	attachments = frappe.get_all(
		"File",
		filters={
			"attached_to_doctype": "Communication",
			"attached_to_name": ["in", [email.name for email in emails]],
		},
		fields=["name", "file_name", "file_url", "attached_to_name"],
		order_by="creation asc",
	)
	for email in emails:
		email.attachments = [file for file in attachments if file.attached_to_name == email.name]
	return emails


@frappe.whitelist()
def get_comments(doctype: str, name: str) -> list[dict]:
	"""Members are website users, who can't list Comment themselves, so the record grants access."""
	if doctype not in COMMENT_DOCTYPES:
		frappe.throw(
			_("Comments can only be listed for {0}, not {1}").format(", ".join(COMMENT_DOCTYPES), doctype)
		)
	frappe.get_doc(doctype, name).check_permission("read")

	return frappe.get_all(
		"Comment",
		filters={"comment_type": "Comment", "reference_doctype": doctype, "reference_name": name},
		fields=["name", "content", "comment_email", "comment_by", "creation"],
		order_by="creation asc",
	)


@frappe.whitelist()
def get_mailbox(sent_or_received: str) -> list[dict]:
	"""The shared account's mail, newest first, each with the record whose thread it belongs to."""
	frappe.only_for(("Band Member", "System Manager"))
	if sent_or_received not in ("Sent", "Received"):
		frappe.throw(_("Mailbox is either Sent or Received, not {0}").format(sent_or_received))

	# ponytail: last 200 emails of every account, page and filter by Email Account if the band adds a second mailbox
	emails = frappe.get_all(
		"Communication",
		filters={
			"communication_medium": "Email",
			"communication_type": "Communication",
			"sent_or_received": sent_or_received,
		},
		fields=[*EMAIL_SUMMARY_FIELDS, "seen", "reference_doctype", "reference_name"],
		order_by="communication_date desc",
		limit=200,
	)
	links = frappe.get_all(
		"Communication Link",
		filters={
			"parenttype": "Communication",
			"parent": ["in", [email.name for email in emails]],
			"link_doctype": ["in", DIRECTORY_DOCTYPES],
		},
		fields=["parent", "link_doctype", "link_name"],
		order_by="idx asc",
	)
	for email in emails:
		email.thread = _thread_of(email, [link for link in links if link.parent == email.name])
	return emails


def _thread_of(email, directory_links):
	if email.reference_doctype in THREAD_DOCTYPES:
		return {"doctype": email.reference_doctype, "name": email.reference_name}
	if directory_links:
		return {"doctype": directory_links[0].link_doctype, "name": directory_links[0].link_name}
	return {"doctype": "Communication", "name": email.name}


@frappe.whitelist(methods=["POST"])
def mark_seen(name: str) -> None:
	"""Frappe only marks mail seen when it was fetched over IMAP, so opening it in the Inbox does it here."""
	email = frappe.get_doc("Communication", name)
	email.check_permission("read")
	email.db_set("seen", 1, update_modified=False)


@frappe.whitelist()
def get_planning() -> list[dict]:
	"""Gantt bars in lanes: one per live gig ordered by its first date, then "Other" for tasks without a gig."""
	gigs = frappe.get_list(
		"Gig",
		filters={"status": ["not in", ("Declined", "Dropped")]},
		fields=["name", "title", "gig_owner", "gig_date", "application_opens", "application_closes"],
		limit_page_length=0,
	)
	tasks = frappe.get_list(
		"Band Task",
		fields=["name", "title", "done", "gig", "assignee", "start_date", "due_date"],
		limit_page_length=0,
	)

	lanes = {gig.name: [] for gig in gigs}
	for gig in gigs:
		record = {"name": gig.name, "gig": gig.name, "person": gig.gig_owner}
		if gig.application_opens or gig.application_closes:
			lanes[gig.name].append(
				_bar(
					f"{gig.name}-window",
					gig.title,
					_("Application window"),
					gig.application_opens,
					gig.application_closes,
					"window",
					record,
				)
			)
		if gig.gig_date:
			lanes[gig.name].append(
				_bar(f"{gig.name}-date", gig.title, _("Gig"), gig.gig_date, gig.gig_date, "gig", record)
			)

	gig_titles = {gig.name: gig.title for gig in gigs}
	other_lane = []
	dated_tasks = [task for task in tasks if task.start_date or task.due_date]
	for task in sorted(dated_tasks, key=lambda task: task.start_date or task.due_date):
		if task.gig and task.gig not in lanes:
			continue
		lane = lanes[task.gig] if task.gig else other_lane
		lane_title = gig_titles[task.gig] if task.gig else _("Other")
		kind = "done" if task.done else "task"
		record = {"name": task.name, "gig": task.gig, "person": task.assignee}
		lane.append(_bar(task.name, lane_title, task.title, task.start_date, task.due_date, kind, record))

	gig_lanes = sorted(filter(None, lanes.values()), key=lambda lane: min(bar["start"] for bar in lane))
	return [bar for lane in [*gig_lanes, other_lane] for bar in lane]


def _bar(bar_id, lane, label, start, end, kind, record):
	"""`start`/`end` fill each other in to draw the bar; `saved_start`/`saved_end` are what Undo restores."""
	return {
		"id": bar_id,
		"lane": lane,
		"label": label,
		"start": str(start or end),
		"end": str(end or start),
		"saved_start": start,
		"saved_end": end,
		"kind": kind,
		**record,
	}


# The fields a dragged Planning bar writes back: (DocType, start field, end field). A gig is a single day.
RESCHEDULED_FIELDS = {
	"window": ("Gig", "application_opens", "application_closes"),
	"gig": ("Gig", "gig_date", None),
	"task": ("Band Task", "start_date", "due_date"),
	"done": ("Band Task", "start_date", "due_date"),
}


@frappe.whitelist(methods=["POST"])
def reschedule(kind: str, name: str, start: str | None = None, end: str | None = None) -> None:
	if kind not in RESCHEDULED_FIELDS:
		frappe.throw(
			_("Only {0} bars can be rescheduled, not {1}").format(", ".join(RESCHEDULED_FIELDS), kind)
		)
	doctype, start_field, end_field = RESCHEDULED_FIELDS[kind]
	record = frappe.get_doc(doctype, name)
	record.set(start_field, start)
	if end_field:
		record.set(end_field, end)
	record.save()


@frappe.whitelist()
def get_members() -> list[dict]:
	frappe.only_for(("Band Member", "System Manager"))

	return frappe.get_all(
		"User",
		filters=[["Has Role", "role", "=", "Band Member"], ["enabled", "=", 1]],
		fields=["name", "full_name", "user_image"],
		order_by="full_name asc",
		distinct=True,
	)


def can_use_drive() -> bool:
	# Drive refuses its share and permission calls to anyone without its Drive User role.
	return "drive" in frappe.get_installed_apps() and "Drive User" in frappe.get_roles()


@frappe.whitelist(methods=["POST"])
def share_drive_link(entity_name: str) -> str:
	if not can_use_drive():
		frappe.throw(
			_("Linking Drive items needs Frappe Drive and the Drive User role"), frappe.PermissionError
		)

	entity = frappe.get_doc("File", entity_name)
	# Drive serves these types elsewhere (Writer, Slides, the link target), never at /drive/f/.
	if not entity.team or entity.file_type in ("Link", "Document", "Presentation"):
		frappe.throw(
			_("Only files and folders from a Drive team can be linked, not {0}").format(entity.file_name)
		)

	from drive.api.permissions import get_user_access

	# Sharing again would reset the public access Drive already grants, such as comment rights.
	if not get_user_access(entity, "Guest")["read"]:
		# Drive overrides the File class with share(), which checks the caller's share permission.
		entity.share(user="", read=1)
	return frappe.utils.get_url(f"/drive/{'d' if entity.is_folder else 'f'}/{entity.name}")


# Router paths, not site paths: the SPA's router is already mounted at /roadie.
NOTIFICATION_ROUTES = {"Gig": "/", "Band Task": "/tasks"}
SPA_BASE = "/roadie"
NOTIFICATION_FIELDS = [
	"name",
	"type",
	"subject",
	"title",
	"description",
	"document_type",
	"document_name",
	"link",
	"read",
	"creation",
]


@frappe.whitelist()
def get_notifications() -> list[dict]:
	"""The caller's in-app notifications: unread first, newest first, capped."""
	frappe.only_for(("Band Member", "System Manager"))

	notifications = frappe.get_all(
		"Notification Log",
		filters={"for_user": frappe.session.user},
		fields=NOTIFICATION_FIELDS,
		order_by="read asc, creation desc",
		limit=50,
	)
	for notification in notifications:
		notification.route = _notification_route(notification)
	return notifications


def _notification_route(notification) -> str | None:
	"""A Notification Log's own link is a site path like /roadie/tasks, which the router would double."""
	if notification.document_type in NOTIFICATION_ROUTES:
		return NOTIFICATION_ROUTES[notification.document_type]
	path = urlsplit(notification.link or "").path
	if not path.startswith(SPA_BASE):
		return None
	return path[len(SPA_BASE) :] or "/"


@frappe.whitelist(methods=["POST"])
def mark_notifications_read(names: list[str] | None = None) -> None:
	"""Clears the unread flag on the caller's notifications, all of them or just those in `names`."""
	frappe.only_for(("Band Member", "System Manager"))

	filters = {"for_user": frappe.session.user, "read": 0}
	if names:
		filters["name"] = ["in", names]
	frappe.db.set_value("Notification Log", filters, "read", 1, update_modified=False)


def has_app_permission() -> bool:
	return frappe.has_permission("Gig", "read")
