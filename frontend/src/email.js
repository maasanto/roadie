export const splitEmails = (value) =>
	(value || "")
		.split(",")
		.map((email) => email.trim())
		.filter(Boolean);

export const isEmail = (value) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);

export function splitRecipients(text) {
	const entries = text.split(/[,;\s]+/).filter(Boolean);
	return { valid: entries.filter(isEmail), invalid: entries.filter((entry) => !isEmail(entry)) };
}

const FAILED_STATUSES = [
	"Bounced",
	"Soft-Bounced",
	"Rejected",
	"Error",
	"Expired",
	"Marked As Spam",
	"Recipient Unsubscribed",
];
const QUEUED_STATUSES = ["", "Sending", "Scheduled", "Delayed"];

export const isFailedDelivery = (status) => FAILED_STATUSES.includes(status);

export function deliveryState(status) {
	if (isFailedDelivery(status)) return { label: __("Error"), theme: "red" };
	if (QUEUED_STATUSES.includes(status || "")) return { label: __("Queued"), theme: "orange" };
	return { label: __("Sent"), theme: "green" };
}

const parseServerDate = (value) => new Date(value.replace(" ", "T"));

export const formatDateTime = (value) =>
	parseServerDate(value).toLocaleString(window.lang, {
		dateStyle: "medium",
		timeStyle: "short",
	});

export function formatListDate(value) {
	const date = parseServerDate(value);
	const isToday = date.toDateString() === new Date().toDateString();
	return date.toLocaleString(window.lang, isToday ? { timeStyle: "short" } : { dateStyle: "medium" });
}

// Gmail, Thunderbird and Apple Mail mark their quotes. Roadie's own replies end on a bare blockquote and its
// attribution, so only one closing the email folds: a blockquote anywhere else is the sender's own content.
// ponytail: Outlook marks quotes with ids per version, add its markers if the band's correspondents use it.
export const QUOTE_SELECTOR = [
	".gmail_quote",
	".moz-cite-prefix",
	"blockquote[type=cite]",
	"body > blockquote:last-child",
	"body > p:has(+ blockquote:last-child)",
].join(", ");

export const isUnread = (email) => email.sent_or_received === "Received" && !email.seen;

export function openByDefault(emails) {
	const isLatest = (index) => index === emails.length - 1;
	return new Set(
		emails.filter((email, index) => isLatest(index) || isUnread(email)).map((email) => email.name)
	);
}

// Plain-text emails are stored as escaped text with every CRLF doubled, which the rich-text renderer would collapse.
export function asHtml(content) {
	if (/<[a-z][\s\S]*>/i.test(content || "")) return content;
	const paragraphs = (content || "").trim().split(/\n{2,}/);
	return paragraphs.map((paragraph) => `<p>${paragraph.replaceAll("\n", "<br>")}</p>`).join("");
}

// The folded-quote markers in QUOTE_SELECTOR expect exactly this shape: an intro paragraph, then the blockquote.
const quote = (email, intro) => `<p></p><p>${intro}</p><blockquote>${asHtml(email.content)}</blockquote>`;

// Below an empty paragraph for the cursor and above any quote, which must stay last for QUOTE_SELECTOR to fold
// it. The quote's own leading empty paragraph then spaces the signature from it.
export function withSignature(content, signature) {
	return signature ? `<p></p>${asHtml(signature)}${content}` : content;
}

// Received headers keep display names: "Bob <bob@example.com>".
const bareAddress = (recipient) => (recipient.match(/<([^>]+)>/)?.[1] ?? recipient).trim();

export function replyDraft(email, mode) {
	const isOtherParty = (address) => address.toLowerCase() !== (email.account_email || "").toLowerCase();
	const addresses = (value) => splitEmails(value).map(bareAddress).filter(isOtherParty);
	const isReceived = email.sent_or_received === "Received";
	const author = email.sender_full_name || email.sender;
	const attribution = __("On {0}, {1} wrote:", [formatDateTime(email.communication_date), author]);
	const to = isReceived ? [email.sender] : addresses(email.recipients);
	if (mode === "reply-all" && isReceived) to.push(...addresses(email.recipients));
	return {
		to: [...new Set(to)],
		cc: mode === "reply-all" ? addresses(email.cc) : [],
		subject: /^re:/i.test(email.subject || "") ? email.subject : `Re: ${email.subject || ""}`,
		content: quote(email, attribution),
		inReplyTo: email.name,
	};
}

const escapeHtml = (text) => text.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");

// Outlook in French prefixes forwards with "TR:", and French typography puts a space before the colon.
const FORWARD_PREFIX = /^\s*(fwd?|tr)\s*:/i;

// Not a reply, so no In-Reply-To: the new recipient never saw the original.
export function forwardDraft(email) {
	// Frappe stores the bare address as the full name when the sender gave none.
	const hasDisplayName = email.sender_full_name && email.sender_full_name !== email.sender;
	const sender = hasDisplayName ? `${email.sender_full_name} <${email.sender}>` : email.sender;
	const header = [
		`---------- ${__("Forwarded message")} ---------`,
		__("From: {0}", [sender]),
		__("Date: {0}", [formatDateTime(email.communication_date)]),
		__("Subject: {0}", [email.subject || ""]),
		// A Bcc copy has no To header.
		email.recipients && __("To: {0}", [email.recipients]),
		email.cc && __("Cc: {0}", [email.cc]),
	].filter(Boolean);
	return {
		subject: FORWARD_PREFIX.test(email.subject || "") ? email.subject : `Fwd: ${email.subject || ""}`,
		content: quote(email, header.map(escapeHtml).join("<br>")),
		attachments: email.attachments,
	};
}
