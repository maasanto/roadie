// A row's answer is blank until the member replies.
export const AVAILABILITY_STATES = {
	Yes: { label: __("Available"), dot: "bg-surface-green-6" },
	No: { label: __("Not available"), dot: "bg-surface-red-6" },
	"": { label: __("No answer yet"), dot: "bg-surface-gray-5" },
};

export const availabilityState = (answer) => AVAILABILITY_STATES[answer || ""];

const unavailableNames = (rows, members) =>
	rows
		.filter((row) => row.answer === "No")
		.map((row) => members.find((member) => member.name === row.member)?.full_name || row.member);

// A warning, not a block: a stand-in may cover for whoever can't play. The members are null until they load.
export function confirmBooking(title, rows, members) {
	const names = unavailableNames(rows || [], members || []);
	return (
		!names.length || window.confirm(__("{0} can't play {1}. Book it anyway?", [names.join(", "), title]))
	);
}
