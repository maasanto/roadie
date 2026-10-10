import frappe
from frappe.tests import IntegrationTestCase

from roadie.api import get_planning, reschedule
from roadie.roadie.doctype.gig.test_gig import MEMBER, make_member


def make_gig(title, **fields):
	return frappe.get_doc({"doctype": "Gig", "title": title, **fields}).insert()


def make_task(title, **fields):
	return frappe.get_doc({"doctype": "Band Task", "title": title, "assignee": MEMBER, **fields}).insert()


class TestPlanning(IntegrationTestCase):
	def setUp(self):
		make_member(MEMBER, "John")
		frappe.set_user(MEMBER)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_gig_lanes_plot_windows_dates_and_tasks_with_loose_tasks_in_other(self):
		festival_gig = make_gig(
			"Acme Festival 2031",
			application_opens="2031-01-05",
			application_closes="2031-02-15",
			gig_date="2031-07-12",
		)
		club_gig = make_gig("Le Petit Club 2030", gig_date="2030-03-20")
		declined_gig = make_gig("Declined Fest 2030", status="Declined", gig_date="2030-01-01")
		rider = make_task(
			"Send the rider", gig=festival_gig.name, start_date="2031-06-01", due_date="2031-06-10"
		)
		make_task("Chase the declined fest", gig=declined_gig.name, due_date="2030-01-01")
		make_task("Some day", gig=festival_gig.name)
		van = make_task("Book the van", due_date="2031-07-01")

		ours = {festival_gig.name, club_gig.name, declined_gig.name, rider.name, van.name}
		bars = [
			bar for bar in get_planning() if bar["id"].removesuffix("-window").removesuffix("-date") in ours
		]

		self.assertEqual(
			[(bar["lane"], bar["label"], bar["start"], bar["end"], bar["kind"]) for bar in bars],
			[
				("Le Petit Club 2030", "Gig", "2030-03-20", "2030-03-20", "gig"),
				("Acme Festival 2031", "Application window", "2031-01-05", "2031-02-15", "window"),
				("Acme Festival 2031", "Gig", "2031-07-12", "2031-07-12", "gig"),
				("Acme Festival 2031", "Send the rider", "2031-06-01", "2031-06-10", "task"),
				("Other", "Book the van", "2031-07-01", "2031-07-01", "task"),
			],
		)

	def test_dragging_each_bar_writes_only_the_dates_it_was_drawn_from(self):
		gig = make_gig(
			"Acme Festival 2032",
			application_opens="2032-01-05",
			application_closes="2032-02-15",
			gig_date="2032-07-12",
		)
		task = make_task("Send the rider", gig=gig.name, due_date="2032-06-10")

		reschedule("window", gig.name, "2032-01-12", "2032-02-22")
		reschedule("gig", gig.name, "2032-07-19", "2032-07-19")
		reschedule("task", task.name, "2032-06-03", "2032-06-12")

		gig.reload()
		task.reload()
		self.assertEqual(
			[str(gig.application_opens), str(gig.application_closes), str(gig.gig_date)],
			["2032-01-12", "2032-02-22", "2032-07-19"],
		)
		self.assertEqual([str(task.start_date), str(task.due_date)], ["2032-06-03", "2032-06-12"])

		reschedule("task", task.name, None, "2032-06-10")
		task.reload()
		self.assertEqual([task.start_date, str(task.due_date)], [None, "2032-06-10"])

	def test_a_bar_dragged_to_end_before_it_starts_is_refused(self):
		gig = make_gig("Acme Festival 2033", application_opens="2033-01-05", application_closes="2033-02-15")
		task = make_task("Book the van", start_date="2033-06-01", due_date="2033-06-10")

		with self.assertRaises(frappe.ValidationError):
			reschedule("window", gig.name, "2033-03-01", "2033-02-15")
		with self.assertRaises(frappe.ValidationError):
			reschedule("task", task.name, "2033-06-11", "2033-06-10")

		gig.reload()
		self.assertEqual(str(gig.application_opens), "2033-01-05")
