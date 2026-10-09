<script setup>
import { Badge, ErrorMessage, LoadingText, useList } from "frappe-ui";

const gigs = useList({ doctype: "Gig", fields: ["name", "title", "status"], orderBy: "modified desc", limit: 100 });
</script>

<template>
	<div class="p-6">
		<h1 class="text-2xl-semibold">Pipeline</h1>
		<LoadingText v-if="gigs.loading && !gigs.data" class="mt-4" />
		<ErrorMessage v-else-if="gigs.error" class="mt-4" :message="gigs.error" />
		<p v-else-if="!gigs.data?.length" class="mt-4 text-p-base text-ink-gray-5">No gigs yet.</p>
		<ul v-else class="mt-4 divide-y divide-outline-gray-1 rounded-6 border">
			<li v-for="gig in gigs.data" :key="gig.name" class="flex items-center justify-between px-4 py-3">
				<span class="text-base">{{ gig.title }}</span>
				<Badge :label="gig.status" />
			</li>
		</ul>
	</div>
</template>
