import frappe

from roadie.mailbox_access import link_every_member


def execute():
	for account in frappe.get_all("Email Account", fields=["name", "email_id", "enable_outgoing"]):
		link_every_member(account)
