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
		// The directory's own address, from old bookmarks and the mention notifications, opens on its first type.
		{ path: "/directory", redirect: directoryTypes[0].route.path },
		{
			path: "/inbox",
			name: "Inbox",
			component: () => import("./pages/MailboxScreen.vue"),
			props: { sentOrReceived: "Received" },
		},
		{
			path: "/outbox",
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
