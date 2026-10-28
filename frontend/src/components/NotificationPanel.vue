<script setup>
import { watch } from "vue";
import { Avatar, Button, ErrorMessage, useCall } from "frappe-ui";
import { useRouter } from "vue-router";
import EmptyState from "./EmptyState.vue";
import ListSkeleton from "./ListSkeleton.vue";
import { notificationRoute, relativeDate } from "../notifications";

const props = defineProps({
	notifications: { type: Object, required: true },
});
const open = defineModel("open", { type: Boolean, default: false });
const router = useRouter();

const markRead = useCall({
	url: "/api/v2/method/roadie.api.mark_notifications_read",
	method: "POST",
	immediate: false,
	onSuccess: () => props.notifications.reload(),
});

// The list is stale as soon as it closes: assignments and deadlines keep landing.
watch(open, (isOpen) => isOpen && props.notifications.reload());

function openNotification(notification) {
	if (!notification.read) markRead.submit({ names: [notification.name] });
	// Suite's documents open in their own app, in a new tab as the sidebar's Drive link does.
	if (notification.url) {
		window.open(notification.url, "_blank", "noopener");
	} else {
		const route = notificationRoute(notification);
		if (route) router.push(route);
	}
	open.value = false;
}
</script>

<template>
	<Teleport to="body">
		<div v-if="open" class="fixed inset-0 z-40 bg-black/25 md:left-60" @click="open = false" />
		<aside
			v-if="open"
			class="fixed inset-y-0 left-0 z-50 flex w-80 max-w-full flex-col border-r bg-surface-base shadow-xl md:left-60"
			role="dialog"
			:aria-label="__('Notifications')"
		>
			<header class="flex min-h-12 items-center gap-1 border-b px-4">
				<h2 class="flex-1 text-lg-semibold">{{ __("Notifications") }}</h2>
				<Button
					v-if="notifications.data?.some((notification) => !notification.read)"
					variant="ghost"
					:label="__('Mark all as read')"
					@click="markRead.submit({})"
				/>
				<Button icon="lucide-x" variant="ghost" :label="__('Close')" @click="open = false" />
			</header>
			<ListSkeleton v-if="notifications.loading && !notifications.data" class="p-4" />
			<ErrorMessage v-else-if="notifications.error" class="m-4" :message="notifications.error" />
			<EmptyState
				v-else-if="!notifications.data?.length"
				class="m-4"
				icon="lucide-bell"
				:title="__('No notifications yet')"
				:description="__('Task assignments, deadlines and mentions show up here.')"
			/>
			<ul v-else class="flex-1 space-y-0.5 overflow-y-auto p-2">
				<li v-for="notification in notifications.data" :key="notification.name">
					<button
						class="flex w-full items-start gap-2 rounded-6 px-2 py-2.5 text-left hover:bg-surface-gray-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-outline-gray-3"
						@click="openNotification(notification)"
					>
						<span
							class="mt-3.5 size-2 shrink-0 rounded-full"
							:class="notification.read ? 'bg-transparent' : 'bg-surface-blue-7'"
							:aria-label="notification.read ? undefined : __('Unread')"
						/>
						<Avatar
							:image="notification.from_user_image"
							:label="notification.from_user_name || notification.from_user"
							class="size-9"
							aria-hidden="true"
						/>
						<span class="min-w-0 flex-1 pl-0.5">
							<!-- Sanitised by get_notifications down to its bold tags. -->
							<span
								class="line-clamp-3 text-base"
								:class="notification.read ? 'text-ink-gray-7' : 'text-ink-gray-9'"
								v-html="notification.title"
							/>
							<span
								v-if="notification.description"
								class="mt-0.5 line-clamp-2 text-p-sm text-ink-gray-6"
							>
								{{ notification.description }}
							</span>
							<span class="mt-0.5 block text-xs text-ink-gray-5">{{
								relativeDate(notification.creation)
							}}</span>
						</span>
					</button>
				</li>
			</ul>
		</aside>
	</Teleport>
</template>
