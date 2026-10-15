import { ref } from "vue";
import { call, toast } from "frappe-ui";
import { toastWithUndo } from "./undo";

export const TASK_FIELDS = ["name", "title", "done", "assignee", "gig", "start_date", "due_date"];

// frappe-ui's Checkbox emits update:modelValue twice per click, so a repeat of the current value is ignored.
// One request per tick, and no refetch: useList.setValue is shared, so a second tick would abort the first.
export async function setDone(tasks, task, isDone) {
	const done = isDone ? 1 : 0;
	if (task.done === done) return;
	tasks.updateRow({ name: task.name, done });
	try {
		await call("frappe.client.set_value", {
			doctype: "Band Task",
			name: task.name,
			fieldname: "done",
			value: done,
		});
	} catch (error) {
		tasks.updateRow({ name: task.name, done: done ? 0 : 1 });
		toast.error(error.messages?.join("\n") || error.message);
	}
}

// Module scope: the delete lands once its toast closes, by which time the dialog and the list it was opened from
// may be gone. Every task list hides these, and a task stays hidden once deleted, its name never comes back.
const deletedTasks = ref(new Set());

export const isShownTask = (task) => !deletedTasks.value.has(task.name);

export function deleteTask(name) {
	deletedTasks.value.add(name);
	toastWithUndo(__("Task deleted"), {
		undo: () => deletedTasks.value.delete(name),
		commit: () => deleteForGood(name),
	});
}

async function deleteForGood(name) {
	try {
		await call("frappe.client.delete", { doctype: "Band Task", name });
	} catch (error) {
		deletedTasks.value.delete(name);
		toast.error(error.messages?.join("\n") || error.message);
	}
}

export const byDueDate = (a, b) => (a.due_date || "9999").localeCompare(b.due_date || "9999");
