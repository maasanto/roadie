import vue from "@vitejs/plugin-vue";
import frappeui from "frappe-ui/vite";
import { defineConfig } from "vite";

export default defineConfig({
	plugins: [
		frappeui({
			frontendRoute: "/band",
			buildConfig: {
				outDir: "../band_crm/public/frontend",
				indexHtmlPath: "../band_crm/www/band.html",
			},
		}),
		vue(),
	],
});
