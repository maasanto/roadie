<script setup>
import { computed, ref, watch } from "vue";
import Gantt from "frappe-gantt";
import { ErrorMessage, LoadingText, useCall } from "frappe-ui";
import { formatDate } from "../gig";

const planning = useCall({ url: "/api/v2/method/band_crm.api.get_planning" });

const legend = [
	{ kind: "window", label: "Application window" },
	{ kind: "gig", label: "Gig" },
	{ kind: "task", label: "Task" },
	{ kind: "done", label: "Done" },
];

const lanes = computed(() => {
	const lanes = [];
	for (const bar of planning.data || []) {
		const lane = lanes.at(-1);
		if (lane?.title === bar.lane) lane.bars.push(bar);
		else lanes.push({ title: bar.lane, bars: [bar] });
	}
	return lanes;
});

const formatRange = (bar) =>
	bar.start === bar.end ? formatDate(bar.start) : `${formatDate(bar.start)} – ${formatDate(bar.end)}`;

const chart = ref(null);
watch([chart, () => planning.data], ([element, bars]) => {
	if (!element || !bars?.length) return;
	element.replaceChildren();
	new Gantt(
		element,
		bars.map((bar) => ({
			id: bar.id,
			name: `${bar.lane} · ${bar.label}`,
			start: bar.start,
			end: bar.end,
			progress: 0,
			custom_class: `bar-${bar.kind}`,
		})),
		{ readonly: true, view_mode: "Week", view_mode_select: true, auto_move_label: true },
	);
});
</script>

<template>
	<div class="p-6">
		<div class="flex flex-wrap items-center justify-between gap-3">
			<h1 class="text-2xl-semibold">Planning</h1>
			<ul class="flex flex-wrap gap-3 text-sm text-ink-gray-6">
				<li v-for="item in legend" :key="item.kind" class="flex items-center gap-1.5">
					<span class="planning-swatch size-3 rounded-sm" :class="`bar-${item.kind}`" />{{ item.label }}
				</li>
			</ul>
		</div>
		<LoadingText v-if="planning.loading && !planning.data" class="mt-4" />
		<ErrorMessage v-else-if="planning.error" class="mt-4" :message="planning.error" />
		<p v-else-if="!planning.data?.length" class="mt-4 text-p-base text-ink-gray-5">
			Nothing dated yet. Give a gig a date or an application window, or a task a due date.
		</p>
		<template v-else>
			<div ref="chart" class="mt-4 hidden overflow-hidden rounded-6 border md:block" />
			<div class="mt-4 space-y-6 md:hidden">
				<section v-for="(lane, index) in lanes" :key="index">
					<h2 class="pb-2 text-sm-medium text-ink-gray-7">{{ lane.title }}</h2>
					<ul class="divide-y divide-outline-gray-1 rounded-6 border">
						<li v-for="bar in lane.bars" :key="bar.id" class="flex items-baseline gap-2 px-3 py-2">
							<span class="planning-swatch size-3 shrink-0 rounded-sm" :class="`bar-${bar.kind}`" />
							<div class="min-w-0">
								<p class="text-base text-ink-gray-8">{{ bar.label }}</p>
								<p class="text-sm text-ink-gray-5">{{ formatRange(bar) }}</p>
							</div>
						</li>
					</ul>
				</section>
			</div>
		</template>
	</div>
</template>

<style>
/* frappe-gantt's exports map only exposes its stylesheet under a "style" condition that Vite's JS resolver ignores. */
@import "../../node_modules/frappe-gantt/dist/frappe-gantt.css";

.bar-window {
	--planning-bar: var(--surface-amber-2);
}
.bar-gig {
	--planning-bar: var(--surface-green-3);
}
.bar-task {
	--planning-bar: var(--surface-blue-2);
}
.bar-done {
	--planning-bar: var(--surface-gray-4);
}
.planning-swatch {
	background: var(--planning-bar);
}
.gantt .bar-wrapper .bar {
	fill: var(--planning-bar);
}
</style>
