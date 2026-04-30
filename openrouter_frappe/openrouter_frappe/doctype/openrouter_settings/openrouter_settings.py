# Copyright (c) 2026, BHW and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from openrouter_frappe.utils import get_openrouter_client


class OpenRouterSettings(Document):
	@property
	def credits(self):
		with get_openrouter_client() as client:
			response = client.credits.get_credits()
			data = response.data
			return data.total_credits - data.total_usage
		return 0.9
