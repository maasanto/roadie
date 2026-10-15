<script setup>
import {
	Badge,
	Button,
	Dropdown,
	FrappeUIProvider,
	KeyboardShortcut,
	ScrollArea,
	Sidebar,
	SidebarHeader,
	SidebarItem,
	SidebarLabel,
	useCall,
} from "frappe-ui";
import { computed, onMounted, provide, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import AvailabilityStrip from "./components/AvailabilityStrip.vue";
import NotificationPanel from "./components/NotificationPanel.vue";
import SearchPalette from "./components/SearchPalette.vue";
import { directoryTypes } from "./directory";
import { onShortcut } from "./keyboard";
import { unreadCount } from "./notifications";
import { disablePush, isPushAvailable, isPushEnabled } from "./push";
import { resultRoute } from "./search";
import { user } from "./user";

const route = useRoute();
const router = useRouter();
const showNotifications = ref(false);
const notifications = useCall({ url: "/api/v2/method/roadie.api.get_notifications" });
const unread = computed(() => unreadCount(notifications.data || []));

// Read on the first screen and on every move to another, so a request that arrived meanwhile shows. A filter, a sort
// or an opened record only changes the query, and the gig panel reads it again itself after an answer.
const pendingAvailability = useCall({
	url: "/api/v2/method/roadie.api.get_pending_availability",
	immediate: false,
});
router.afterEach((to, from) => {
	if (to.path !== from.path || !from.matched.length) pendingAvailability.reload();
});
provide("pendingAvailability", pendingAvailability);

// An open Dialog treats any pointerdown or focus elsewhere as "outside" and closes, so Undo on a toast would close it too.
onMounted(() => {
	const toaster = document.querySelector('section[aria-label^="Notifications"]');
	for (const eventType of ["pointerdown", "focusin"])
		toaster.addEventListener(eventType, (event) => event.stopPropagation());
});
const logoUrl = "/assets/roadie/logo.svg";
const driveUrl = window.drive_url;
const openDrive = () => window.open(driveUrl, "_blank", "noopener");
const logOut = {
	label: __("Log out"),
	icon: "lucide-log-out",
	onClick: async () => {
		// The browser's push subscription outlives the session: left on, the next person on this device gets the member's notifications.
		if (isPushAvailable() && isPushEnabled()) {
			await disablePush().catch((error) => console.error("Could not turn push off on logout", error));
		}
		window.location.href = "/?cmd=web_logout";
	},
};
const settings = {
	label: __("Settings"),
	icon: "lucide-settings",
	onClick: () => router.push("/settings"),
};
const accountMenu = [settings, logOut];

// Each directory type is its own screen, listed under the sidebar's Directory heading.
const directoryScreens = directoryTypes.map((type) => ({
	name: type.route.name,
	label: type.plural,
	icon: type.icon,
	to: type.route.path,
}));

const screens = [
	{ name: "Pipeline", label: __("Gigs"), shortLabel: __("Gigs"), icon: "lucide-kanban", to: "/" },
	{
		name: "Planning",
		label: __("Planning"),
		shortLabel: __("Planning"),
		icon: "lucide-chart-gantt",
		to: "/planning",
	},
	{
		name: "MyTasks",
		label: __("My tasks"),
		shortLabel: __("Tasks"),
		icon: "lucide-list-checks",
		to: "/tasks",
	},
];

const mailboxScreens = [
	{ name: "Inbox", label: __("Inbox"), shortLabel: __("Received"), icon: "lucide-inbox", to: "/inbox" },
	{ name: "Outbox", label: __("Outbox"), shortLabel: __("Outgoing"), icon: "lucide-send", to: "/outbox" },
];

// The phone menu carries the four types, then the screens the bar along the bottom has no room for.
const phoneMenu = [
	...directoryScreens.map(({ label, icon, to }) => ({ label, icon, route: to })),
	...(driveUrl ? [{ label: __("Drive"), icon: "lucide-hard-drive", onClick: openDrive }] : []),
	settings,
	logOut,
];

const searchPalette = ref(null);
onShortcut({ key: "k", ctrl: true }, () => searchPalette.value.open());

// A result on the screen already open keeps that screen's own query, such as the pipeline's list view.
function openResult(item) {
	const target = resultRoute(item);
	const current = router.currentRoute.value;
	router.push(
		target.name === current.name ? { ...target, query: { ...current.query, ...target.query } } : target
	);
}
</script>

<template>
	<FrappeUIProvider>
		<div class="flex h-screen flex-col bg-surface-base text-ink-gray-8 md:flex-row">
			<!-- frappe-ui casts SidebarItem's absent `active` prop to false, so route matching is passed explicitly. -->
			<div class="hidden md:flex">
				<Sidebar disable-collapse>
					<SidebarHeader
						title="Roadie"
						:logo="logoUrl"
						:subtitle="user.fullName"
						:menu-items="accountMenu"
					/>
					<!-- Composition mode leaves the gutter and scrolling to the app; SidebarHeader owns its own. -->
					<ScrollArea class="min-h-0 flex-1" viewport-class="px-2 pt-0.5 pb-2">
						<nav class="flex flex-col gap-0.5">
							<SidebarItem
								:label="__('Search')"
								icon="lucide-search"
								@click="searchPalette.open()"
							>
								<template #suffix><KeyboardShortcut class="mr-2" combo="Mod+K" /></template>
							</SidebarItem>
							<SidebarItem
								:label="__('Notifications')"
								icon="lucide-bell"
								:active="showNotifications"
								@click="showNotifications = true"
							>
								<template v-if="unread" #suffix>
									<Badge class="mr-2" :label="String(unread)" theme="gray" />
								</template>
							</SidebarItem>
							<SidebarItem
								v-for="screen in screens"
								:key="screen.name"
								:label="screen.label"
								:icon="screen.icon"
								:to="screen.to"
								:active="route.name === screen.name"
							/>
							<SidebarLabel class="mt-2">{{ __("Directory") }}</SidebarLabel>
							<SidebarItem
								v-for="screen in directoryScreens"
								:key="screen.name"
								:label="screen.label"
								:icon="screen.icon"
								:to="screen.to"
								:active="route.name === screen.name"
							/>
							<SidebarLabel class="mt-2">{{ __("Mail") }}</SidebarLabel>
							<SidebarItem
								v-for="screen in mailboxScreens"
								:key="screen.name"
								:label="screen.label"
								:icon="screen.icon"
								:to="screen.to"
								:active="route.name === screen.name"
							/>
							<SidebarItem
								v-if="driveUrl"
								:label="__('Drive')"
								icon="lucide-hard-drive"
								@click="openDrive"
							>
								<template #suffix
									><span
										class="lucide-external-link mr-2 size-3.5 text-ink-gray-4"
										aria-hidden="true"
								/></template>
							</SidebarItem>
						</nav>
					</ScrollArea>
				</Sidebar>
			</div>
			<header class="flex items-center gap-2 border-b px-4 py-2 md:hidden">
				<img :src="logoUrl" alt="" class="size-7" />
				<span class="flex-1 text-base-semibold">Roadie</span>
				<Button
					variant="ghost"
					icon="lucide-search"
					:label="__('Search')"
					@click="searchPalette.open()"
				/>
				<Button
					icon="lucide-bell"
					variant="ghost"
					:label="__('Notifications')"
					@click="showNotifications = true"
				>
					<template v-if="unread" #suffix>
						<Badge :label="String(unread)" theme="gray" />
					</template>
				</Button>
				<Dropdown
					:options="phoneMenu"
					align="end"
					:button="{ icon: 'lucide-menu', variant: 'ghost', label: __('Menu') }"
				/>
			</header>
			<div class="flex min-h-0 min-w-0 flex-1 flex-col">
				<AvailabilityStrip :pending="pendingAvailability" />
				<main class="min-h-0 flex-1 overflow-auto">
					<!-- Keyed so the four directory screens, which share one component, remount on a type change. -->
					<router-view :key="route.name" />
				</main>
			</div>
			<nav class="flex border-t bg-surface-base md:hidden" :aria-label="__('Screens')">
				<router-link
					v-for="screen in [...screens, ...mailboxScreens]"
					:key="screen.name"
					:to="screen.to"
					class="flex min-w-0 flex-1 flex-col items-center gap-0.5 py-2 text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-outline-gray-3"
					:class="route.name === screen.name ? 'text-ink-gray-9' : 'text-ink-gray-5'"
					:aria-current="route.name === screen.name ? 'page' : undefined"
				>
					<span class="size-5" :class="screen.icon" aria-hidden="true" />
					<span class="max-w-full truncate">{{ screen.shortLabel }}</span>
				</router-link>
			</nav>
			<SearchPalette ref="searchPalette" @select="openResult" />
		</div>
		<NotificationPanel v-model:open="showNotifications" :notifications="notifications" />
	</FrappeUIProvider>
</template>
