frappe.ui.form.on("Gig", {
	setup(frm) {
		frm.set_query("festival_edition", () => ({
			filters: frm.doc.festival ? { festival: frm.doc.festival } : {},
		}));
	},
});
