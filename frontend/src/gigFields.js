import { computed } from "vue";
import { useCall, useList } from "frappe-ui";
import { gigFields } from "./gig";

// The gig panel's form, with the festivals, venues, promoters and members its pickers offer.
export function useGigFields() {
	const linkLists = Object.fromEntries(
		["Festival", "Venue", "Promoter"].map((doctype) => [
			doctype,
			useList({ doctype, fields: ["name", "title"], orderBy: "title asc", limit: 500 }),
		])
	);
	const members = useCall({ url: "/api/v2/method/roadie.api.get_members" });
	const fields = computed(() =>
		gigFields({
			festivals: linkLists.Festival.data,
			venues: linkLists.Venue.data,
			promoters: linkLists.Promoter.data,
			members: members.data,
		})
	);
	return { linkLists, members, fields };
}
