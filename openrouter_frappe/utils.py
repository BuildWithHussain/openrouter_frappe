import os
import frappe

from openrouter import OpenRouter

def get_openrouter_key(throw=False):
    key = frappe.conf.get("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY")

    if not key and throw:
        frappe.throw("OpenRouter API Key not set!")

    return key

def get_default_model() -> str:
    return frappe.get_cached_doc("OpenRouter Settings").default_model

def get_openrouter_client():
    return OpenRouter(api_key=get_openrouter_key()) 


@frappe.whitelist()
def get_available_models() -> list[str]:
    models = []
    with get_openrouter_client() as open_router:
        response = open_router.models.list()
        models = [model.id for model in response.data]

    return models