import { onUnmounted, ref } from "vue";

export function useIsPhone() {
	const phone = window.matchMedia("(max-width: 639px)");
	const isPhone = ref(phone.matches);
	const onPhoneChange = (event) => (isPhone.value = event.matches);
	phone.addEventListener("change", onPhoneChange);
	onUnmounted(() => phone.removeEventListener("change", onPhoneChange));
	return isPhone;
}
