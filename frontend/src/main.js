import { __ } from "./translation";
import { createApp } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import App from "./App.vue";
import { directoryTypes } from "./directory";
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

document.documentElement.lang = window.lang;

const app = createApp(App).use(router);
app.config.globalProperties.__ = __;
app.mount("#app");

if ("serviceWorker" in navigator && import.meta.env.PROD) {
	// After load, so precaching every chunk doesn't compete with the first screen for bandwidth
	window.addEventListener("load", () =>
		navigator.serviceWorker.register("/roadie/sw.js", { scope: "/roadie" })
	);
}
