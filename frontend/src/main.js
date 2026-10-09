import { __ } from "./translation";
import { createApp } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import App from "./App.vue";
import "./style.css";

const router = createRouter({
	history: createWebHistory("/band"),
	routes: [
		{ path: "/", name: "Pipeline", component: () => import("./pages/PipelineScreen.vue") },
		{ path: "/planning", name: "Planning", component: () => import("./pages/PlanningScreen.vue") },
		{ path: "/tasks", name: "MyTasks", component: () => import("./pages/MyTasksScreen.vue") },
		{ path: "/directory", name: "Directory", component: () => import("./pages/DirectoryScreen.vue") },
		{ path: "/inbox", name: "Inbox", component: () => import("./pages/MailboxScreen.vue"), props: { sentOrReceived: "Received" } },
		{ path: "/outbox", name: "Outbox", component: () => import("./pages/MailboxScreen.vue"), props: { sentOrReceived: "Sent" } },
	],
});

document.documentElement.lang = window.lang;

const app = createApp(App).use(router);
app.config.globalProperties.__ = __;
app.mount("#app");
