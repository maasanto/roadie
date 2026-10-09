export const GIG_STATUSES = ["Idea", "Contacted", "Applied", "Negotiating", "Booked", "Played", "Declined", "Dropped"];

export const pipelineColumns = [
	...GIG_STATUSES.slice(0, 6).map((status) => ({ label: status, statuses: [status] })),
	{ label: "Declined / Dropped", statuses: ["Declined", "Dropped"] },
];

// Matches the owner reminder sent 7 days before an application closes.
const DEADLINE_WARNING_DAYS = 7;
const DAY_MS = 24 * 60 * 60 * 1000;

export function daysUntil(isoDate) {
	const todayIso = new Date().toLocaleDateString("en-CA");
	return Math.round((Date.parse(isoDate) - Date.parse(todayIso)) / DAY_MS);
}

export const isDeadlineClose = (isoDate) => daysUntil(isoDate) <= DEADLINE_WARNING_DAYS;

export const formatDate = (isoDate) =>
	new Date(`${isoDate}T00:00:00`).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });

const toOptions = (rows, labelField) => (rows || []).map((row) => ({ label: row[labelField], value: row.name }));

export function gigFields({ festivals, venues, promoters, members }) {
	return [
		{ fieldname: "title", label: "Title", type: "text", required: true },
		{ fieldname: "status", label: "Status", type: "select", options: GIG_STATUSES, default: "Idea" },
		{ fieldname: "gig_owner", label: "Owner", type: "combobox", options: toOptions(members, "full_name"), default: window.user },
		{ fieldname: "gig_date", label: "Gig date", type: "date" },
		{ fieldname: "festival", label: "Festival", type: "combobox", options: toOptions(festivals, "title") },
		{ fieldname: "venue", label: "Venue", type: "combobox", options: toOptions(venues, "title") },
		{ fieldname: "promoter", label: "Promoter", type: "combobox", options: toOptions(promoters, "title") },
		{ fieldname: "fee", label: "Fee", type: "number" },
		{ fieldname: "application_opens", label: "Application opens", type: "date" },
		{ fieldname: "application_closes", label: "Application closes", type: "date" },
		{ fieldname: "notes", label: "Notes", type: "textarea" },
	];
}
