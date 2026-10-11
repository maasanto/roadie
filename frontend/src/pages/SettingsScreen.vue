<script setup>
import { Avatar, Button, ErrorMessage, FileUploader, call, toast } from "frappe-ui";
import { ref } from "vue";
import { initials, user } from "../user";

const error = ref("");

// frappe.client.set_value on their own User: the standard call a member is allowed to make for themselves.
async function setPicture(fileUrl) {
	error.value = "";
	try {
		await call("frappe.client.set_value", {
			doctype: "User",
			name: user.name,
			fieldname: "user_image",
			value: fileUrl,
		});
		user.image = fileUrl;
		toast.success(fileUrl ? __("Profile picture updated") : __("Profile picture removed"));
	} catch (err) {
		error.value = err.messages?.join("\n") || err.message;
	}
}
</script>

<template>
	<div class="max-w-3xl p-6">
		<h1 class="text-2xl-semibold">{{ __("Settings") }}</h1>

		<section class="mt-6 flex items-center gap-4">
			<FileUploader
				:upload-args="{
					doctype: 'User',
					docname: user.name,
					fieldname: 'user_image',
					private: false,
				}"
				:file-types="['image/*']"
				@success="(file) => setPicture(file.file_url)"
			>
				<template #default="{ openFileSelector, uploading, error: uploadError }">
					<button
						type="button"
						class="group relative shrink-0 rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
						@click="openFileSelector"
					>
						<Avatar :image="user.image" :label="user.fullName" class="size-20">
							<span class="text-2xl-medium">{{ initials(user.fullName) }}</span>
						</Avatar>
						<span
							class="absolute inset-0 flex items-center justify-center rounded-full bg-black/40 text-sm-medium text-white opacity-0 duration-300 group-hover:opacity-100"
						>
							{{ uploading ? __("Uploading…") : user.image ? __("Change") : __("Upload") }}
						</span>
					</button>
					<ErrorMessage class="mt-2" :message="uploadError" />
				</template>
			</FileUploader>

			<div class="min-w-0">
				<div class="truncate text-lg-semibold text-ink-gray-8">{{ user.fullName }}</div>
				<div class="truncate text-p-sm text-ink-gray-6">{{ user.name }}</div>
				<Button
					v-if="user.image"
					class="mt-2"
					variant="ghost"
					:label="__('Remove picture')"
					@click="setPicture('')"
				/>
			</div>
		</section>

		<ErrorMessage class="mt-4" :message="error" />
	</div>
</template>
