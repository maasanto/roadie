import { translatedOptions } from "./translation.js";

const MONTHS = [
	"January",
	"February",
	"March",
	"April",
	"May",
	"June",
	"July",
	"August",
	"September",
	"October",
	"November",
	"December",
];

// A band's genres; values stay English in the database, only their labels are translated.
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

// A multiselect lives as an array in the SPA and as one comma-separated string in the database.
export const splitList = (value) =>
	(value || "")
		.split(",")
		.map((item) => item.trim())
		.filter(Boolean);

export const joinList = (values) => (values || []).join(", ");

const headFields = [
	{ fieldname: "title", label: __("Name"), type: "text", required: true },
	{ fieldname: "city", label: __("City"), type: "text" },
	{ fieldname: "website", label: __("Website"), type: "url" },
	{ fieldname: "instagram", label: __("Instagram"), type: "text" },
];
const notesField = { fieldname: "notes", label: __("Notes"), type: "textarea" };

const withCommonFields = (extraFields) => [...headFields, ...extraFields, notesField];

export const directoryTypes = [
	{
		doctype: "Festival",
		plural: __("Festivals"),
		fields: withCommonFields([
			{
				fieldname: "usual_month",
				label: __("Usual month"),
				type: "select",
				options: translatedOptions(MONTHS),
			},
			{ fieldname: "application_url", label: __("Application URL"), type: "url" },
			{ fieldname: "application_opens", label: __("Usual application opens"), type: "date" },
			{ fieldname: "application_closes", label: __("Usual application closes"), type: "date" },
		]),
	},
	{
		doctype: "Venue",
		plural: __("Venues"),
		fields: withCommonFields([
			{ fieldname: "capacity", label: __("Capacity"), type: "number" },
			{ fieldname: "address", label: __("Address"), type: "textarea" },
		]),
	},
	{ doctype: "Promoter", plural: __("Promoters"), fields: withCommonFields([]) },
	{
		doctype: "Band",
		plural: __("Bands"),
		fields: withCommonFields([
			{
				fieldname: "genre",
				label: __("Genre"),
				type: "multiselect",
				options: translatedOptions(GENRES),
			},
		]),
	},
];
