export const splitEmails = (value) =>
	(value || "")
		.split(",")
		.map((email) => email.trim())
		.filter(Boolean);

export const isEmail = (value) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);

const FAILED_STATUSES = ["Bounced", "Soft-Bounced", "Rejected", "Error", "Expired", "Marked As Spam", "Recipient Unsubscribed"];
const QUEUED_STATUSES = ["", "Sending", "Scheduled", "Delayed"];

export function deliveryState(status) {
	if (FAILED_STATUSES.includes(status)) return { label: __("Error"), theme: "red" };
	if (QUEUED_STATUSES.includes(status || "")) return { label: __("Queued"), theme: "orange" };
	return { label: __("Sent"), theme: "green" };
}

export const formatDateTime =(value) =>
	new Date(value.replace(" ", "T")).toLocaleString(window.lang, { dateStyle: "medium", timeStyle: "short" });

// Plain-text emails are stored as escaped text with every CRLF doubled, which the rich-text renderer would collapse.
export function asHtml(content) {
	if (/<[a-z][\s\S]*>/i.test(content || "")) return content;
	const paragraphs = (content || "").trim().split(/\n{2,}/);
	return paragraphs.map((paragraph) => `<p>${paragraph.replaceAll("\n", "<br>")}</p>`).join("");
}

function quote(email) {
	const author = email.sender_full_name || email.sender;
	const attribution = __("On {0}, {1} wrote:", [formatDateTime(email.communication_date), author]);
	return `<p></p><p>${attribution}</p><blockquote>${asHtml(email.content)}</blockquote>`;
}

export function replyDraft(email, mode) {
	const to = email.sent_or_received === "Received" ? [email.sender] : splitEmails(email.recipients);
	return {
		to,
		cc: mode === "reply-all" ? splitEmails(email.cc) : [],
		subject: /^re:/i.test(email.subject || "") ? email.subject : `Re: ${email.subject || ""}`,
		content: quote(email),
		inReplyTo: email.name,
	};
}
