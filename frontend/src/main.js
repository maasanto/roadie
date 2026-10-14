import { __ } from "./translation";
import { dayjs } from "frappe-ui";
import { createApp } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import App from "./App.vue";
import { directoryTypes } from "./directory";
import { confirmDiscardDraft, hasEditedDraft } from "./draft";
import { keepListQueries } from "./listQuery";
import { refreshPushToken } from "./push";
import "./style.css";

const router = createRouter({
	history: createWebHistory("/roadie"),
	routes: [
		{ path: "/", name: "Pipeline", component: () => import("./pages/PipelineScreen.vue") },
		{ path: "/planning", name: "Planning", component: () => import("./pages/PlanningScreen.vue") },
		{ path: "/tasks", name: "MyTasks", component: () => import("./pages/MyTasksScreen.vue") },
		...directoryTypes.map((type) => ({
			path: type.route.path,
			name: type.route.name,
			component: () => import("./pages/DirectoryScreen.vue"),
			props: { doctype: type.doctype },
		})),
		// The directory's own address, from old bookmarks and older mention notifications, opens on its first type.
		{ path: "/directory", redirect: directoryTypes[0].route.path },
		// The open thread is the record it belongs to, so a refresh or a shared link reopens it.
		{
			path: "/inbox/:doctype?/:name?",
			name: "Inbox",
			component: () => import("./pages/MailboxScreen.vue"),
			props: { sentOrReceived: "Received" },
		},
		{
			path: "/outbox/:doctype?/:name?",
			name: "Outbox",
			component: () => import("./pages/MailboxScreen.vue"),
			props: { sentOrReceived: "Sent" },
		},
		{ path: "/settings", name: "Settings", component: () => import("./pages/SettingsScreen.vue") },
	],
});
keepListQueries(router);

// Another screen, or another mailbox thread, unmounts the composer. A query change is the screen's own business:
// useOpenRecord asks before ?gig= or ?entry= switches the open record.
router.beforeEach((to, from) => to.path === from.path || confirmDiscardDraft());
window.addEventListener("beforeunload", (event) => {
	if (!hasEditedDraft()) return;
	event.preventDefault();
	// Chromium before 119, still in some Android WebViews, only warns when returnValue is set.
	event.returnValue = true;
});

document.documentElement.lang = window.lang;
// frappe-ui's date pickers lay out their weeks from dayjs's locale.
dayjs.updateLocale(dayjs.locale(), { weekStart: window.week_start });

const app = createApp(App).use(router);
app.config.globalProperties.__ = __;
app.mount("#app");

if ("serviceWorker" in navigator && import.meta.env.PROD) {
	// After load, so precaching every chunk doesn't compete with the first screen for bandwidth
	window.addEventListener("load", () => {
		navigator.serviceWorker.register("/roadie/sw.js", { scope: "/roadie" });
		refreshPushToken();
	});
}
