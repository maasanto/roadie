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
	],
});

createApp(App).use(router).mount("#app");
