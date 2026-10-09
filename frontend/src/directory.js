const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

const headFields = [
	{ fieldname: "title", label: "Name", type: "text", required: true },
	{ fieldname: "city", label: "City", type: "text" },
	{ fieldname: "website", label: "Website", type: "url" },
	{ fieldname: "instagram", label: "Instagram", type: "text" },
];
const notesField = { fieldname: "notes", label: "Notes", type: "textarea" };

const withCommonFields = (extraFields) => [...headFields, ...extraFields, notesField];

export const directoryTypes = [
	{
		doctype: "Festival",
		plural: "Festivals",
		fields: withCommonFields([
			{ fieldname: "usual_month", label: "Usual month", type: "select", options: MONTHS },
			{ fieldname: "application_url", label: "Application URL", type: "url" },
			{ fieldname: "application_opens", label: "Usual application opens", type: "date" },
			{ fieldname: "application_closes", label: "Usual application closes", type: "date" },
		]),
	},
	{
		doctype: "Venue",
		plural: "Venues",
		fields: withCommonFields([
			{ fieldname: "capacity", label: "Capacity", type: "number" },
			{ fieldname: "address", label: "Address", type: "textarea" },
		]),
	},
	{ doctype: "Promoter", plural: "Promoters", fields: withCommonFields([]) },
	{ doctype: "Band", plural: "Bands", fields: withCommonFields([{ fieldname: "genre", label: "Genre", type: "text" }]) },
];
