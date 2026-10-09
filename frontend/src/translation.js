// The page boot carries the catalogue inline (www/band.py), so it is ready before any module builds a label.
const messages = window.translations || {};

export function __(message, replacements = []) {
	const translated = messages[message] || message;
	return translated.replace(/{(\d+)}/g, (placeholder, index) => replacements[index] ?? placeholder);
}

// Select values stay English in the database; only their labels are translated.
export const translatedOptions = (values) => values.map((value) => ({ label: __(value), value }));

window.__ = __;
