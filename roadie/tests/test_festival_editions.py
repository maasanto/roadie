import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import nowdate

from roadie.patches import create_festival_editions
from roadie.roadie.doctype.gig.test_gig import MEMBER, make_member

LEGACY_COLUMNS = {
	"application_url": "varchar(140)",
	"application_opens": "date",
	"application_closes": "date",
}


def forget_festival_columns():
	frappe.client_cache.delete_value("table_columns::tabFestival")


def drop_columns(columns):
	for column in columns:
		frappe.db.sql_ddl(f"alter table `tabFestival` drop column `{column}`")
	forget_festival_columns()


class TestCreateFestivalEditions(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		# A fresh install never had the window on Festival, so the columns an upgraded site still holds are put back.
		# DDL commits, so they come and go outside the class's rollback: dropped after it, added before any data.
		missing = [column for column in LEGACY_COLUMNS if not frappe.db.has_column("Festival", column)]
		for column in missing:
			frappe.db.sql_ddl(f"alter table `tabFestival` add column `{column}` {LEGACY_COLUMNS[column]}")
		forget_festival_columns()
		cls.addClassCleanup(drop_columns, missing)
		super().setUpClass()

	def make_legacy_festival(self, title, **window):
		festival = frappe.get_doc({"doctype": "Festival", "title": title}).insert()
		if window:
			table = frappe.qb.DocType("Festival")
			update = frappe.qb.update(table).where(table.name == festival.name)
			for column, value in window.items():
				update = update.set(table[column], value)
			update.run()
		return festival.name

	def make_gig(self, festival, gig_date):
		return frappe.get_doc(
			{"doctype": "Gig", "title": "Acme gig", "festival": festival, "gig_date": gig_date}
		).insert()

	def editions_of(self, festival):
		return frappe.get_all(
			"Festival Edition",
			filters={"festival": festival},
			fields=["name", "year", "application_url", "application_opens", "application_closes"],
		)

	def test_each_festival_gets_the_edition_of_its_window_and_its_gigs_of_that_year(self):
		acme = self.make_legacy_festival(
			"Acme Festival",
			application_url="https://example.com/apply",
			application_opens="2027-02-01",
			application_closes="2027-03-15",
		)
		undated = self.make_legacy_festival("Acme Nights")
		gig_of_the_year = self.make_gig(acme, "2027-07-10")
		gig_of_last_year = self.make_gig(acme, "2026-07-11")
		undated_gig = self.make_gig(undated, None)

		create_festival_editions.execute()
		create_festival_editions.execute()

		[edition] = self.editions_of(acme)
		self.assertEqual(edition.year, 2027)
		self.assertEqual(edition.application_url, "https://example.com/apply")
		self.assertEqual(str(edition.application_opens), "2027-02-01")
		self.assertEqual(str(edition.application_closes), "2027-03-15")
		[undated_edition] = self.editions_of(undated)
		self.assertEqual(undated_edition.year, int(nowdate()[:4]))

		self.assertEqual(self.edition_of(gig_of_the_year), edition.name)
		self.assertIsNone(self.edition_of(gig_of_last_year))
		self.assertIsNone(self.edition_of(undated_gig))

	def edition_of(self, gig):
		return frappe.db.get_value("Gig", gig.name, "festival_edition")

	def test_saved_festival_layout_forgets_the_moved_window(self):
		self.addCleanup(
			frappe.db.set_single_value,
			"Roadie Settings",
			"directory_columns",
			frappe.db.get_single_value("Roadie Settings", "directory_columns"),
		)
		frappe.db.set_single_value(
			"Roadie Settings",
			"directory_columns",
			frappe.as_json(
				{"Festival": [{"fieldname": "title"}, {"fieldname": "application_closes"}], "Venue": []}
			),
		)

		create_festival_editions.execute()

		columns = frappe.parse_json(frappe.db.get_single_value("Roadie Settings", "directory_columns"))
		self.assertEqual([column["fieldname"] for column in columns["Festival"]], ["title"])


class TestFestivalEdition(IntegrationTestCase):
	def setUp(self):
		make_member(MEMBER, "John")
		self.festival = frappe.get_doc({"doctype": "Festival", "title": "Acme Festival"}).insert()

	def tearDown(self):
		frappe.set_user("Administrator")

	def make_edition(self, festival, year=2027, **fields):
		return frappe.get_doc(
			{"doctype": "Festival Edition", "festival": festival, "year": year, **fields}
		).insert()

	def test_member_has_the_same_rights_on_editions_as_on_festivals(self):
		frappe.set_user(MEMBER)
		edition = self.make_edition(self.festival.name)
		for ptype in ("read", "write", "create", "delete", "email"):
			self.assertEqual(
				frappe.has_permission("Festival Edition", ptype, edition),
				frappe.has_permission("Festival", ptype, self.festival),
				ptype,
			)
		self.assertIn(edition.name, [row.name for row in frappe.get_list("Festival Edition")])

	def test_gig_takes_the_edition_window_and_festival_unless_already_set(self):
		edition = self.make_edition(
			self.festival.name, application_opens="2027-01-10", application_closes="2027-02-15"
		)

		frappe.set_user(MEMBER)
		copied = frappe.get_doc(
			{"doctype": "Gig", "title": "Acme 2027", "festival_edition": edition.name}
		).insert()
		edited = frappe.get_doc(
			{
				"doctype": "Gig",
				"title": "Acme 2027 late",
				"festival_edition": edition.name,
				"application_closes": "2027-03-01",
			}
		).insert()

		self.assertEqual(copied.festival, self.festival.name)
		self.assertEqual(str(copied.application_opens), "2027-01-10")
		self.assertEqual(str(copied.application_closes), "2027-02-15")
		self.assertEqual(str(edited.application_closes), "2027-03-01")
		self.assertEqual(copied.gig_owner, MEMBER)

	def test_gig_refuses_an_edition_of_another_festival(self):
		other = frappe.get_doc({"doctype": "Festival", "title": "Acme Nights"}).insert()
		edition = self.make_edition(other.name)

		frappe.set_user(MEMBER)
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Gig",
					"title": "Acme 2027",
					"festival": self.festival.name,
					"festival_edition": edition.name,
				}
			).insert()

	def test_member_deletes_a_festival_with_its_editions_unless_a_gig_holds_one(self):
		other = frappe.get_doc({"doctype": "Festival", "title": "Acme Nights"}).insert()
		self.make_edition(self.festival.name)
		held = self.make_edition(other.name)
		frappe.get_doc(
			{"doctype": "Gig", "title": "Acme Nights 2027", "festival_edition": held.name}
		).insert()

		frappe.set_user(MEMBER)
		frappe.delete_doc("Festival", self.festival.name)
		with self.assertRaises(frappe.LinkExistsError):
			frappe.delete_doc("Festival", other.name)

		self.assertFalse(frappe.db.exists("Festival Edition", {"festival": self.festival.name}))
		self.assertTrue(frappe.db.exists("Festival Edition", held.name))

	def test_edition_stays_with_its_festival(self):
		edition = self.make_edition(self.festival.name)
		other = frappe.get_doc({"doctype": "Festival", "title": "Acme Nights"}).insert()

		edition.festival = other.name
		with self.assertRaises(frappe.CannotChangeConstantError):
			edition.save()

	def test_edition_and_its_application_window_cannot_end_before_they_start(self):
		frappe.set_user(MEMBER)
		for start, end in (("start_date", "end_date"), ("application_opens", "application_closes")):
			with self.subTest(start), self.assertRaises(frappe.ValidationError):
				self.make_edition(self.festival.name, **{start: "2027-07-12", end: "2027-07-10"})
