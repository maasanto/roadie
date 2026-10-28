<script setup>
import { Switch, call } from "frappe-ui";
import { onMounted, ref } from "vue";

const label = __("Email me when I'm mentioned");
const description = __("Mentions still appear in Roadie's notifications either way.");

const enabled = ref(false);
const loaded = ref(false);
const busy = ref(false);
const error = ref("");

function messageOf(err) {
	return err.messages?.join("\n") || err.message;
}

onMounted(async () => {
	try {
		enabled.value = await call("roadie.api.are_mention_emails_enabled");
		loaded.value = true;
	} catch (err) {
		error.value = messageOf(err);
	}
});

async function setEnabled(value) {
	busy.value = true;
	error.value = "";
	enabled.value = value;
	try {
		await call("roadie.api.set_mention_emails_enabled", { enabled: value });
	} catch (err) {
		enabled.value = !value;
		error.value = messageOf(err);
	} finally {
		busy.value = false;
	}
}
</script>

<template>
	<!-- Hidden until read, or the default case would show off and then flip on. -->
	<Switch
		v-if="loaded || error"
		:model-value="enabled"
		:label="label"
		:description="description"
		:error="error"
		:disabled="!loaded || busy"
		@update:model-value="setEnabled"
	/>
</template>
