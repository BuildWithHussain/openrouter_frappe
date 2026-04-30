// Copyright (c) 2026, BHW and contributors
// For license information, please see license.txt

frappe.query_reports["OpenRouter Usage"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.now_date(),
			reqd: 1,
		},
		{
			fieldname: "model",
			label: __("Model"),
			fieldtype: "Autocomplete",
			options: [],
		},
		{
			fieldname: "provider_name",
			label: __("Provider"),
			fieldtype: "Data",
		},
	],

	onload(report) {
		frappe.call({
			method: "openrouter_frappe.utils.get_available_models",
			callback({ message }) {
				const filter = report.get_filter("model");
				if (!filter || !message) return;
				filter.df.options = message;
				filter.refresh();
			},
		});
	},
};
