# Copyright (c) 2026, BHW and contributors
# For license information, please see license.txt

import frappe
from openrouter import OpenRouter
from frappe.model.document import Document

from openrouter_frappe.utils import get_openrouter_client, get_default_model


class AIConsole(Document):
	@frappe.whitelist()
	def get_chat_output(self):
		with get_openrouter_client() as client:
			response = client.chat.send(
				model=get_default_model(),
				messages=[{"role": "user", "content": self.message}]
			)
			return response.choices[0].message.content
