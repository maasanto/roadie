import frappe
from frappe.tests import IntegrationTestCase

from roadie.api import add_form_field, rename_form_field, set_form_field_hidden
from roadie.roadie.doctype.gig.test_gig import MEMBER, make_member

OUTSIDER = "outsider@example.com"


def remove_custom_field(doctype, fieldname):
	"""Adding the field altered the table, which committed it, so its removal has to be committed too."""
	frappe.db.rollback()
	frappe.db.delete("Custom Field", {"dt": doctype, "fieldname": fieldname})
	frappe.db.sql_ddl(f"alter table `tab{doctype}` drop column if exists `{fieldname}`")  # nosemgrep
	frappe.clear_cache(doctype=doctype)


class TestFormCustomisation(IntegrationTestCase):
	def setUp(self):
		make_member(MEMBER, "John")
		frappe.set_user(MEMBER)

	def tearDown(self):
		frappe.set_user("Administrator")
		for doctype, fieldname, property in (
			("Gig", "fee", "label"),
			("Venue", "instagram", "hidden"),
			("Band", "relevance", "hidden"),
		):
			frappe.db.delete(
				"Property Setter", {"doc_type": doctype, "field_name": fieldname, "property": property}
			)
			frappe.clear_cache(doctype=doctype)

	def test_member_adds_a_choice_list_and_the_band_fills_it_in(self):
		fieldname = add_form_field("Festival", " Camping ", "Select", "Tents\n\n Vans \n")
		self.addCleanup(remove_custom_field, "Festival", fieldname)

		field = frappe.get_meta("Festival").get_field(fieldname)
		self.assertEqual((field.label, field.options), ("Camping", "\nTents\nVans"))
		self.assertEqual(frappe.get_meta("Festival").fields[-1].fieldname, fieldname)
		festival = frappe.get_doc(
			{"doctype": "Festival", "title": "Camping Test Festival", fieldname: "Vans"}
		).insert()
		self.assertEqual(frappe.db.get_value("Festival", festival.name, fieldname), "Vans")
		left_blank = frappe.get_doc({"doctype": "Festival", "title": "Undecided Test Festival"}).insert()
		self.assertFalse(frappe.db.get_value("Festival", left_blank.name, fieldname))

	def test_a_field_the_band_added_is_changed_in_place_so_desk_can_still_edit_it(self):
		fieldname = add_form_field("Festival", "Merch stand", "Check")
		self.addCleanup(remove_custom_field, "Festival", fieldname)

		rename_form_field("Festival", fieldname, "Merch table")
		set_form_field_hidden("Festival", fieldname, True)

		custom_field = frappe.db.get_value(
			"Custom Field", {"dt": "Festival", "fieldname": fieldname}, ["label", "hidden"], as_dict=True
		)
		self.assertEqual((custom_field.label, custom_field.hidden), ("Merch table", 1))
		self.assertFalse(
			frappe.db.exists("Property Setter", {"doc_type": "Festival", "field_name": fieldname})
		)

	def test_member_renames_a_field_for_the_whole_band(self):
		rename_form_field("Gig", "fee", "Net fee")

		self.assertEqual(frappe.get_meta("Gig").get_label("fee"), "Net fee")

	def test_member_hides_a_field_and_brings_it_back(self):
		set_form_field_hidden("Venue", "instagram", True)
		self.assertTrue(frappe.get_meta("Venue").get_field("instagram").hidden)

		set_form_field_hidden("Venue", "instagram", False)
		self.assertFalse(frappe.get_meta("Venue").get_field("instagram").hidden)

	def test_member_hides_the_relevance_stars_the_form_offers(self):
		set_form_field_hidden("Band", "relevance", True)

		self.assertTrue(frappe.get_meta("Band").get_field("relevance").hidden)

	def test_fields_the_pipeline_and_planning_rely_on_cannot_be_hidden(self):
		for fieldname in ("status", "gig_date", "application_closes"):
			with self.assertRaises(frappe.ValidationError):
				set_form_field_hidden("Gig", fieldname, True)
		self.assertFalse(frappe.get_meta("Gig").get_field("gig_date").hidden)

	def test_only_roadie_forms_can_be_customised(self):
		with self.assertRaises(frappe.ValidationError):
			add_form_field("Contact", "Nickname", "Data")
		with self.assertRaises(frappe.ValidationError):
			rename_form_field("Gig", "no_such_field", "Anything")
		with self.assertRaises(frappe.ValidationError):
			add_form_field("Festival", "Lineup", "Table")

	def test_a_user_outside_the_band_cannot_customise(self):
		if not frappe.db.exists("User", OUTSIDER):
			frappe.get_doc(
				{"doctype": "User", "email": OUTSIDER, "first_name": "Outsider", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.set_user(OUTSIDER)

		with self.assertRaises(frappe.PermissionError):
			rename_form_field("Gig", "fee", "Free beer")
