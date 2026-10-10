import { computed } from "vue";
import { useCall, useList } from "frappe-ui";
import { gigControls } from "./gig";

// The gig panel's pickers, with the festivals, venues, promoters and members they offer.
export function useGigControls() {
	const linkLists = Object.fromEntries(
		["Festival", "Venue", "Promoter"].map((doctype) => [
			doctype,
			useList({ doctype, fields: ["name", "title"], orderBy: "title asc", limit: 500 }),
		])
	);
	const members = useCall({ url: "/api/v2/method/roadie.api.get_members" });
	const controls = computed(() =>
		gigControls({
			festivals: linkLists.Festival.data,
			venues: linkLists.Venue.data,
			promoters: linkLists.Promoter.data,
			members: members.data,
		})
	);
	return { linkLists, members, controls };
}
