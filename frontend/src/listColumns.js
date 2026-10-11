import { directoryType, splitList } from "./directory.js";

// How a column reads the value behind it: `number` groups digits, `label` translates a value the database
// keeps in English, `list` joins a comma-separated one, and the list draws a `rating` as stars. Anything else
// shows as stored.
const FORMATS = ["text", "number", "label", "list", "rating"];

// The column that names the row. It leads every list and cannot be moved or removed.
export const isNameColumn = (column) => column.fieldname === "title";

export const defaultColumns = (doctype) => [...(directoryType(doctype)?.columns ?? [])];

// A saved layout is user input that outlives the app that wrote it, and the row is a Code field anyone can
// hand-edit in Desk: keep what still names a field, in order, once each, and drop the rest.
const isColumn = (column) =>
	Boolean(column) && typeof column.fieldname === "string" && column.fieldname.length > 0;

const cleanColumn = (column) => ({
	fieldname: column.fieldname,
	// The label is stored in the DocType's own words, never as the translation of the moment: a member who
	// saves in French and reads in English gets their columns in English.
	label: column.label ? String(column.label) : column.fieldname,
	format: FORMATS.includes(column.format) ? column.format : "text",
});

// One column per field, however many times a hand-edited layout names it.
const unique = (columns) => {
	const seen = new Set();
	return columns.filter((column) => {
		if (seen.has(column.fieldname)) return false;
		seen.add(column.fieldname);
		return true;
	});
};

export function parseColumns(columns) {
	if (Array.isArray(columns)) return columns;
	if (typeof columns === "string" && columns.trim()) {
		try {
			const parsed = JSON.parse(columns);
			return Array.isArray(parsed) ? parsed : [];
		} catch {
			return [];
		}
	}
	return [];
}

// The member's saved layout, or the type's defaults when they have not saved one. Every column comes back
// in the same shape — fieldname, label, format — so a caller never has to know where it came from.
export function columnsFor(doctype, saved) {
	const columns = unique(parseColumns(saved).filter(isColumn).map(cleanColumn));
	if (!columns.length) return defaultColumns(doctype).map(cleanColumn);

	// The name column leads whatever order it was saved in: it is what a row reads as, and it holds the
	// list's flexible track.
	const name = defaultColumns(doctype).find(isNameColumn);
	if (!name) return columns;

	const saved_name = columns.find(isNameColumn);
	return [saved_name ?? cleanColumn(name), ...columns.filter((column) => !isNameColumn(column))];
}

// What the list fetches: the row's name, which is its identity and key, then every field a column reads.
// Sorted, because reordering columns changes neither what is read nor the response, and an unsorted list
// would re-request the whole type.
export function fetchFields(columns) {
	const fields = new Set(columns.map((column) => column.fieldname));
	fields.delete("name");
	return ["name", ...[...fields].sort()];
}

// Swap a column with its neighbour. The name column leads and stays, so neither end of the list can be
// swapped into it.
export function moveColumn(columns, fieldname, offset) {
	const from = columns.findIndex((column) => column.fieldname === fieldname);
	const to = from + offset;
	if (from <= 0 || to <= 0 || to >= columns.length) return columns;

	const moved = [...columns];
	[moved[from], moved[to]] = [moved[to], moved[from]];
	return moved;
}

// A field picked from the DocType's meta becomes a column: digits group, a choice's stored value translates,
// a multiselect joins, a rating draws stars.
const FORMAT_BY_CONTROL = { number: "number", multiselect: "list", select: "label", rating: "rating" };

export function columnFromField(field) {
	return {
		fieldname: field.fieldname,
		label: field.label,
		format: FORMAT_BY_CONTROL[field.type] ?? "text",
	};
}

export function formatCell(column, row) {
	const value = row?.[column.fieldname];
	if (value === null || value === undefined || value === "") return "";
	if (column.format === "number") {
		const number = Number(value);
		return Number.isFinite(number) ? number.toLocaleString(window.lang) : String(value);
	}
	if (column.format === "label") return __(String(value));
	if (column.format === "list") return splitList(value).join(", ");
	return String(value);
}
