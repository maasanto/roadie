import { translatedOptions } from "./translation.js";

export const GIG_STATUSES = [
	"Idea",
	"Contacted",
	"Applied",
	"Negotiating",
	"Booked",
	"Played",
	"Declined",
	"Dropped",
];

export const pipelineColumns = [
	...GIG_STATUSES.slice(0, 6).map((status) => ({ label: __(status), statuses: [status] })),
	{ label: __("Declined / Dropped"), statuses: ["Declined", "Dropped"] },
];

// The columns the gig list opens with, labelled in the DocType's own words like a directory list's.
export const gigListColumns = [
	{ fieldname: "title", label: "Title" },
	{ fieldname: "status", label: "Status" },
	{ fieldname: "gig_date", label: "Gig date", format: "date" },
	{ fieldname: "festival", label: "Festival" },
	{ fieldname: "venue", label: "Venue" },
	{ fieldname: "application_closes", label: "Application closes", format: "date" },
	{ fieldname: "gig_owner", label: "Owner" },
];

// Matches the owner reminder sent 7 days before an application closes.
const DEADLINE_WARNING_DAYS = 7;
const DAY_MS = 24 * 60 * 60 * 1000;

export function daysUntil(isoDate) {
	const todayIso = new Date().toLocaleDateString("en-CA");
	return Math.round((Date.parse(isoDate) - Date.parse(todayIso)) / DAY_MS);
}

export const isDeadlineClose = (isoDate) => daysUntil(isoDate) <= DEADLINE_WARNING_DAYS;

export function formatDate(isoDate) {
	const date = new Date(`${isoDate}T00:00:00`);
	const isThisYear = date.getFullYear() === new Date().getFullYear();
	return date.toLocaleDateString(window.lang, {
		day: "numeric",
		month: "short",
		year: isThisYear ? undefined : "numeric",
	});
}

// Intl only knows ISO codes while Frappe takes any Currency name, and a site may have no default at all: either
// way the fee shows as a plain amount rather than breaking the board.
export function formatFee(amount) {
	try {
		return amount.toLocaleString(window.lang, {
			style: "currency",
			currency: window.currency,
			trailingZeroDisplay: "stripIfInteger",
		});
	} catch {
		return amount.toLocaleString(window.lang, { maximumFractionDigits: 2 });
	}
}

// The band's own name for the fee, or null once the form customiser hid it.
export function feeLabelOf(metaFields) {
	const field = metaFields.find((metaField) => metaField.fieldname === "fee");
	return field && !field.hidden ? __(field.label || field.fieldname) : null;
}

export const totalFee = (gigs) => gigs.reduce((total, gig) => total + (gig.fee || 0), 0);

const toOptions = (rows, labelField) =>
	(rows || []).map((row) => ({ label: row[labelField], value: row.name }));

// The members a gig can be assigned to, labelled by name and valued by their user id.
export const memberOptions = (members) => toOptions(members, "full_name");

export function gigControls({ festivals, venues, promoters, members }) {
	return {
		// The pipeline has one column per status it knows, so a status added in Desk would hide its gigs.
		status: { options: translatedOptions(GIG_STATUSES) },
		gig_owner: { type: "combobox", options: memberOptions(members), default: window.user },
		festival: { type: "combobox", options: toOptions(festivals, "title") },
		venue: { type: "combobox", options: toOptions(venues, "title") },
		promoter: { type: "combobox", options: toOptions(promoters, "title") },
	};
}
