import vue from "@vitejs/plugin-vue";
import frappeui from "frappe-ui/vite";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

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
		VitePWA({
			strategies: "injectManifest",
			srcDir: "src",
			filename: "sw.js",
			// Registered in main.js at /roadie/sw.js, which roadie/page_renderers.py serves
			injectRegister: false,
			// Static in roadie/public/pwa: a generated one joins the precache unprefixed and resolves to the SPA route
			manifest: false,
			// An oversized chunk is left out of the precache instead of failing bench build
			showMaximumFileSizeToCacheInBytesWarning: true,
			injectManifest: {
				// The page is rendered per request with boot data, so only the built assets are precached
				globPatterns: ["**/*.{js,css}"],
				// The worker lives at /roadie/ while the build is served from /assets/roadie/frontend/
				modifyURLPrefix: { "": "/assets/roadie/frontend/" },
				// A sourcemap URL next to /roadie/sw.js would resolve to the SPA route
				sourcemap: false,
			},
		}),
	],
});
