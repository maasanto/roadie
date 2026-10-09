import vue from "@vitejs/plugin-vue";
import frappeui from "frappe-ui/vite";
import { defineConfig } from "vite";

export default defineConfig({
	plugins: [
		frappeui({
			frontendRoute: "/roadie",
			buildConfig: {
				outDir: "../roadie/public/frontend",
				indexHtmlPath: "../roadie/www/roadie.html",
			},
		}),
		vue(),
	],
});
