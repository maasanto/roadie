<script setup>
import { reactive } from "vue";
import { Avatar, Button, ErrorMessage, FormControl, useCall } from "frappe-ui";

const props = defineProps({ doctype: { type: String, required: true }, name: { type: String, required: true } });

const contacts = useCall({
	url: "/api/v2/method/roadie.api.get_contacts",
	params: () => ({ doctype: props.doctype, name: props.name }),
});
const createContact = useCall({ url: "/api/v2/document/Contact", method: "POST", immediate: false });
const deleteContact = useCall({ url: "/api/v2/method/frappe.client.delete", method: "POST", immediate: false });

const draft = reactive({ first_name: "", last_name: "", email: "", phone: "" });

async function addContact() {
	await createContact.submit({
		first_name: draft.first_name,
		last_name: draft.last_name,
		email_ids: draft.email ? [{ email_id: draft.email, is_primary: 1 }] : [],
		phone_nos: draft.phone ? [{ phone: draft.phone, is_primary_phone: 1 }] : [],
		links: [{ link_doctype: props.doctype, link_name: props.name }],
	});
	if (createContact.error) return;
	Object.assign(draft, { first_name: "", last_name: "", email: "", phone: "" });
	contacts.reload();
}

async function removeContact(contactName) {
	await deleteContact.submit({ doctype: "Contact", name: contactName });
	contacts.reload();
}
</script>

<template>
	<section>
		<h2 class="text-lg-semibold">{{ __("Contacts") }}</h2>
		<ul v-if="contacts.data?.length" class="mt-3 divide-y divide-outline-gray-1 rounded-6 border">
			<li v-for="contact in contacts.data" :key="contact.name" class="flex items-center gap-3 px-3 py-2">
				<Avatar :label="contact.full_name" size="sm" />
				<span class="min-w-0 flex-1 truncate text-base">{{ contact.full_name }}</span>
				<a v-if="contact.email_id" :href="`mailto:${contact.email_id}`" class="text-sm text-ink-blue-link">{{ contact.email_id }}</a>
				<span class="w-32 truncate text-sm text-ink-gray-5">{{ contact.phone || contact.mobile_no }}</span>
				<Button icon="lucide-trash-2" variant="ghost" :label="__('Remove contact')"@click="removeContact(contact.name)" />
			</li>
		</ul>
		<p v-else-if="contacts.isFinished" class="mt-3 text-p-sm text-ink-gray-5">{{ __("No contacts yet.") }}</p>
		<ErrorMessage class="mt-2" :message="contacts.error || deleteContact.error" />
		<form class="mt-3 grid grid-cols-[1fr_1fr_1.4fr_1fr_auto] items-end gap-2" @submit.prevent="addContact">
			<FormControl v-model="draft.first_name" :label="__('First name')" required />
			<FormControl v-model="draft.last_name" :label="__('Last name')" />
			<FormControl v-model="draft.email" type="email" :label="__('Email')" />
			<FormControl v-model="draft.phone" type="tel" :label="__('Phone')" />
			<Button type="submit" icon-left="lucide-plus" :label="__('Add')":loading="createContact.loading" />
		</form>
		<ErrorMessage class="mt-2" :message="createContact.error" />
	</section>
</template>
