import re

# acme.com, www.acme.com:8080/apply?x=1: what a member types for a website, short of the scheme.
BARE_HOST = re.compile(r"[\w-]+(\.[\w-]+)+(:\d+)?([/?#]\S*)?")


def imply_https(doc, method=None):
	"""Frappe rejects a URL without a scheme, while members type a website as they say it: acme.com.
	Anything else is left for Frappe to reject, so a stray "N/A" never becomes a dead link."""
	for field in doc.meta.get("fields", {"fieldtype": "Data", "options": "URL"}):
		url = (doc.get(field.fieldname) or "").strip()
		if BARE_HOST.fullmatch(url):
			doc.set(field.fieldname, f"https://{url}")
