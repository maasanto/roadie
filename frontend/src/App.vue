<script setup>
import { FrappeUIProvider, Sidebar, SidebarHeader, SidebarItem } from "frappe-ui";

const currentUser = window.user;
const accountMenu = [{ label: "Log out", icon: "lucide-log-out", onClick: () => (window.location.href = "/?cmd=web_logout") }];
</script>

<template>
	<FrappeUIProvider>
		<div class="flex h-screen bg-surface-base text-ink-gray-8">
			<Sidebar disable-collapse>
				<SidebarHeader title="Band CRM" :subtitle="currentUser" :menu-items="accountMenu" />
				<SidebarItem label="Pipeline" icon="lucide-kanban" to="/" />
				<SidebarItem label="Directory" icon="lucide-book-user" to="/directory" />
			</Sidebar>
			<main class="min-w-0 flex-1 overflow-auto">
				<router-view />
			</main>
		</div>
	</FrappeUIProvider>
</template>
