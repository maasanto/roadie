import { RATING_STARS, toStars } from "./directory.js";
import { isBlank } from "./listFilters.js";

const stars = (fraction) => "★".repeat(toStars(fraction)).padEnd(RATING_STARS, "☆");

// Version keeps values as Frappe displays them, a date in the site's format, a fee with its currency. A checkbox and
// a rating it keeps raw, and a choice in the language of whoever made the change.
const FORMAT_BY_FIELDTYPE = {
	Check: (value) => (Number(value) ? __("Yes") : __("No")),
	Select: (value) => __(String(value)),
	Rating: stars,
};

const formatChangedValue = (fieldtype, value) => FORMAT_BY_FIELDTYPE[fieldtype]?.(value) ?? String(value);

// Version formats only a value that is set, so a fee or a rating of 0 stays a bare 0: it reads as unset, as on the
// form. A checkbox's 0 is its No.
const isUnset = (fieldtype, value) => isBlank(value) || (value === 0 && fieldtype !== "Check");

function describeChange({ label, fieldtype, from, to }) {
	const field = __(label);
	if (isUnset(fieldtype, from)) return __("set {0} to {1}", [field, formatChangedValue(fieldtype, to)]);
	if (isUnset(fieldtype, to)) return __("cleared {0}", [field]);
	return __("changed {0} from {1} to {2}", [
		field,
		formatChangedValue(fieldtype, from),
		formatChangedValue(fieldtype, to),
	]);
}

const DESCRIPTIONS = {
	created: () => __("created this record"),
	changed: describeChange,
	commented: () => __("commented"),
	attached: () => __("attached a file"),
	detached: () => __("removed a file"),
	emailed: () => __("sent an email"),
};

export const describeActivity = (entry) => DESCRIPTIONS[entry.type](entry);
