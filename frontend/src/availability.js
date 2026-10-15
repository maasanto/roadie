// A row's answer is blank until the member replies.
export const AVAILABILITY_STATES = {
	Yes: { label: __("Available"), dot: "bg-surface-green-6" },
	No: { label: __("Not available"), dot: "bg-surface-red-6" },
	"": { label: __("No answer yet"), dot: "bg-surface-gray-5" },
};

export const availabilityState = (answer) => AVAILABILITY_STATES[answer || ""];

// What a gig card shows of the answers: how many of the members asked can play, red as soon as one can't, green once
// every one of them can.
export function availabilitySummary(rows = []) {
	const available = rows.filter((row) => row.answer === "Yes").length;
	const declined = rows.filter((row) => row.answer === "No").length;
	const summary = { available, declined, asked: rows.length, tone: "" };
	if (declined) return { ...summary, tone: "text-ink-red-7" };
	if (rows.length && available === rows.length) return { ...summary, tone: "text-ink-green-6" };
	return summary;
}

const unavailableNames = (rows, members) =>
	rows
		.filter((row) => row.answer === "No")
		.map((row) => members.find((member) => member.name === row.member)?.full_name || row.member);

// A warning, not a block: a stand-in may cover for whoever can't play. Takes every gig being booked at once, each
// as { title, rows }. The members are null until they load.
export function confirmBooking(gigs, members) {
	const refusals = gigs
		.map(({ title, rows }) => [title, unavailableNames(rows || [], members || [])])
		.filter(([, names]) => names.length);
	if (!refusals.length) return true;
	const lines = refusals.map(([title, names]) => __("{0} can't play {1}.", [names.join(", "), title]));
	return window.confirm([...lines, __("Book anyway?")].join("\n"));
}
