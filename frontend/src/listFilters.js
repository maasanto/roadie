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

const isBlank = (value) => value === "" || value === null || value === undefined;

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
