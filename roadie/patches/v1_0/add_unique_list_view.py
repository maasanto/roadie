import frappe


def execute():
	"""One saved layout per member per DocType, held by the database and not only by the controller's validate."""
	drop_duplicates()
	frappe.db.add_unique("Roadie List View", ["dt", "owner"], constraint_name="unique_list_view_per_member")


def drop_duplicates():
	"""Two tabs could insert a layout each before the constraint existed; the screen reads the newest row."""
	rows = frappe.get_all("Roadie List View", fields=["name", "dt", "owner"], order_by="modified desc")

	for name in names_to_drop(rows):
		frappe.db.delete("Roadie List View", {"name": name})


def names_to_drop(rows: list[dict]) -> list[str]:
	"""The rows repeating a `dt`/`owner` pair already seen in `rows`, which are ordered newest first."""
	seen = set()
	repeated = []
	for row in rows:
		key = (row["dt"], row["owner"])
		if key in seen:
			repeated.append(row["name"])
		else:
			seen.add(key)
	return repeated
