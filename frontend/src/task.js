export const TASK_FIELDS = ["name", "title", "done", "assignee", "gig", "start_date", "due_date"];

// frappe-ui's Checkbox emits update:modelValue twice per click, so a repeat of the current value is ignored.
export async function setDone(tasks, task, isDone) {
	const done = isDone ? 1 : 0;
	if (task.done === done) return;
	task.done = done;
	await tasks.setValue.submit({ name: task.name, done });
	if (tasks.setValue.error) task.done = done ? 0 : 1;
}

export const byDueDate = (a, b) => (a.due_date || "9999").localeCompare(b.due_date || "9999");
