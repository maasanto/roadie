<script setup>
import { FrappeUIProvider, Sidebar, SidebarHeader, SidebarItem } from "frappe-ui";

const currentUser = window.user;
const driveUrl = window.drive_url;
const openDrive = () => window.open(driveUrl, "_blank", "noopener");
const accountMenu = [{ label: __("Log out"), icon: "lucide-log-out", onClick: () => (window.location.href = "/?cmd=web_logout") }];
</script>

<template>
	<FrappeUIProvider>
		<div class="flex h-screen bg-surface-base text-ink-gray-8">
			<Sidebar disable-collapse>
				<SidebarHeader title="Band CRM" logo="/assets/band_crm/logo.svg" :subtitle="currentUser" :menu-items="accountMenu" />
				<SidebarItem :label="__('Pipeline')" icon="lucide-kanban" to="/" />
				<SidebarItem :label="__('Planning')" icon="lucide-chart-gantt" to="/planning" />
				<SidebarItem :label="__('My tasks')" icon="lucide-list-checks" to="/tasks" />
				<SidebarItem :label="__('Directory')" icon="lucide-book-user" to="/directory" />
				<SidebarItem :label="__('Inbox')" icon="lucide-inbox" to="/inbox" />
				<SidebarItem :label="__('Outbox')" icon="lucide-send" to="/outbox" />
				<SidebarItem v-if="driveUrl" :label="__('Drive')" icon="lucide-hard-drive" @click="openDrive">
					<template #suffix><span class="lucide-external-link mr-2 size-3.5 text-ink-gray-4" aria-hidden="true" /></template>
				</SidebarItem>
			</Sidebar>
			<main class="min-w-0 flex-1 overflow-auto">
				<router-view />
			</main>
		</div>
	</FrappeUIProvider>
</template>
