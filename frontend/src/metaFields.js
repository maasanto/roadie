import { joinList, toFraction } from "./directory.js";
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
			default: DYNAMIC_DEFAULT.test(field.default) ? undefined : field.default,
			...controls[field.fieldname],
		}));
}

// A multiselect is an array in the form and one comma-separated string in the database. A rating is a count of
// stars in the form and a fraction in the database.
const STORED_VALUE = { multiselect: joinList, rating: toFraction };

export const toStoredValue = (field, value) => STORED_VALUE[field.type]?.(value) ?? value;
