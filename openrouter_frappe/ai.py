import base64

import frappe

from openrouter_frappe.utils import get_chat_completion

MODEL = ""
PDF_ENGINE = "cloudflare-ai"

ERROR_LOG_TITLE = "Invoice Processor"
NOT_AN_INVOICE_MARKER = "<NOT-AN-INVOICE>"
PROMPT_TEMPLATE_PATH = "templates/invoice_prompt.txt"


class InvoiceProcessor:
    def __init__(self, communication):
        self.communication = communication

    def process(self):
        if self.communication.sent_or_received != "Received":
            return

        try:
            attachments = self._collect_pdf_attachments()
            if not attachments:
                return

            reply = self._ask_llm(attachments)
            if not reply or reply.strip() == NOT_AN_INVOICE_MARKER:
                return

            invoice_data = self._parse_invoice(reply)
            if invoice_data is None:
                return

            self._create_purchase_invoice(invoice_data)
        except Exception:
            frappe.log_error(
                title=ERROR_LOG_TITLE,
                message=f"Failed to process communication {self.communication.name}\n\n{frappe.get_traceback()}",
            )

    def _collect_pdf_attachments(self):
        file_names = frappe.db.get_all(
            "File",
            filters={
                "file_type": "PDF",
                "attached_to_doctype": "Communication",
                "attached_to_name": self.communication.name,
            },
            pluck="name",
        )

        attachments = []
        for file_name in file_names:
            file_doc = frappe.get_doc("File", file_name)
            try:
                encoded = self._encode_pdf_to_base64(file_doc.get_full_path())
            except OSError:
                frappe.log_error(
                    title=ERROR_LOG_TITLE,
                    message=(
                        f"Could not read PDF {file_doc.file_name} "
                        f"for {self.communication.name}\n\n{frappe.get_traceback()}"
                    ),
                )
                continue

            attachments.append({
                "type": "file",
                "file": {
                    "filename": file_doc.file_name,
                    "file_data": f"data:application/pdf;base64,{encoded}",
                },
            })
        return attachments

    @staticmethod
    def _encode_pdf_to_base64(pdf_path: str) -> str:
        with open(pdf_path, "rb") as pdf_file:
            return base64.b64encode(pdf_file.read()).decode("utf-8")

    def _build_prompt(self) -> str:
        return frappe.render_template(PROMPT_TEMPLATE_PATH, context={"doc": self.communication})

    def _ask_llm(self, attachments) -> str:
        prompt = self._build_prompt()
        response = get_chat_completion([{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                *attachments,
            ],
        }])
        return response.choices[0].message.content

    def _parse_invoice(self, reply: str):
        try:
            return frappe.parse_json(reply)
        except Exception:
            frappe.log_error(
                title=ERROR_LOG_TITLE,
                message=(
                    f"LLM returned invalid JSON for {self.communication.name}:\n"
                    f"{reply}\n\n{frappe.get_traceback()}"
                ),
            )
            return None

    def _create_purchase_invoice(self, invoice_data: dict):
        frappe.get_doc({
            "doctype": "Purchase Invoice",
            "supplier": invoice_data["supplier_name"],
            "total_amount": invoice_data["total_amount"],
        }).insert()


def process_communication(doc, event=None):
    if not frappe.db.get_single_value("OpenRouter Settings", "enable_invoice_processor"):
        return
    InvoiceProcessor(doc).process()
