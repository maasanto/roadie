<script setup>
defineProps({
	item: { type: Object, required: true },
	active: { type: Boolean, default: false },
});

const ICONS = {
	Gig: "lucide-music",
	Festival: "lucide-tent",
	Venue: "lucide-map-pin",
	Promoter: "lucide-megaphone",
	Band: "lucide-users",
	"Band Task": "lucide-list-checks",
};
</script>

<template>
	<div
		class="flex w-full min-w-0 items-center rounded px-2 py-2 text-base-medium text-ink-gray-8"
		:class="active ? 'bg-surface-gray-2' : ''"
	>
		<span class="mr-3 size-4 shrink-0 text-ink-gray-7" :class="ICONS[item.doctype]" aria-hidden="true" />
		<span class="overflow-hidden text-ellipsis whitespace-nowrap">{{ item.title }}</span>
		<span v-if="item.city" class="ml-auto truncate pl-2 text-sm text-ink-gray-5">{{ item.city }}</span>
	</div>
</template>
