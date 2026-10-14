// Filters, quick filters and sort for the directory lists, adapted from Frappe CRM's list view
// (https://github.com/frappe/crm, frontend/src/components/Filter.vue, SortBy.vue and ViewControls.vue),
// Copyright (C) Frappe Technologies Pvt. Ltd., AGPL-3.0. Modified for Roadie in October 2026: one filter per
// field, as CRM keeps them, and a single sort key instead of CRM's stack.
import { toFraction } from "./directory.js";

// A form control decides how a field is filtered: what it can be compared with, and what a value looks like.
const KIND_BY_CONTROL = {
	number: "number",
	rating: "rating",
	date: "date",
	select: "select",
	// A link's stored value is a generated id nobody types, so it is picked from the records it links to.
	combobox: "select",
	checkbox: "check",
};

export const filterKind = (field) => KIND_BY_CONTROL[field.type] ?? "text";

const OPERATORS = {
	text: ["like", "not like", "=", "!=", "is"],
	number: ["=", "!=", ">", "<", ">=", "<=", "is"],
	rating: ["=", "!=", ">", "<", ">=", "<="],
	date: ["=", ">", "<", ">=", "<=", "is"],
	select: ["=", "!=", "is"],
	check: ["="],
};

const OPERATOR_LABELS = {
	like: __("Contains"),
	"not like": __("Does not contain"),
	"=": __("Equals"),
	"!=": __("Not equals"),
	">": ">",
	"<": "<",
	">=": ">=",
	"<=": "<=",
	is: __("Is"),
};

export const operatorOptions = (field) =>
	OPERATORS[filterKind(field)].map((operator) => ({ label: OPERATOR_LABELS[operator], value: operator }));

// A quick filter narrows as one types for text, and keeps the entries rated at least that well.
export const quickOperator = (field) => ({ text: "like", rating: ">=" }[filterKind(field)] ?? "=");

export function defaultValue(field, operator) {
	if (operator === "is") return "set";
	const kind = filterKind(field);
	if (kind === "select") return field.options?.[0]?.value ?? "";
	if (kind === "check") return "Yes";
	return "";
}

export const newFilter = (field) => {
	const operator = OPERATORS[filterKind(field)][0];
	return { fieldname: field.fieldname, operator, value: defaultValue(field, operator) };
};

export const isBlank = (value) =>
	value === "" || value === null || value === undefined || (Array.isArray(value) && !value.length);

function queryValue(field, { operator, value }) {
	if (operator === "is") return value;
	if (operator === "like" || operator === "not like") return `%${value}%`;
	const kind = filterKind(field);
	if (kind === "check") return value === "Yes" ? 1 : 0;
	if (kind === "rating") return toFraction(value);
	if (kind === "number") return Number(value);
	return value;
}

// The filters as useList sends them, keyed by fieldname. A filter still waiting for its value filters nothing,
// and neither does one on a field the DocType no longer has.
export function queryFilters(filters, fields) {
	const query = {};
	for (const filter of filters) {
		const field = fields.find((candidate) => candidate.fieldname === filter.fieldname);
		if (!field || isBlank(filter.value)) continue;
		query[filter.fieldname] = [filter.operator, queryValue(field, filter)];
	}
	return query;
}

// What a quick filter shows: its own filter's value, not one set to another operator from the Filter menu.
export function quickValue(filters, field) {
	const filter = filters.find(
		(candidate) => candidate.fieldname === field.fieldname && candidate.operator === quickOperator(field)
	);
	return filter?.value ?? "";
}

// Setting a quick filter replaces whatever filter its field had; clearing it removes that filter.
export function setQuickValue(filters, field, value) {
	const others = filters.filter((filter) => filter.fieldname !== field.fieldname);
	if (isBlank(value)) return others;
	return [...others, { fieldname: field.fieldname, operator: quickOperator(field), value }];
}

const DEFAULT_ORDER = "relevance desc, title asc";

// The name breaks ties, so entries sorted on a shared value keep a stable order between loads.
export function orderBy(sort) {
	if (!sort) return DEFAULT_ORDER;
	const order = `${sort.fieldname} ${sort.direction}`;
	return sort.fieldname === "title" ? order : `${order}, title asc`;
}

// The database sorts an empty value first, so an ascending sort on a date would bury the dated rows under the rest.
export const sortEmptyLast = (rows, fieldname) =>
	rows.toSorted((first, second) => isBlank(first[fieldname]) - isBlank(second[fieldname]));

// Filters and sort live in the address, so a reload, a shared link or the back button brings the same list back.
// The address can be typed by hand, so only what the menus could have made for the list's fields is kept: the
// menus and the request then agree on what filters the list.
export const filtersToQuery = (filters) =>
	filters.length
		? JSON.stringify(filters.map(({ fieldname, operator, value }) => [fieldname, operator, value]))
		: undefined;

function fitsField(field, operator, value) {
	const kind = filterKind(field);
	if (!OPERATORS[kind].includes(operator)) return false;
	if (operator === "is") return ["set", "not set"].includes(value);
	if (kind === "check") return ["Yes", "No"].includes(value);
	return typeof value === "string" || Number.isFinite(value);
}

export function filtersFromQuery(param, fields) {
	let triples;
	try {
		triples = JSON.parse(param);
	} catch {
		return [];
	}
	if (!Array.isArray(triples)) return [];
	const filters = [];
	for (const triple of triples) {
		if (!Array.isArray(triple)) continue;
		const [fieldname, operator, value] = triple;
		const field = fields.find((candidate) => candidate.fieldname === fieldname);
		// One filter per field, as the Filter menu keeps them.
		const isDuplicate = filters.some((filter) => filter.fieldname === fieldname);
		if (field && !isDuplicate && fitsField(field, operator, value))
			filters.push({ fieldname, operator, value });
	}
	return filters;
}

export const sortToQuery = (sort) => (sort ? `${sort.fieldname}:${sort.direction}` : undefined);

// A sort on a field the list does not offer would reach the database as an unknown column.
export function sortFromQuery(param, fields) {
	const [fieldname, direction] = typeof param === "string" ? param.split(":") : [];
	const isValid =
		["asc", "desc"].includes(direction) && fields.some((field) => field.fieldname === fieldname);
	return isValid ? { fieldname, direction } : null;
}
