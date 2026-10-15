import frappe
from frappe.utils import add_years, getdate, nowdate

from roadie.roadie.doctype.roadie_settings.roadie_settings import clean_columns, clean_quick_filters

MOVED_FIELDS = ("application_url", "application_opens", "application_closes")


def execute():
	"""The application window belonged to the festival, so every year overwrote the last. It now lives on one
	edition per year: each festival gets the edition its window was for, and its gigs of that year point at it."""
	# Model sync leaves a removed field's column in place; without it there is nothing left to move.
	if not frappe.db.has_column("Festival", "application_opens"):
		return

	festival = frappe.qb.DocType("Festival")
	festivals = (
		frappe.qb.from_(festival)
		.select(festival.name, *(festival[field] for field in MOVED_FIELDS))
		.run(as_dict=True)
	)
	for row in festivals:
		if not frappe.db.exists("Festival Edition", {"festival": row.name}):
			create_edition(row)

	forget_moved_fields_in_directory_settings()


def guess_edition_year(festival):
	"""A window often opens the year before the festival it is for, so the edition takes the year of the first gig
	within a year after the window closes, or after today without a window. Earlier gigs belong to past editions,
	and gigs further out to editions whose window the festival never held."""
	window_end = getdate(festival.application_closes or festival.application_opens or nowdate())
	first_gig_after = frappe.db.get_value(
		"Gig",
		{"festival": festival.name, "gig_date": ("between", (window_end, add_years(window_end, 1)))},
		"gig_date",
		order_by="gig_date asc",
	)
	return getdate(first_gig_after or window_end).year


def create_edition(festival):
	year = guess_edition_year(festival)
	edition = frappe.get_doc(
		{
			"doctype": "Festival Edition",
			"festival": festival.name,
			"year": year,
			**{field: festival[field] for field in MOVED_FIELDS},
		}
	).insert()
	frappe.db.set_value(
		"Gig",
		{
			"festival": festival.name,
			"festival_edition": ("is", "not set"),
			"gig_date": ("between", (f"{year}-01-01", f"{year}-12-31")),
		},
		"festival_edition",
		edition.name,
		update_modified=False,
	)


def forget_moved_fields_in_directory_settings():
	"""A saved Festival layout naming a moved field would keep showing the festival's frozen copy of it."""
	settings = frappe.get_single("Roadie Settings")
	columns = frappe.parse_json(settings.directory_columns or "{}") or {}
	quick_filters = frappe.parse_json(settings.directory_quick_filters or "{}") or {}
	if columns.get("Festival"):
		columns["Festival"] = clean_columns("Festival", columns["Festival"])
	if quick_filters.get("Festival"):
		quick_filters["Festival"] = clean_quick_filters("Festival", quick_filters["Festival"])
	frappe.db.set_single_value(
		"Roadie Settings",
		{
			"directory_columns": frappe.as_json(columns),
			"directory_quick_filters": frappe.as_json(quick_filters),
		},
	)
