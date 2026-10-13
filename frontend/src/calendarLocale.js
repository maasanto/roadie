// Labels for frappe-ui's date picker calendar, which vite.config.js swaps in for its English, Sunday-first ones.
const weekday = new Intl.DateTimeFormat(window.lang, { weekday: "narrow" });
const month = new Intl.DateTimeFormat(window.lang, { month: "short" });

// 1 January 2023 was a Sunday, so day 1 + n of that month is weekday n.
export const weekdayInitials = Array.from({ length: 7 }, (_, column) =>
	weekday.format(new Date(2023, 0, 1 + ((window.week_start + column) % 7)))
);

export const monthNames = Array.from({ length: 12 }, (_, index) => month.format(new Date(2023, index, 1)));
