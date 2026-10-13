import vue from "@vitejs/plugin-vue";
import frappeui from "frappe-ui/vite";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

// frappe-ui's calendar hardcodes English labels and a Sunday-first row (still so in 1.0.1), and has no prop for either.
const calendarPanelPatches = [
	[
		"import { months } from './utils'",
		"import { monthNames as months, weekdayInitials } from '/src/calendarLocale.js'",
	],
	["const WEEKDAYS = ['S', 'M', 'T', 'W', 'T', 'F', 'S']", "const WEEKDAYS = weekdayInitials"],
	// Home and End go to the ends of the row, which now starts on the site's first day of the week.
	["cell.date.subtract(cell.date.day(), 'day')", "cell.date.startOf('week')"],
	["cell.date.add(6 - cell.date.day(), 'day')", "cell.date.startOf('week').add(6, 'day')"],
];

// Warning: main.js moves the week's first day for the whole grid, so an unpatched panel heads every column wrong.
let isCalendarPanelPatched = false;
const localizedCalendarPanel = {
	name: "roadie-localized-calendar-panel",
	apply: "build",
	enforce: "pre",
	transform(code, id) {
		if (!id.endsWith("/frappe-ui/src/components/DatePicker/CalendarPanel.vue")) return;
		isCalendarPanelPatched = true;
		return calendarPanelPatches.reduce((patched, [original, replacement]) => {
			if (!patched.includes(original)) {
				throw new Error(
					`frappe-ui's CalendarPanel.vue no longer contains "${original}": update the patch in vite.config.js`
				);
			}
			return patched.replace(original, replacement);
		}, code);
	},
	buildEnd() {
		if (!isCalendarPanelPatched) {
			throw new Error(
				"frappe-ui's CalendarPanel.vue was not found to patch: update the patch in vite.config.js"
			);
		}
	},
};

export default defineConfig({
	plugins: [
		localizedCalendarPanel,
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
