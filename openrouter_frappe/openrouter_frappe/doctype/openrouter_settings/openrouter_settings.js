// Copyright (c) 2026, BHW and contributors
// For license information, please see license.txt

frappe.ui.form.on("OpenRouter Settings", {
	refresh(frm) {
        frappe.call({
            method: "openrouter_frappe.utils.get_available_models",
            callback({message}) {
                frm.fields_dict.default_model.set_data(message);
            }
        })
	},
});
