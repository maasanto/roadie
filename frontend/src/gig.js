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

const toOptions = (rows, labelField) =>
	(rows || []).map((row) => ({ label: row[labelField], value: row.name }));

export function gigControls({ festivals, venues, promoters, members }) {
	return {
		// The pipeline has one column per status it knows, so a status added in Desk would hide its gigs.
		status: { options: translatedOptions(GIG_STATUSES) },
		gig_owner: { type: "combobox", options: toOptions(members, "full_name"), default: window.user },
		festival: { type: "combobox", options: toOptions(festivals, "title") },
		venue: { type: "combobox", options: toOptions(venues, "title") },
		promoter: { type: "combobox", options: toOptions(promoters, "title") },
	};
}
