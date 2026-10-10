import { translatedOptions } from "./translation.js";

export const directoryTypes = [
	{ doctype: "Festival", plural: __("Festivals") },
	{ doctype: "Venue", plural: __("Venues") },
	{ doctype: "Promoter", plural: __("Promoters") },
	{ doctype: "Band", plural: __("Bands") },
];

// A band's genres: values stay English in the database, only their labels are translated.
const GENRES = [
	"Alternative",
	"Blues",
	"Chanson",
	"Classical",
	"Country",
	"Disco",
	"Electronic",
	"Folk",
	"Funk",
	"Gospel",
	"Hardcore",
	"Hip Hop",
	"Indie",
	"Jazz",
	"Latin",
	"Metal",
	"Pop",
	"Punk",
	"Rap",
	"Reggae",
	"Rock",
	"Ska",
	"Soul",
	"Techno",
	"World",
];

// The fields a DocType's meta cannot describe on its own, keyed by doctype then fieldname. Genre is free text
// in the DocType, so the catalogue and the multiselect come from here.
export const directoryControls = {
	Band: { genre: { type: "multiselect", options: translatedOptions(GENRES) } },
};

// A multiselect lives as an array in the SPA and as one comma-separated string in the database.
export const splitList = (value) =>
	(value || "")
		.split(",")
		.map((item) => item.trim())
		.filter(Boolean);

export const joinList = (values) => (values || []).join(", ");
