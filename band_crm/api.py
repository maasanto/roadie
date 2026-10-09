import frappe
from frappe import _

DIRECTORY_DOCTYPES = ("Festival", "Venue", "Promoter", "Band")
EMAIL_DOCTYPES = ("Gig",)


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
	"""Members only see Communications through the record they belong to, oldest first like a thread."""
	if doctype not in EMAIL_DOCTYPES:
		frappe.throw(_("Emails can only be listed for {0}, not {1}").format(", ".join(EMAIL_DOCTYPES), doctype))
	frappe.get_doc(doctype, name).check_permission("read")

	emails = frappe.get_all(
		"Communication",
		filters={"communication_medium": "Email", "reference_doctype": doctype, "reference_name": name},
		fields=[
			"name",
			"subject",
			"content",
			"sender",
			"sender_full_name",
			"recipients",
			"cc",
			"sent_or_received",
			"delivery_status",
			"communication_date",
		],
		order_by="communication_date asc",
	)
	attachments = frappe.get_all(
		"File",
		filters={"attached_to_doctype": "Communication", "attached_to_name": ["in", [email.name for email in emails]]},
		fields=["name", "file_name", "file_url", "attached_to_name"],
		order_by="creation asc",
	)
	for email in emails:
		email.attachments = [file for file in attachments if file.attached_to_name == email.name]
	return emails


@frappe.whitelist()
def get_planning() -> list[dict]:
	"""Gantt bars in lanes: one per live gig ordered by its first date, then "Other" for tasks without a gig."""
	gigs = frappe.get_list(
		"Gig",
		filters={"status": ["not in", ("Declined", "Dropped")]},
		fields=["name", "title", "gig_date", "application_opens", "application_closes"],
		limit_page_length=0,
	)
	tasks = frappe.get_list(
		"Band Task",
		fields=["name", "title", "done", "gig", "start_date", "due_date"],
		limit_page_length=0,
	)

	lanes = {gig.name: [] for gig in gigs}
	for gig in gigs:
		if gig.application_opens or gig.application_closes:
			lanes[gig.name].append(
				_bar(f"{gig.name}-window", gig.title, _("Application window"), gig.application_opens, gig.application_closes, "window")
			)
		if gig.gig_date:
			lanes[gig.name].append(_bar(f"{gig.name}-date", gig.title, _("Gig"), gig.gig_date, gig.gig_date, "gig"))

	gig_titles = {gig.name: gig.title for gig in gigs}
	other_lane = []
	dated_tasks = [task for task in tasks if task.start_date or task.due_date]
	for task in sorted(dated_tasks, key=lambda task: task.start_date or task.due_date):
		if task.gig and task.gig not in lanes:
			continue
		lane = lanes[task.gig] if task.gig else other_lane
		lane_title = gig_titles[task.gig] if task.gig else _("Other")
		kind = "done" if task.done else "task"
		lane.append(_bar(task.name, lane_title, task.title, task.start_date, task.due_date, kind))

	gig_lanes = sorted(filter(None, lanes.values()), key=lambda lane: min(bar["start"] for bar in lane))
	return [bar for lane in [*gig_lanes, other_lane] for bar in lane]


def _bar(bar_id, lane, label, start, end, kind):
	return {"id": bar_id, "lane": lane, "label": label, "start": str(start or end), "end": str(end or start), "kind": kind}


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
