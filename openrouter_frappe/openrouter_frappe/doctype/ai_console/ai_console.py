# Copyright (c) 2026, BHW and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from openrouter_frappe.utils import get_chat_completion


class AIConsole(Document):
	@frappe.whitelist()
	def get_chat_output(self):
		response = get_chat_completion(
			[{"role": "user", "content": self.message}],
			model=self.model or None,
		)
		return response.choices[0].message.content
