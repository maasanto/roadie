import { effectScope } from "vue";
import { useCall } from "frappe-ui";

// A DocType's meta only changes when its form is customised, so every form shares one fetch per session.
const sessionScope = effectScope(true);
const metas = {};

export const useMeta = (doctype) =>
	(metas[doctype] ??= sessionScope.run(() => useCall({ url: `/api/v2/doctype/${doctype}/meta` })));
