import frappe
import base64
ONLY JSON, nothing els
from openrouter_frappe.utils import get_openrouter_client, get_default_model

MODEL = ""
PDF_ENGINE = "cloudflare-ai"

def encode_pdf_to_base64(pdf_path: str):
    with open(pdf_path, "rb") as pdf_file:
        return base64.b64encode(pdf_file.read()).decode('utf-8')

def process_communication(doc, event=None):
    if doc.sent_or_received != "Received":
        return
    
    text_content = doc.text_content
    subject = doc.subject

    attachments = frappe.db.get_all("File", filters={
        "file_type": "PDF",
        "attached_to_doctype": "Communication",
        "attached_to_name": doc.name
    }, pluck="name")

    attachments_base_64 = []
    for file in attachments:
        file_doc = frappe.get_doc("File", file)
        pdf_path = file_doc.get_full_path()
        encoded_pdf = encode_pdf_to_base64(pdf_path)
        attachments_base_64.append({
            "type": "file",
            "file": {
                "filename": file_doc.file_name,
                "file_data": f"data:application/pdf;base64,{encoded_pdf}"
            }
        })

    # Purchase Invoices: an email containing a sales invoice PDF

    prompt = """
    You are an invoice processing expert. Here are the details about an email recieved on our system along with PDF attachments. 

    <email>
        <text_content>{{ doc.text_content }}</text_content>
        <subject>{{ doc.subject }}</subject>
    </email>
    
    
    If the email has an invoice attached, process the PDF (along with the email context), reply with JSON (e) on this format:

```
    {
        "supplier_name": "Google Inc.",
        "currency": "USD",
        "items": [{
            "item_name": "Cloud Subscription",
            "qty": 2,
            "rate": 10,
            "amount": 20,
        }],
        "posting_date": "14-03-2025",
        "total_amount": 20.00 
    }
```

IMPORTANT: If there is no invoice, respond with "<NOT-AN-INVOICE>"
    """
    
    prompt = frappe.render_template(prompt, context={"doc": doc})

    with get_openrouter_client() as client:
        response = client.chat.send(
            model=get_default_model(),
            messages=[{"role": "user", "content": [
                {"type": "text", "text": prompt},
                *attachments_base_64
            ]}]
        )

        frappe.get_doc({
            "doctype": "OpenRouter Log",
            "reply": frappe.as_json(response)
        }).insert()

        reply = response.choices[0].message.content

        if reply == "<NOT-AN-INVOICE>":
            return

        invoice_data = frappe.parse_json(reply)

        frappe.get_doc({
            "doctype": "Purchase Invoice",
            "supplier": invoice_data["supplier_name"],
            "total_amount": invoice_data["total_amount"]
        }).insert()