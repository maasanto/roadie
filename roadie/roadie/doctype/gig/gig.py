import frappe
from frappe import _
from frappe.desk.doctype.notification_log.notification_log import make_notification_logs
from frappe.model.document import Document
from frappe.utils import formatdate, get_fullname, get_url

from roadie.api import band_members
from roadie.mentions import record_path

AVAILABILITY_ANSWERS = ("Yes", "No")


class Gig(Document):
	def validate(self):
		self.validate_from_to_dates("application_opens", "application_closes")
		self.validate_festival_edition()
		self.reset_availability_on_new_date()

	def on_update(self):
		if self.flags.ask_availability_again:
			self.notify_availability(
				[row.member for row in self.availability],
				_("{0} moved to {1}: can you still play it?").format(self.title, formatdate(self.gig_date)),
			)

	def validate_festival_edition(self):
		if not self.festival_edition:
			return
		edition_festival, year = frappe.db.get_value(
			"Festival Edition", self.festival_edition, ["festival", "year"]
		)
		if edition_festival != self.festival:
			frappe.throw(
				_(
					"The {0} edition belongs to another festival. Pick an edition of this gig's festival."
				).format(year)
			)

	def reset_availability_on_new_date(self):
		"""The answers were given for the old date, so the band as it is now is asked again."""
		if self.is_new() or not self.availability or not self.has_value_changed("gig_date"):
			return
		for row in self.availability:
			row.answer = ""
		self.sync_availability_rows()
		# A cleared date leaves nothing to ask about until a new one is set.
		self.flags.ask_availability_again = bool(self.gig_date)

	def sync_availability_rows(self):
		"""Adds the performers who joined since, and drops the pending rows of members who left the band or are no
		longer asked. An answer already given stays, as a record of it."""
		performers = [member.name for member in band_members() if member.confirms_availability]
		for row in [row for row in self.availability if not row.answer and row.member not in performers]:
			self.remove(row)
		asked = {row.member for row in self.availability}
		for member in performers:
			if member not in asked:
				self.append("availability", {"member": member})

	def request_availability(self):
		"""Asks every performer who hasn't answered yet, so pressing it again reminds them."""
		if not self.gig_date:
			frappe.throw(_("Set the gig date before asking the band whether they can play it"))
		self.sync_availability_rows()
		if not self.availability:
			frappe.throw(_("No band member is set to confirm their availability, so there is nobody to ask"))
		self.availability_requested_by = self.availability_requested_by or frappe.session.user
		self.save()

		self.notify_availability(
			[row.member for row in self.availability if not row.answer],
			_("{0} asks: can you play {1} on {2}?").format(
				get_fullname(), self.title, formatdate(self.gig_date)
			),
		)

	def answer_availability(self, answer: str):
		if answer not in AVAILABILITY_ANSWERS:
			frappe.throw(_("Answer Yes or No, not {0}").format(answer))
		if not self.gig_date:
			frappe.throw(_("{0} has no date yet, so there is nothing to answer").format(self.title))
		member = frappe.session.user
		row = next((row for row in self.availability if row.member == member), None)
		if not row:
			frappe.throw(_("Nobody asked you whether you can play {0}").format(self.title))
		if row.answer == answer:
			return
		row.answer = answer
		self.save()

		subject = _("{0} can play {1} on {2}") if answer == "Yes" else _("{0} can't play {1} on {2}")
		self.notify_availability(
			[self.gig_owner, self.availability_requested_by],
			subject.format(get_fullname(member), self.title, formatdate(self.gig_date)),
		)

	def notify_availability(self, users, subject):
		"""Created in the request, as mentions are, so the bell and the push don't wait on a background worker."""
		actor = frappe.session.user
		# Frappe notifies the author of an Alert too, and nobody needs telling what they just did.
		recipients = [user for user in users if user and user != actor]
		if not recipients:
			return
		emails = frappe.get_all("User", filters={"name": ["in", recipients], "enabled": 1}, pluck="email")
		if not emails:
			return
		make_notification_logs(
			frappe._dict(
				{
					"type": "Alert",
					"document_type": self.doctype,
					"document_name": self.name,
					"from_user": actor,
					"subject": subject,
					"link": get_url(record_path(self.doctype, self.name)),
				}
			),
			emails,
		)
