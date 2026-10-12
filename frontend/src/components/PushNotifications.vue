<script setup>
import { Switch, toast } from "frappe-ui";
import { computed, ref } from "vue";
import { disablePush, enablePush, isPushEnabled } from "../push";

const enabled = ref(isPushEnabled());
const blocked = ref(Notification.permission === "denied");
const busy = ref(false);
const error = ref("");

const description = computed(() =>
	blocked.value
		? __("Notifications are blocked for Roadie in this browser's site settings.")
		: __("Assignments, deadlines and mentions reach this device even when Roadie is closed.")
);

async function turnOn() {
	await enablePush();
	blocked.value = Notification.permission === "denied";
	if (isPushEnabled()) toast.success(__("Push notifications turned on for this device"));
}

// Whichever step fails, the switch then shows what the device still holds, so turning it off can be retried.
async function run(action) {
	busy.value = true;
	error.value = "";
	try {
		await action();
	} catch (err) {
		error.value = err.message;
	} finally {
		enabled.value = isPushEnabled();
		busy.value = false;
	}
}
</script>

<template>
	<section>
		<h2 class="text-lg-semibold">{{ __("Notifications") }}</h2>
		<Switch
			class="mt-3"
			:model-value="enabled"
			:label="__('Push notifications on this device')"
			:description="description"
			:error="error"
			:disabled="busy || (blocked && !enabled)"
			@update:model-value="(turningOn) => run(turningOn ? turnOn : disablePush)"
		/>
	</section>
</template>
