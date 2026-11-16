import frappe

from roadie.install import ROLE

# Band Members share every mailbox on the site, but Frappe only opens an email to the users linked to its Email
# Account. Members are linked when they join and when an account is added, never on later saves, so a link an admin
# removes, or one Frappe drops with its deleted account, stays gone.


def link_new_member_to_every_mailbox(user, method=None):
	if not _is_member(user) or _is_member(user.get_doc_before_save()):
		return
	linked = {row.email_account for row in user.user_emails}
	for account in frappe.get_all("Email Account", fields=["name", "email_id", "enable_outgoing"]):
		if account.name not in linked:
			user.append("user_emails", _link_to(account))


def link_every_member(email_account, method=None):
	"""Inserts the rows rather than saving each member, which would run the whole User save for one link."""
	members = frappe.get_all("User", filters=[["Has Role", "role", "=", ROLE]], pluck="name", distinct=True)
	linked = set(frappe.get_all("User Email", filters={"email_account": email_account.name}, pluck="parent"))
	for member in set(members) - linked:
		frappe.get_doc(
			{
				"doctype": "User Email",
				"parenttype": "User",
				"parentfield": "user_emails",
				"parent": member,
				**_link_to(email_account),
			}
		).db_insert()


def _link_to(account):
	# Links are validated, and their fetch_from fields filled, before a validate hook runs, and db_insert fills none.
	# awaiting_password is left out: copied over, it would ask every member for the band mailbox's password.
	return {
		"email_account": account.name,
		"email_id": account.email_id,
		"enable_outgoing": account.enable_outgoing,
	}


def _is_member(user):
	return bool(user) and ROLE in {row.role for row in user.roles}
