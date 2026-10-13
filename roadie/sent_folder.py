import frappe
from frappe.email.receive import InboundMail


class SentFolderEmailAccount:
	"""Frappe drops the mail an account sent itself, or files a reply as received, so what the band wrote from
	webmail or a phone is rebuilt as sent mail when the Sent folder is pulled: the Outbox then lists it too."""

	def get_inbound_mails(self) -> list[InboundMail]:
		return [
			SentMail(mail.raw_message, self, mail.uid, mail.seen_status, mail.append_to, mail.imap_folder)
			if mail.is_sender_same_as_receiver()
			else mail
			for mail in super().get_inbound_mails()
		]


class SentMail(InboundMail):
	def process(self):
		# Warning: a Frappe site sent it, and the Sent folder also holds password resets and invitations, which
		# members must never read. Mail written in Roadie is skipped for the same reason, being in the Outbox already.
		if self.mail.get("X-Frappe-Site"):
			return None
		if self.message_id and frappe.db.exists("Communication", {"message_id": self.message_id}):
			return None
		return self._build_communication_doc()

	def as_dict(self):
		return {**super().as_dict(), "sent_or_received": "Sent", "delivery_status": "Sent"}
