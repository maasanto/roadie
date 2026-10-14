<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import Gantt from "frappe-gantt";
import { Button, ErrorMessage, call, toast, useCall } from "frappe-ui";
import EmptyState from "../components/EmptyState.vue";
import GigPanel from "../components/GigPanel.vue";
import ListSkeleton from "../components/ListSkeleton.vue";
import TaskDialog from "../components/TaskDialog.vue";
import { formatDate } from "../gig";
import { useGigControls } from "../gigControls";
import { UNDO_WINDOW_MS } from "../undo";

const planning = useCall({ url: "/api/v2/method/roadie.api.get_planning" });
const { members, controls } = useGigControls();

const legend = [
	{ kind: "window", label: __("Application window") },
	{ kind: "gig", label: __("Gig") },
	{ kind: "task", label: __("Task") },
	{ kind: "done", label: __("Done") },
];

// frappe-gantt hard-codes its header controls in English and rebuilds them on every view change.
const GANTT_CONTROL_LABELS = {
	Mode: __("Mode"),
	Hour: __("Hour"),
	"Quarter Day": __("Quarter Day"),
	"Half Day": __("Half Day"),
	Day: __("Day"),
	Week: __("Week"),
	Month: __("Month"),
	Year: __("Year"),
};

function translateGanttControls() {
	for (const option of chart.value.querySelectorAll(".viewmode-select option"))
		option.textContent = GANTT_CONTROL_LABELS[option.value] || option.textContent;
	chart.value.querySelector(".today-button").textContent = __("Today");
}

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

const toGanttTasks = (bars) =>
	bars.map((bar) => ({
		id: bar.id,
		name: `${bar.lane} · ${bar.label}`,
		start: bar.start,
		end: bar.end,
		progress: bar.kind === "done" ? 100 : 0,
		custom_class: `bar-${bar.kind}`,
	}));
const barOf = (task) => planning.data.find((bar) => bar.id === task.id);
const toIsoDate = (date) => date.toLocaleDateString("en-CA");
const isTaskBar = (bar) => ["task", "done"].includes(bar.kind);
const recordTitle = (bar) => (isTaskBar(bar) ? bar.label : bar.lane);
const nameOf = (user) => members.data?.find((member) => member.name === user)?.full_name || user;

// Built with textContent: frappe-gantt sets its popup through innerHTML, and titles are user-typed.
function showPopup({ task, get_title, get_subtitle, get_details }) {
	const bar = barOf(task);
	const isTask = isTaskBar(bar);
	get_title().textContent = recordTitle(bar);
	get_subtitle().textContent = isTask ? bar.lane : bar.label;
	const person = isTask
		? __("Assignee: {0}", [nameOf(bar.person)])
		: __("Owner: {0}", [nameOf(bar.person)]);
	get_details().textContent = [formatRange(bar), bar.person && person].filter(Boolean).join(" · ");
}

let gantt = null;
// gantt.refresh() would scroll back to today, away from the bar that was just moved.
function redrawBars() {
	gantt.setup_tasks(toGanttTasks(planning.data));
	gantt.change_view_mode(undefined, true);
}

function reschedule(bar, start, end) {
	return call("roadie.api.reschedule", { kind: bar.kind, name: bar.name, start, end });
}

async function saveDrag({ bar, start, end }) {
	const previous = {
		start: bar.start,
		end: bar.end,
		saved_start: bar.saved_start,
		saved_end: bar.saved_end,
	};
	try {
		await reschedule(bar, start, end);
	} catch (error) {
		redrawBars();
		toast.error(error.messages?.join("\n") || error.message);
		return;
	}
	Object.assign(bar, { start, end, saved_start: start, saved_end: end });
	toast(__("New dates for {0}: {1}", [recordTitle(bar), formatRange(bar)]), {
		action: { label: __("Undo"), onClick: () => undoDrag(bar, previous) },
		duration: UNDO_WINDOW_MS,
	});
}

async function undoDrag(bar, previous) {
	try {
		await reschedule(bar, previous.saved_start, previous.saved_end);
	} catch (error) {
		toast.error(error.messages?.join("\n") || error.message);
		return;
	}
	Object.assign(bar, previous);
	redrawBars();
}

// frappe-gantt fires on_date_change on every step of a drag, so only the last one is saved, once the mouse is released.
let pendingDrag = null;
function savePendingDrag() {
	if (pendingDrag) saveDrag(pendingDrag);
	pendingDrag = null;
}
onMounted(() => document.addEventListener("mouseup", savePendingDrag));
onUnmounted(() => document.removeEventListener("mouseup", savePendingDrag));

const isPanelOpen = ref(false);
const openedGig = ref(null);
const isTaskOpen = ref(false);
const openedTask = ref(null);

function openBar(task) {
	// The browser also clicks the bar at the end of a drag.
	if (gantt.get_bar(task.id).action_completed) return;
	const bar = barOf(task);
	if (bar.gig) {
		openedGig.value = bar.gig;
		isPanelOpen.value = true;
	} else {
		openedTask.value = bar;
		isTaskOpen.value = true;
	}
}

const chart = ref(null);
watch([chart, () => planning.data], ([element, bars]) => {
	if (!element || !bars?.length) return;
	element.replaceChildren();
	gantt = new Gantt(element, toGanttTasks(bars), {
		readonly_progress: true,
		view_mode: "Week",
		view_mode_select: true,
		auto_move_label: true,
		language: window.lang,
		popup_on: "hover",
		popup: showPopup,
		on_view_change: translateGanttControls,
		on_click: openBar,
		on_date_change: (task, start, end) => {
			pendingDrag = { bar: barOf(task), start: toIsoDate(start), end: toIsoDate(end) };
		},
	});
});
</script>

<template>
	<div class="p-6">
		<div class="flex flex-wrap items-center justify-between gap-3">
			<h1 class="text-2xl-semibold">{{ __("Planning") }}</h1>
			<ul class="flex flex-wrap gap-3 text-sm text-ink-gray-6">
				<li v-for="item in legend" :key="item.kind" class="flex items-center gap-1.5">
					<span class="planning-swatch size-3 rounded-sm" :class="`bar-${item.kind}`" />{{
						item.label
					}}
				</li>
			</ul>
		</div>
		<ListSkeleton v-if="planning.loading && !planning.data" class="mt-4" :rows="6" />
		<ErrorMessage v-else-if="planning.error" class="mt-4" :message="planning.error" />
		<EmptyState
			v-else-if="!planning.data?.length"
			class="mt-4"
			icon="lucide-calendar-range"
			:title="__('Nothing on the calendar yet')"
			:description="
				__('Nothing dated yet. Give a gig a date or an application window, or a task a due date.')
			"
		>
			<Button :label="__('Open the pipeline')" route="/" />
		</EmptyState>
		<template v-else>
			<div ref="chart" class="mt-4 hidden overflow-hidden rounded-6 border md:block" />
			<div class="mt-4 space-y-6 md:hidden">
				<section v-for="(lane, index) in lanes" :key="index">
					<h2 class="pb-2 text-sm-medium text-ink-gray-7">{{ lane.title }}</h2>
					<ul class="divide-y divide-outline-gray-1 rounded-6 border">
						<li
							v-for="bar in lane.bars"
							:key="bar.id"
							class="flex items-baseline gap-2 px-3 py-2"
						>
							<span
								class="planning-swatch size-3 shrink-0 rounded-sm"
								:class="`bar-${bar.kind}`"
							/>
							<div class="min-w-0">
								<p class="text-base text-ink-gray-8">{{ bar.label }}</p>
								<p class="text-sm text-ink-gray-5">{{ formatRange(bar) }}</p>
							</div>
						</li>
					</ul>
				</section>
			</div>
		</template>
		<GigPanel
			v-if="isPanelOpen"
			:name="openedGig"
			:controls="controls"
			@close="isPanelOpen = false"
			@saved="planning.reload()"
		/>
		<TaskDialog
			v-if="openedTask"
			v-model:open="isTaskOpen"
			:name="openedTask.name"
			:title="openedTask.label"
		/>
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
/* A gig is a single day: it moves, but never stretches. */
.gantt .bar-wrapper.bar-gig .handle {
	display: none;
}
</style>
