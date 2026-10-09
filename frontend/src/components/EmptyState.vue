<script setup>
defineProps({
	icon: { type: String, required: true },
	title: { type: String, required: true },
	description: { type: String, default: "" },
});
</script>

<template>
	<div class="flex flex-col items-center rounded-6 border border-dashed border-outline-gray-2 px-6 py-12 text-center">
		<span class="size-6 text-ink-gray-5" :class="icon" aria-hidden="true" />
		<p class="mt-3 text-base-medium text-ink-gray-8">{{ title }}</p>
		<p v-if="description" class="mt-1 max-w-sm text-p-sm text-ink-gray-5">{{ description }}</p>
		<div v-if="$slots.default" class="mt-4"><slot /></div>
	</div>
</template>
