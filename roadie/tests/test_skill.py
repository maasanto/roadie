import json
import re
import shlex

import frappe
from frappe.model import default_fields
from frappe.tests import IntegrationTestCase


class TestSkill(IntegrationTestCase):
	"""Agents act on what the skill says, so a DocType, field, status or method renamed in the app must fail here."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		with open(frappe.get_app_path("roadie", "roadie", "skills", "roadie", "SKILL.md")) as skill:
			cls.skill = skill.read()

	def test_domain_model_covers_every_doctype_with_existing_fields(self):
		model = dict(re.findall(r"^- \*\*(.+?)\*\* — (.+)$", self.skill, re.MULTILINE))
		self.assertEqual(set(model), set(frappe.get_all("DocType", {"module": "Roadie"}, pluck="name")))
		for doctype, description in model.items():
			self.assertFields(doctype, re.findall(r"`(\w+)`", description))

	def test_statuses_match_the_gig_status_options(self):
		statuses = re.search(r"^Gig statuses.*$", self.skill, re.MULTILINE).group()
		options = frappe.get_meta("Gig").get_field("status").options.split("\n")
		self.assertEqual(re.findall(r"`(\w+)`", statuses), options)

	def test_recipes_use_existing_methods_doctypes_and_fields(self):
		commands = [shlex.split(line)[1:] for line in self.skill.splitlines() if line.startswith("dokos ")]
		self.assertGreaterEqual(len(commands), 10)
		for command, *args in commands:
			if command == "get-list":
				filtered = [condition[0] for condition in option(args, "--filters")]
				self.assertFields(args[0], [*option(args, "--fields"), *filtered])
			elif command == "insert":
				record = json.loads(args[0])
				self.assertFields(record.pop("doctype"), record)
			elif command == "set-value":
				self.assertFields(args[0], [args[2]])
			elif command == "call":
				self.assertIn(frappe.get_attr(args[0]), frappe.whitelisted)
			else:
				self.fail(f"SKILL.md uses `dokos {command}`, which this test does not check yet")

	def assertFields(self, doctype, fieldnames):
		meta = frappe.get_meta(doctype)
		unknown = [field for field in fieldnames if field not in default_fields and not meta.has_field(field)]
		self.assertFalse(unknown, f"SKILL.md names fields {unknown} that {doctype} does not have")


def option(args, flag):
	return json.loads(args[args.index(flag) + 1]) if flag in args else []
