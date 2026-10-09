<script setup>
import { Skeleton } from "frappe-ui";

defineProps({ rows: { type: Number, default: 4 } });
</script>

<template>
	<ul class="divide-y divide-outline-gray-1 rounded-6 border" aria-busy="true" :aria-label="__('Loading')">
		<li v-for="row in rows" :key="row" class="flex items-center gap-3 px-4 py-3">
			<Skeleton class="size-5 rounded" />
			<Skeleton class="h-4 rounded" :style="{ width: `${40 - row * 4}%` }" />
			<Skeleton class="ml-auto h-4 w-20 rounded" />
		</li>
	</ul>
</template>
