// Copyright (c) 2026, BHW and contributors
// For license information, please see license.txt

frappe.ui.form.on("AI Console", {
	refresh(frm) {
        frm.disable_save();

        frappe.call({
            method: "openrouter_frappe.utils.get_available_models",
            callback({message}) {
                frm.fields_dict.model.set_data(message || []);
            }
        });

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
