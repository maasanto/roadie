import { createApp } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import App from "./App.vue";
import "./style.css";

const router = createRouter({
	history: createWebHistory("/band"),
	routes: [{ path: "/", name: "Pipeline", component: () => import("./pages/PipelineScreen.vue") }],
});

createApp(App).use(router).mount("#app");
