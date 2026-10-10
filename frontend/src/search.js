import { __ } from "./translation.js";

export const RESULTS_PER_GROUP = 5;

// Palette group titles, keyed by DocType. Read as literals so the translation catalogue picks them up.
const GROUP_TITLES = {
	Gig: __("Gigs"),
	Festival: __("Festivals"),
	Venue: __("Venues"),
	Promoter: __("Promoters"),
	Band: __("Bands"),
	"Band Task": __("Tasks"),
};

const GROUP_ORDER = Object.keys(GROUP_TITLES);

// Shapes the endpoint's grouped matches into CommandPalette groups: translated titles in a stable order,
// at most `limit` items each, empty groups dropped. An empty query yields nothing, even with stale results.
export function searchGroups(query, groupedResults, limit = RESULTS_PER_GROUP) {
	if (!query.trim()) return [];
	return GROUP_ORDER.reduce((groups, doctype) => {
		const group = (groupedResults || []).find((entry) => entry.doctype === doctype);
		const items = (group?.results || []).slice(0, limit).map((result) => ({ ...result, doctype }));
		if (items.length) groups.push({ doctype, title: GROUP_TITLES[doctype], items });
		return groups;
	}, []);
}

// Where a result takes the user: a gig opens its panel on the Pipeline, a task the tasks screen, and every
// directory record its entry dialog on the Directory. The screens read the record back from the query.
export function resultRoute({ doctype, name }) {
	if (doctype === "Gig") return { name: "Pipeline", query: { gig: name } };
	if (doctype === "Band Task") return { name: "MyTasks" };
	return { name: "Directory", query: { entry: `${doctype}:${name}` } };
}
