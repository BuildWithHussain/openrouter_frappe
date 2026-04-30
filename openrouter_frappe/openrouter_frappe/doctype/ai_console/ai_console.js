// Copyright (c) 2026, BHW and contributors
// For license information, please see license.txt

frappe.ui.form.on("AI Console", {
	refresh(frm) {
        frm.disable_save();
        frm.page.set_primary_action(__("Send Message"), ($btn) => {
            frm.call({
                method: "get_chat_output",
                doc: frm.doc,
                freeze: true,
                freeze_message: "Bot is responding.."
            }).then(d => {
                frm.set_value("output", d.message);
            })
		});
	},
});
