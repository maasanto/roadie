import re
from collections import Counter
from urllib.parse import urlsplit

import frappe
from frappe import _
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.email import relink
from markupsafe import Markup

from roadie.roadie.doctype.roadie_settings.roadie_settings import clean_columns, clean_quick_filters

DIRECTORY_DOCTYPES = ("Festival", "Venue", "Promoter", "Band")
CUSTOMISABLE_DOCTYPES = ("Gig", *DIRECTORY_DOCTYPES)
# The lists whose columns and quick filters the band sets: the directory's and the gig list.
LIST_DOCTYPES = ("Gig", *DIRECTORY_DOCTYPES)
# The pipeline, the planning and the reminders read these, so hiding one would quietly break them.
PROTECTED_FIELDS = ("title", "status", "gig_owner", "gig_date", "application_opens", "application_closes")
# Text, long text, number, date, checkbox and choice list: the types a form edits without a picker.
NEW_FIELD_TYPES = ("Data", "Small Text", "Float", "Date", "Check", "Select")
# Mirrors the controls of frontend/src/metaFields.js, plus Link for the gig's pickers.
FORM_FIELD_TYPES = (*NEW_FIELD_TYPES, "Text", "Long Text", "Int", "Currency", "Rating", "Link")
EMAIL_DOCTYPES = ("Gig", "Band Task", *DIRECTORY_DOCTYPES)
COMMENT_DOCTYPES = ("Gig", *DIRECTORY_DOCTYPES)
# Frappe roots a thread linked to no record on its first Communication, so that Communication is a thread too.
THREAD_DOCTYPES = (*EMAIL_DOCTYPES, "Communication")
# The composer stamps its uploads with this, so a draft can only ever delete a file it uploaded itself.
EMAIL_DRAFT_FIELD = "roadie_email_draft"
MAILBOX_ROLES = ("Band Member", "System Manager")
# A task's emails show in its dialog only, so a thread filed there would drop out of every record's history.
LINKABLE_DOCTYPES = ("Gig", *DIRECTORY_DOCTYPES)
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
	"seen",
]
MAILBOX_SEARCH_FIELDS = ("subject", "sender", "sender_full_name", "recipients", "cc")


SEARCH_DOCTYPES = ("Gig", "Band Task", *DIRECTORY_DOCTYPES)
SEARCH_RESULTS_PER_TYPE = 5
SEARCH_QUERY_MAX_LENGTH = 100


@frappe.whitelist()
def search(query: str) -> list[dict]:
	"""Grouped, permission-checked matches for the command palette, a handful per type at most."""
	query = _clean_query(query)
	if not query:
		return []

	needle = f"%{query}%"
	groups = []
	for doctype in SEARCH_DOCTYPES:
		# get_list throws rather than return nothing when the caller cannot read the DocType.
		if not frappe.has_permission(doctype, "read"):
			continue
		or_filters = [["title", "like", needle]]
		fields = ["name", "title"]
		if doctype in DIRECTORY_DOCTYPES:
			or_filters.append(["city", "like", needle])
			fields.append("city")
		matches = frappe.get_list(
			doctype,
			or_filters=or_filters,
			fields=fields,
			order_by="title asc",
			limit_page_length=SEARCH_RESULTS_PER_TYPE,
		)
		if matches:
			groups.append({"doctype": doctype, "results": matches})
	return groups


def _clean_query(query):
	query = (query or "").strip()
	if len(query) > SEARCH_QUERY_MAX_LENGTH:
		frappe.throw(
			_("Search is limited to {0} characters, not {1}").format(SEARCH_QUERY_MAX_LENGTH, len(query))
		)
	return query


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


@frappe.whitelist(methods=["POST"])
def delete_draft_attachment(file: str) -> None:
	"""The composer attaches an upload to the record straight away, so a file the email never sent must go."""
	draft_file = frappe.get_doc("File", file)
	# Sending copies the file onto the Communication with the same URL. Frappe dedupes uploads by content,
	# so an older email of the same bytes shares that URL too: only a copy made since this upload means sent.
	is_sent = frappe.db.exists(
		"File",
		{
			"file_url": draft_file.file_url,
			"attached_to_doctype": "Communication",
			"creation": [">=", draft_file.creation],
			"name": ["!=", file],
		},
	)
	if (
		draft_file.owner != frappe.session.user
		or draft_file.attached_to_field != EMAIL_DRAFT_FIELD
		or is_sent
	):
		frappe.throw(
			_("This file isn't an unsent email attachment of yours, so it can't be deleted from a draft"),
			frappe.PermissionError,
		)
	draft_file.delete()


@frappe.whitelist()
def get_emails(doctype: str, name: str) -> list[dict]:
	"""A record's thread, oldest first: emails written from it, plus those Frappe linked to it through a contact."""
	_check_readable_thread(doctype, name)
	emails = _thread_emails(
		doctype,
		name,
		# Reply all leaves out the shared account's own address
		fields=[*EMAIL_SUMMARY_FIELDS, "content", "email_account.email_id as account_email"],
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


def _check_readable_thread(doctype, name):
	if doctype not in THREAD_DOCTYPES:
		frappe.throw(
			_("Emails can only be listed for {0}, not {1}").format(", ".join(THREAD_DOCTYPES), doctype)
		)
	frappe.get_doc(doctype, name).check_permission("read")


def _thread_emails(doctype, name, fields):
	referencing = frappe.get_all(
		"Communication", filters={"reference_doctype": doctype, "reference_name": name}, pluck="name"
	)
	linked = frappe.get_all(
		"Communication Link",
		filters={"parenttype": "Communication", "link_doctype": doctype, "link_name": name},
		pluck="parent",
	)
	thread_root = [name] if doctype == "Communication" else []
	return frappe.get_all(
		"Communication",
		filters={
			"communication_medium": "Email",
			"communication_type": "Communication",
			"name": ["in", [*thread_root, *referencing, *linked]],
		},
		fields=fields,
		order_by="communication_date asc",
	)


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
def get_gig_activity() -> dict[str, dict]:
	"""What the board's cards show of every gig the member can read: unread emails, open tasks and the earliest
	one's due date, comments and attachments. Members can't list Comment or File themselves, so the gig grants
	access, as it does in its panel. A gig with none of these is left out."""
	# ponytail: every readable gig, not only the board's filtered ones; take the board's names if a band keeps thousands
	gigs = frappe.get_list("Gig", pluck="name", limit=0)
	if not gigs:
		return {}

	counts = [
		_unread_emails(gigs),
		frappe.get_all(
			"Band Task",
			filters={"gig": ["in", gigs], "done": 0},
			fields=["gig", {"COUNT": "*", "as": "open_tasks"}, {"MIN": "due_date", "as": "next_due"}],
			group_by="gig",
		),
		frappe.get_all(
			"Comment",
			filters={"comment_type": "Comment", "reference_doctype": "Gig", "reference_name": ["in", gigs]},
			fields=["reference_name as gig", {"COUNT": "*", "as": "comments"}],
			group_by="reference_name",
		),
		frappe.get_all(
			"File",
			filters={"attached_to_doctype": "Gig", "attached_to_name": ["in", gigs]},
			fields=["attached_to_name as gig", {"COUNT": "*", "as": "attachments"}],
			group_by="attached_to_name",
		),
	]
	activity = {}
	for rows in counts:
		for row in rows:
			activity.setdefault(row.pop("gig"), {}).update(row)
	return activity


def _unread_emails(gigs):
	"""Counted from the emails the gig's thread shows, which opening it marks seen."""
	unread = {
		"communication_medium": "Email",
		"communication_type": "Communication",
		"sent_or_received": "Received",
		"seen": 0,
	}
	referencing = frappe.get_all(
		"Communication",
		filters={**unread, "reference_doctype": "Gig", "reference_name": ["in", gigs]},
		fields=["name", "reference_name as gig"],
	)
	linked = frappe.get_all(
		"Communication",
		filters=[
			*([field, "=", value] for field, value in unread.items()),
			["Communication Link", "link_doctype", "=", "Gig"],
			["Communication Link", "link_name", "in", gigs],
		],
		fields=["name", "`tabCommunication Link`.link_name as gig"],
	)
	# An email can both be written from a gig and reach it through a contact.
	emails = {(email.gig, email.name) for email in [*referencing, *linked]}
	return [
		frappe._dict(gig=gig, unread_emails=count) for gig, count in Counter(gig for gig, _ in emails).items()
	]


@frappe.whitelist()
def get_mailbox(sent_or_received: str, query: str | None = None, limit: int = 200) -> list[dict]:
	"""The shared account's threads, newest first: each one's latest email in this direction, with how many
	emails and unread emails it holds in that direction. Only the latest `limit` emails are read, and with a query
	only those whose subject, sender or recipients contain it."""
	frappe.only_for(MAILBOX_ROLES)
	if sent_or_received not in ("Sent", "Received"):
		frappe.throw(_("Mailbox is either Sent or Received, not {0}").format(sent_or_received))
	# Frappe reads a limit of 0 as no limit at all.
	if limit < 1:
		frappe.throw(_("The mailbox lists at least one email, not {0}").format(limit))

	query = _clean_query(query)
	# ponytail: every account's emails, filter by Email Account if the band adds a second mailbox
	emails = frappe.get_all(
		"Communication",
		filters={
			"communication_medium": "Email",
			"communication_type": "Communication",
			"sent_or_received": sent_or_received,
		},
		or_filters={field: ["like", f"%{query}%"] for field in MAILBOX_SEARCH_FIELDS} if query else None,
		fields=[*EMAIL_SUMMARY_FIELDS, "reference_doctype", "reference_name"],
		order_by="communication_date desc",
		limit=limit,
	)
	links = _directory_links([email.name for email in emails])
	threads = {}
	for email in emails:
		email.directory_links = links.get(email.name, [])
		thread = _thread_of(email, email.directory_links)
		latest = threads.setdefault(
			(thread["doctype"], thread["name"]),
			{**email, "thread": thread, "count": 0, "unread": 0, "holds_filed_mail": False},
		)
		latest["count"] += 1
		latest["unread"] += not email.seen
		# Bulk delete refuses a conversation holding mail filed under a record, so the list can say so upfront.
		latest["holds_filed_mail"] = latest["holds_filed_mail"] or _is_filed(email)
	return [frappe._dict(thread) for thread in threads.values()]


def _thread_of(email, directory_links):
	if email.reference_doctype in THREAD_DOCTYPES:
		return {"doctype": email.reference_doctype, "name": email.reference_name}
	if directory_links:
		return {"doctype": directory_links[0].link_doctype, "name": directory_links[0].link_name}
	return {"doctype": "Communication", "name": email.name}


def _directory_links(email_names):
	links = frappe.get_all(
		"Communication Link",
		filters={
			"parenttype": "Communication",
			"parent": ["in", email_names],
			"link_doctype": ["in", DIRECTORY_DOCTYPES],
		},
		fields=["parent", "link_doctype", "link_name"],
		order_by="idx asc",
	)
	by_email = {}
	for link in links:
		by_email.setdefault(link.parent, []).append(link)
	return by_email


def _mailbox_thread(thread):
	"""The emails a mailbox row stands for. A record's own thread shows more: the mail its contacts are copied on,
	which the mailbox files under the thread that mail replies to, so acting on the row must not reach it."""
	thread = {"doctype": thread["doctype"], "name": thread["name"]}
	_check_readable_thread(thread["doctype"], thread["name"])
	emails = _thread_emails(
		thread["doctype"],
		thread["name"],
		fields=["name", "sent_or_received", "seen", "reference_doctype", "reference_name"],
	)
	links = _directory_links([email.name for email in emails])
	for email in emails:
		email.directory_links = links.get(email.name, [])
	return [email for email in emails if _thread_of(email, email.directory_links) == thread]


@frappe.whitelist(methods=["POST"])
def mark_thread_seen(doctype: str, name: str) -> None:
	"""Frappe only marks mail seen when it was fetched over IMAP, so opening a thread in the Inbox does it here."""
	unseen = [
		email.name
		for email in get_emails(doctype, name)
		if email.sent_or_received == "Received" and not email.seen
	]
	if unseen:
		frappe.db.set_value("Communication", {"name": ["in", unseen]}, "seen", 1, update_modified=False)


def _set_seen(emails, seen):
	names = [email.name for email in emails if email.seen != seen]
	if names:
		frappe.db.set_value("Communication", {"name": ["in", names]}, "seen", seen, update_modified=False)


def _received(thread):
	return [email for email in _mailbox_thread(thread) if email.sent_or_received == "Received"]


# Bulk read and unread act on what a mailbox row stands for, while opening a thread marks all it shows. In Roadie
# only: the mailbox server already holds every fetched email as read, and Frappe pushes no flag back to it.
@frappe.whitelist(methods=["POST"])
def mark_threads_read(threads: list[dict]) -> None:
	frappe.only_for(MAILBOX_ROLES)
	_set_seen([email for thread in threads for email in _received(thread)], 1)


@frappe.whitelist(methods=["POST"])
def mark_threads_unread(threads: list[dict]) -> None:
	"""Only each thread's latest received email: enough to bring the thread back as unread."""
	frappe.only_for(MAILBOX_ROLES)
	_set_seen([email for thread in threads for email in _received(thread)[-1:]], 0)


@frappe.whitelist(methods=["POST"])
def delete_threads(names: list[str]) -> None:
	"""Bulk delete clears conversations filed under nothing. Mail of a gig, a venue or any other document goes
	one email at a time. Roadie's copy only: the mailbox server keeps its own."""
	frappe.only_for(MAILBOX_ROLES)
	# Every conversation is checked before any is deleted: deleting an email removes its attachments from disk,
	# which a refusal further down the list would not roll back.
	conversations = []
	for name in names:
		# Gone already: a bandmate deleted it during the undo window.
		if not frappe.db.exists("Communication", name):
			continue
		emails = _mailbox_thread({"doctype": "Communication", "name": name})
		if name not in [email.name for email in emails] or any(_is_filed(email) for email in emails):
			frappe.throw(
				_(
					"Only conversations filed under no gig, task or directory entry can be deleted in bulk, not {0}"
				).format(name)
			)
		conversations.append(emails)
	for emails in conversations:
		for email in emails:
			_delete_email(email.name)


def _is_filed(email):
	return bool(email.directory_links) or email.reference_doctype not in (None, "", "Communication")


@frappe.whitelist(methods=["POST"])
def delete_email(name: str) -> dict:
	"""Deleting an email its replies hang on hands its place to the next reply, which the caller gets back as
	`promoted`. Roadie's copy only: the mailbox server keeps its own."""
	frappe.only_for(MAILBOX_ROLES)
	email = frappe.get_doc("Communication", name)
	directory_links = [link for link in email.timeline_links if link.link_doctype in DIRECTORY_DOCTYPES]
	if name not in [each.name for each in _mailbox_thread(_thread_of(email, directory_links))]:
		frappe.throw(_("Only the emails Roadie lists can be deleted here, not {0}").format(name))

	replies = frappe.get_all(
		"Communication",
		filters={"reference_doctype": "Communication", "reference_name": name, "name": ["!=", name]},
		order_by="communication_date asc",
		pluck="name",
	)
	promoted = replies[0] if replies else None
	if promoted:
		_promote(email, promoted, replies[1:])
	_delete_email(name)
	return {"promoted": promoted}


def _promote(email, promoted, other_replies):
	# Warning: a root references nothing, never itself. Frappe follows a Communication's reference chain on every
	# insert, and a self-reference makes the next reply loop forever.
	if email.reference_doctype:
		reference = {"reference_doctype": email.reference_doctype, "reference_name": email.reference_name}
		frappe.db.set_value("Communication", {"name": ["in", [promoted, *other_replies]]}, reference)
	else:
		reference = {"reference_doctype": "Communication", "reference_name": promoted}
		frappe.db.set_value("Communication", promoted, {"reference_doctype": None, "reference_name": None})
		if other_replies:
			frappe.db.set_value("Communication", {"name": ["in", other_replies]}, reference)
	# Frappe threads an inbound reply through the queue row of the email it answers.
	frappe.db.set_value(
		"Email Queue", {"reference_doctype": "Communication", "reference_name": email.name}, reference
	)


def _delete_email(name):
	# A reply's in_reply_to would otherwise keep pointing here and fail link validation on its next save.
	frappe.db.set_value("Communication", {"in_reply_to": name}, "in_reply_to", None, update_modified=False)
	# Members have no delete right on Communication: these endpoints are the only way in, and they check access.
	# force skips the link check that in_reply_to and reference_name would trip.
	frappe.delete_doc("Communication", name, ignore_permissions=True, force=True)


@frappe.whitelist(methods=["POST"])
def link_thread(communication: str, doctype: str, name: str) -> None:
	"""Files a conversation filed under nothing under a gig or directory record. A reply takes its record from the
	Email Queue entry it answers, or else from the email itself, so both move for later replies to follow."""
	if doctype not in LINKABLE_DOCTYPES:
		frappe.throw(
			_("Emails can only be filed under {0}, not {1}").format(", ".join(LINKABLE_DOCTYPES), doctype)
		)
	# The right Frappe asks for to send an email from the record itself.
	frappe.get_doc(doctype, name).check_permission("email")
	emails = [email.name for email in _mailbox_thread({"doctype": "Communication", "name": communication})]
	# A reply or a filed email would move without the rest of its conversation.
	if communication not in emails:
		frappe.throw(
			_("Only conversations filed under no gig, task or directory entry can be linked, not {0}").format(
				communication
			)
		)

	for email in emails:
		relink(email, doctype, name)
	frappe.db.set_value(
		"Email Queue",
		{"communication": ["in", emails]},
		{"reference_doctype": doctype, "reference_name": name},
		update_modified=False,
	)


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


@frappe.whitelist()
def get_directory_columns() -> dict:
	"""The columns each directory list and the gig list show, keyed by DocType: one setting for the whole site."""
	frappe.only_for(("Band Member", "System Manager"))

	return frappe.parse_json(frappe.db.get_single_value("Roadie Settings", "directory_columns") or "{}") or {}


@frappe.whitelist(methods=["POST"])
def set_directory_columns(doctype: str, columns: str) -> None:
	"""Replace one type's columns. An empty list puts that type back on the columns the app ships."""
	frappe.only_for(("Band Member", "System Manager"))
	if doctype not in LIST_DOCTYPES:
		frappe.throw(_("{0} is not a directory list").format(doctype))

	settings = frappe.get_doc("Roadie Settings")
	all_columns = frappe.parse_json(settings.directory_columns or "{}") or {}
	all_columns[doctype] = clean_columns(doctype, frappe.parse_json(columns))
	settings.directory_columns = frappe.as_json(all_columns)
	settings.save()


@frappe.whitelist()
def get_directory_quick_filters() -> dict:
	"""The quick filters each directory list offers, keyed by DocType: one setting for the whole site."""
	frappe.only_for(("Band Member", "System Manager"))

	return (
		frappe.parse_json(frappe.db.get_single_value("Roadie Settings", "directory_quick_filters") or "{}")
		or {}
	)


@frappe.whitelist(methods=["POST"])
def set_directory_quick_filters(doctype: str, fieldnames: str) -> None:
	"""Replace one type's quick filters. An empty list leaves that type with none."""
	frappe.only_for(("Band Member", "System Manager"))
	if doctype not in LIST_DOCTYPES:
		frappe.throw(_("{0} is not a directory list").format(doctype))

	settings = frappe.get_doc("Roadie Settings")
	all_filters = frappe.parse_json(settings.directory_quick_filters or "{}") or {}
	all_filters[doctype] = clean_quick_filters(doctype, frappe.parse_json(fieldnames))
	settings.directory_quick_filters = frappe.as_json(all_filters)
	settings.save()


@frappe.whitelist(methods=["POST"])
def add_form_field(doctype: str, label: str, fieldtype: str, options: str | None = None) -> str:
	"""Members are website users who cannot write Custom Field, so Roadie adds the field on their behalf."""
	check_customisable(doctype)
	if fieldtype not in NEW_FIELD_TYPES:
		frappe.throw(_("A new field is one of {0}, not {1}").format(", ".join(NEW_FIELD_TYPES), fieldtype))
	choices = "\n".join(filter(None, (line.strip() for line in (options or "").splitlines())))
	if fieldtype == "Select" and not choices:
		frappe.throw(_("A choice list needs at least one choice"))

	field = frappe.get_doc(
		{
			"doctype": "Custom Field",
			"dt": doctype,
			"label": clean_label(label),
			"fieldtype": fieldtype,
			# The blank first choice keeps Frappe from defaulting every new record to the first real one.
			"options": f"\n{choices}" if fieldtype == "Select" else None,
			"insert_after": "append",
			"is_system_generated": 0,
		}
	)
	field.insert(ignore_permissions=True)
	return field.fieldname


@frappe.whitelist(methods=["POST"])
def rename_form_field(doctype: str, fieldname: str, label: str) -> None:
	check_customisable_field(doctype, fieldname)
	set_field_property(doctype, fieldname, "label", clean_label(label), "Data")


@frappe.whitelist(methods=["POST"])
def set_form_field_hidden(doctype: str, fieldname: str, hidden: bool) -> None:
	field = check_customisable_field(doctype, fieldname)
	if hidden and (fieldname in PROTECTED_FIELDS or field.reqd):
		frappe.throw(_("{0} cannot be hidden: Roadie relies on it").format(_(field.label)))
	set_field_property(doctype, fieldname, "hidden", int(hidden), "Check")


def check_customisable(doctype: str) -> None:
	frappe.only_for(("Band Member", "System Manager"))
	if doctype not in CUSTOMISABLE_DOCTYPES:
		frappe.throw(
			_("Only the forms of {0} can be customised, not {1}").format(
				", ".join(CUSTOMISABLE_DOCTYPES), doctype
			)
		)


def check_customisable_field(doctype: str, fieldname: str):
	"""Only the fields the Roadie form shows: no layout breaks, tables, or levels members cannot read."""
	check_customisable(doctype)
	field = frappe.get_meta(doctype).get_field(fieldname)
	if not field or field.permlevel or field.fieldtype not in FORM_FIELD_TYPES:
		frappe.throw(_("{0} has no field {1} that Roadie's form shows").format(doctype, fieldname))
	return field


def set_field_property(doctype: str, fieldname: str, property_name: str, value, property_type: str) -> None:
	"""A field someone added by hand is edited in place, as Customize Form does, so Desk can still change it.
	Fields from the DocType or another app's fixtures get a Property Setter, which survives their next sync."""
	if custom_field := frappe.db.get_value(
		"Custom Field", {"dt": doctype, "fieldname": fieldname, "is_system_generated": 0}
	):
		field = frappe.get_doc("Custom Field", custom_field)
		field.set(property_name, value)
		field.save(ignore_permissions=True)
	else:
		make_property_setter(
			doctype, fieldname, property_name, value, property_type, is_system_generated=False
		)


def clean_label(label: str) -> str:
	if not (label := (label or "").strip()):
		frappe.throw(_("A field needs a label"))
	return label


def can_use_drive() -> bool:
	# Drive ships inside the suite app since the standalone one was archived, and refuses its share
	# and permission calls to anyone without the role it reads.
	return "suite" in frappe.get_installed_apps() and "Suite User" in frappe.get_roles()


def is_in_drive(entity) -> bool:
	"""Whether Drive serves this file, which it does only under one of its own two roots."""
	from suite.drive.utils import ROOT_FOLDER, USERS_FOLDER, generate_upward_path

	return generate_upward_path(entity.name)[0]["name"] in (ROOT_FOLDER, USERS_FOLDER)


def is_drive_home(entity) -> bool:
	"""Drive's two roots, or a member's home folder: one link would publish everything under it."""
	from suite.drive.utils import USERS_FOLDER, generate_upward_path

	path = [folder["name"] for folder in generate_upward_path(entity.name)]
	return len(path) == 1 or (path[0] == USERS_FOLDER and len(path) == 2)


@frappe.whitelist(methods=["POST"])
def share_drive_link(entity_name: str) -> str:
	if not can_use_drive():
		frappe.throw(
			_("Linking Drive items needs Frappe Suite and the Suite User role"), frappe.PermissionError
		)

	entity = frappe.get_doc("File", entity_name)
	# Drive serves these types elsewhere (Writer, Slides, the link target), never at /drive/f/.
	if entity.file_type in ("Link", "Document", "Presentation") or not is_in_drive(entity):
		frappe.throw(_("Only files and folders in Drive can be linked, not {0}").format(entity.file_name))
	if is_drive_home(entity):
		frappe.throw(_("{0} holds a whole Drive: link a folder inside it instead").format(entity.file_name))

	from suite.drive.api.permissions import get_user_access_for_user

	# Sharing again would reset the public access Drive already grants, such as comment rights.
	if not get_user_access_for_user(entity, "Guest")["read"]:
		# Drive overrides the File class with share(), which checks the caller's share permission.
		entity.share(user="", read=1)
	return frappe.utils.get_url(f"/drive/{'d' if entity.is_folder else 'f'}/{entity.name}")


SPA_BASE = "/roadie"
# Where a block element ends, so its text doesn't run into the next one's once the tags are stripped.
BLOCK_END = re.compile(r"<(?:br|/p|/div|/li|/h[1-6])\b[^>]*>", re.IGNORECASE)
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
		# A mention keeps the email's HTML in its title and the comment's in its description; the panel shows text.
		notification.title = _html_to_text(notification.title or notification.subject)
		notification.description = _html_to_text(notification.description)
	return notifications


def _html_to_text(html: str | None) -> str:
	return Markup(BLOCK_END.sub(" ", html or "")).striptags()


def _notification_route(notification) -> str | None:
	"""A Notification Log's own link is a site path like /roadie/tasks, which the router would double. A record's
	own screen is resolved by the SPA (notificationRoute in frontend/src/notifications.js), so this is the fallback."""
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
