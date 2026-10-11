<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { Button } from "frappe-ui";
import { QUOTE_SELECTOR, asHtml } from "../email";

const props = defineProps({
	content: { type: String, default: "" },
});

// The frame is sized to its content, so content sized to the frame (height: 100%, 100vh) would grow it forever.
const FRAME_STYLE = `
	html, body { min-height: 0 !important; height: auto !important; }
	body { display: flow-root; margin: 0; font: 14px/1.5 Inter, system-ui, sans-serif; color: #383838; overflow-wrap: break-word; }
	img { max-width: 100%; height: auto; }
	html:not(.show-quotes) :is(${QUOTE_SELECTOR}) { display: none; }
`;
const srcdoc = computed(
	() =>
		`<!doctype html><html><head><meta charset="utf-8"><style>${FRAME_STYLE}</style></head>` +
		`<body>${asHtml(props.content)}</body></html>`
);

const frame = ref(null);
const hasQuote = ref(false);
const isShowingQuote = ref(false);
let resizeObserver = null;

// The sandbox runs no script, so reading the frame's own document is safe and stands in for iframe-resizer.
function fitToContent() {
	const email = frame.value.contentDocument;
	// Whatever target the email gave a link, opening it inside the thread pane would replace the email.
	email.querySelectorAll("a").forEach((link) => (link.target = "_blank"));
	hasQuote.value = Boolean(email.querySelector(QUOTE_SELECTOR));
	email.documentElement.classList.toggle("show-quotes", isShowingQuote.value);
	// A forward is all quote: folding it would leave an empty email behind the toggle.
	if (hasQuote.value && !email.body.innerText.trim()) isShowingQuote.value = true;
	resizeObserver?.disconnect();
	// The root's height includes the margins an email may set on its own body.
	resizeObserver = new ResizeObserver(() => {
		frame.value.style.height = `${email.documentElement.offsetHeight}px`;
	});
	resizeObserver.observe(email.documentElement);
}

watch(isShowingQuote, (isShowing) =>
	frame.value.contentDocument.documentElement.classList.toggle("show-quotes", isShowing)
);
onBeforeUnmount(() => resizeObserver?.disconnect());
</script>

<template>
	<div>
		<!-- No allow-scripts: the email can't run code, and its styles can't leak into the app. -->
		<iframe
			ref="frame"
			class="block h-0 w-full"
			sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"
			:srcdoc="srcdoc"
			:title="__('Email content')"
			@load="fitToContent"
		/>
		<Button
			v-if="hasQuote"
			class="mt-1"
			size="sm"
			icon="lucide-ellipsis"
			:label="isShowingQuote ? __('Hide quoted text') : __('Show quoted text')"
			:aria-pressed="isShowingQuote"
			@click="isShowingQuote = !isShowingQuote"
		/>
	</div>
</template>
