// Drive lets only an item's owner, or whoever it was shared with, share it; a public item already has its link.
const PUBLIC_SHARE_COUNT = -2;

export const canLink = (item) => Boolean(item?.share || item?.share_count === PUBLIC_SHARE_COUNT);

// The Site and Home entries the dialog starts from carry no share rights, so they never fall through here; the server refuses them too.
export const linkTarget = (selectedItem, currentFolder) =>
	selectedItem ?? (canLink(currentFolder) ? currentFolder : null);
