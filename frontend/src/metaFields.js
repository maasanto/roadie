import { joinList, toFraction } from "./directory.js";
import { isBlank } from "./listFilters.js";
import { translatedOptions } from "./translation.js";

// Field types a form can edit without a dedicated picker. Anything else, a table or an attachment
// added in Desk, stays out of the form rather than breaking it.
const CONTROL_TYPES = {
	Data: "text",
	"Small Text": "textarea",
	Text: "textarea",
	"Long Text": "textarea",
	Int: "number",
	Float: "number",
	Currency: "number",
	Date: "date",
	Check: "checkbox",
	Select: "select",
	Rating: "rating",
};

// Defaults such as "Today", "__user" or ":Company" are resolved by the server on insert, never by the browser.
const DYNAMIC_DEFAULT = /^(__|:|eval:)|^(today|now)$/i;

const controlType = ({ fieldtype, options }) =>
	fieldtype === "Data" && options === "URL" ? "url" : CONTROL_TYPES[fieldtype];

// Members only hold permlevel 0, so a higher level would show a field whose edits the server drops.
const isFormField = (field, controls) =>
	!field.permlevel && Boolean(controls[field.fieldname] || controlType(field));

// The form's fields as the DocType meta has them, so a field added, renamed or hidden in Desk shows here too.
// Hidden fields stay in the list, flagged, so the form customiser can bring them back.
export function fieldsFromMeta(metaFields, controls = {}) {
	return metaFields
		.filter((field) => isFormField(field, controls))
		.map((field) => ({
			fieldname: field.fieldname,
			label: __(field.label || field.fieldname),
			type: controlType(field),
			hidden: Boolean(field.hidden),
			// A required checkbox would force a tick, while Frappe accepts an unticked one.
			required: Boolean(field.reqd) && field.fieldtype !== "Check",
			disabled: Boolean(field.read_only || (field.fetch_from && !field.fetch_if_empty)),
			options:
				field.fieldtype === "Select"
					? translatedOptions((field.options || "").split("\n").filter(Boolean))
					: undefined,
			linkTo: field.fieldtype === "Link" ? field.options : undefined,
			default: DYNAMIC_DEFAULT.test(field.default) ? undefined : field.default,
			...controls[field.fieldname],
		}));
}

// A field that depends on another, a gig's edition on its festival, offers only the options of the value picked
// there. With nothing picked there, it offers them all.
export const optionsFor = (field, form) =>
	field.dependsOn && form[field.dependsOn]
		? field.options.filter((option) => option[field.dependsOn] === form[field.dependsOn])
		: field.options;

// Whether the field holds a pick of another parent than the one now picked. An option not loaded yet cannot be
// told apart from one of the right parent, so it is kept.
export function isStalePick(field, form) {
	const picked = field.dependsOn && field.options.find((option) => option.value === form[field.fieldname]);
	return Boolean(picked) && picked[field.dependsOn] !== form[field.dependsOn];
}

// A field added from the form customiser gets Frappe's custom_ prefix, so a "City" added to the gig matches the
// festival's own city.
const sharedName = (fieldname) => fieldname.replace(/^custom_/, "");

// Every record has these, and no gig field means them.
const STANDARD_FIELDS = new Set([
	"name",
	"owner",
	"creation",
	"modified",
	"modified_by",
	"docstatus",
	"idx",
	"doctype",
]);

// A title and notes describe the picked record itself rather than the gig.
const NOT_FILLED_FROM_PICK = new Set(["title", "notes"]);

// Frappe stores an unset number as 0, so a picked record's 0 is nothing to fill in.
const isFilledOnPick = (value) => Boolean(value) && !isBlank(value);

// Only a blank field is filled, or one this picker filled before and the member left alone: picking another record
// replaces it, or blanks it when that record holds nothing for it. A checkbox can't tell untouched from unticked,
// so it is never filled.
export function valuesFromPick(fields, form, pickedDoc, previousFill = {}) {
	const pickedValues = {};
	for (const [fieldname, value] of Object.entries(pickedDoc))
		if (!STANDARD_FIELDS.has(fieldname) && isFilledOnPick(value))
			pickedValues[sharedName(fieldname)] = value;

	const values = {};
	for (const { fieldname, type, disabled } of fields) {
		const name = sharedName(fieldname);
		const wasFilledByPick = fieldname in previousFill && form[fieldname] === previousFill[fieldname];
		const isFillable = isBlank(form[fieldname]) || wasFilledByPick;
		if (NOT_FILLED_FROM_PICK.has(name) || type === "checkbox" || disabled || !isFillable) continue;
		if (name in pickedValues) values[fieldname] = pickedValues[name];
		else if (wasFilledByPick) values[fieldname] = "";
	}
	return values;
}

// A multiselect is an array in the form and one comma-separated string in the database. A rating is a count of
// stars in the form and a fraction in the database.
const STORED_VALUE = { multiselect: joinList, rating: toFraction };

export const toStoredValue = (field, value) => STORED_VALUE[field.type]?.(value) ?? value;
