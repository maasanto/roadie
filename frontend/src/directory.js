import { translatedOptions } from "./translation.js";

// The four types behind the sidebar's Directory heading, in the order it shows them. Each one is its own
// screen: `route` is the screen's route, `columns` the list it opens with. A column's label is the DocType's
// own word, translated where the list renders it — never a translation captured in a saved layout.
export const directoryTypes = [
	{
		doctype: "Festival",
		plural: __("Festivals"),
		icon: "lucide-tent",
		route: { name: "Festivals", path: "/directory/festivals" },
		columns: [
			{ fieldname: "title", label: "Name" },
			{ fieldname: "relevance", label: "Relevance", format: "rating" },
			{ fieldname: "city", label: "City" },
			{ fieldname: "usual_month", label: "Usual month", format: "label" },
		],
	},
	{
		doctype: "Venue",
		plural: __("Venues"),
		icon: "lucide-building-2",
		route: { name: "Venues", path: "/directory/venues" },
		columns: [
			{ fieldname: "title", label: "Name" },
			{ fieldname: "relevance", label: "Relevance", format: "rating" },
			{ fieldname: "city", label: "City" },
			{ fieldname: "capacity", label: "Capacity", format: "number" },
		],
	},
	{
		doctype: "Promoter",
		plural: __("Promoters"),
		icon: "lucide-handshake",
		route: { name: "Promoters", path: "/directory/promoters" },
		columns: [
			{ fieldname: "title", label: "Name" },
			{ fieldname: "relevance", label: "Relevance", format: "rating" },
			{ fieldname: "city", label: "City" },
		],
	},
	{
		doctype: "Band",
		plural: __("Bands"),
		icon: "lucide-guitar",
		route: { name: "Bands", path: "/directory/bands" },
		columns: [
			{ fieldname: "title", label: "Name" },
			{ fieldname: "relevance", label: "Relevance", format: "rating" },
			{ fieldname: "city", label: "City" },
			{ fieldname: "genre", label: "Genre", format: "list" },
		],
	},
];

export const directoryType = (doctype) => directoryTypes.find((type) => type.doctype === doctype);

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

// A Rating field stores the fraction of the stars lit, 0.6 for three of five, so the SPA counts stars and the
// database keeps the fraction Desk reads.
export const RATING_STARS = 5;

export const toStars = (fraction) => Math.round((Number(fraction) || 0) * RATING_STARS);

export const toFraction = (stars) => (Number(stars) || 0) / RATING_STARS;
