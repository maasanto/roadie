// Whose tasks My tasks lists: Mine stays the default, the other scopes are asked for through the address.
export const TASK_SCOPES = {
	mine: {
		label: __("Mine"),
		filters: (user) => ({ assignee: user }),
		emptyTitle: __("Nothing assigned to you"),
		emptyDescription: __(
			"Open a gig and add a task to its checklist. Whatever is assigned to you shows up here, overdue first."
		),
	},
	unassigned: {
		label: __("Unassigned"),
		filters: () => ({ assignee: ["is", "not set"] }),
		emptyTitle: __("No unassigned tasks"),
		emptyDescription: __("Every task has someone on it."),
	},
	everyone: {
		label: __("Everyone"),
		filters: () => ({}),
		emptyTitle: __("No tasks yet"),
		emptyDescription: __("Open a gig and add a task to its checklist."),
	},
};

export const scopeFromQuery = (show) => (Object.keys(TASK_SCOPES).includes(show) ? show : "mine");

// A member who left is no longer listed, so their tasks fall back to the bare user ID rather than look unassigned.
export function assigneeAvatar(task, membersByName) {
	if (!task.assignee || !membersByName) return null;
	return membersByName[task.assignee] || { full_name: task.assignee };
}
