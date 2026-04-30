import os
import frappe

from openrouter import OpenRouter
from openrouter.errors import NotFoundResponseError

# How long after creation we keep retrying generation metadata before giving up.
METADATA_FETCH_WINDOW = "1 DAY"

# Max logs the scheduler will try per run, to bound work in busy installs.
METADATA_FETCH_BATCH = 50


def get_openrouter_key(throw=False):
    key = frappe.conf.get("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY")

    if not key and throw:
        frappe.throw("OpenRouter API Key not set!")

    return key

def get_default_model() -> str:
    return frappe.get_cached_doc("OpenRouter Settings").default_model

def get_openrouter_client():
    return OpenRouter(api_key=get_openrouter_key())


def get_chat_completion(messages: list):
    with get_openrouter_client() as client:
        response = client.chat.send(
            model=get_default_model(),
            messages=messages
        )

        log_data = response.model_dump(mode="json")
        frappe.get_doc({
            "doctype": "OpenRouter Log",
            **extract_log_fields(log_data),
            "reply": frappe.as_json(log_data),
        }).insert()

        return response


def extract_log_fields(response_data: dict) -> dict:
    """Pull the fields we surface on OpenRouter Log out of a chat completion response dict."""
    usage = response_data.get("usage") or {}
    completion_details = usage.get("completion_tokens_details") or {}
    prompt_details = usage.get("prompt_tokens_details") or {}
    choices = response_data.get("choices") or []
    finish_reason = choices[0].get("finish_reason") if choices else None

    return {
        "generation_id": response_data.get("id"),
        "model": response_data.get("model"),
        "finish_reason": finish_reason,
        "prompt_tokens": usage.get("prompt_tokens") or 0,
        "cached_tokens": (prompt_details or {}).get("cached_tokens") or 0,
        "completion_tokens": usage.get("completion_tokens") or 0,
        "reasoning_tokens": (completion_details or {}).get("reasoning_tokens") or 0,
        "total_tokens": usage.get("total_tokens") or 0,
    }


def fetch_pending_metadata():
    """Fetch cost / latency / provider metadata from OpenRouter for any logs that don't have it yet.

    Cost data isn't available immediately after a chat completion — OpenRouter populates
    the /generation endpoint a few seconds later. This scheduler walks recently-created
    logs missing metadata and fills it in.
    """
    if not get_openrouter_key():
        return

    rows = frappe.db.sql(
        """
        SELECT name, generation_id
        FROM `tabOpenRouter Log`
        WHERE metadata_fetched = 0
          AND generation_id IS NOT NULL
          AND creation > NOW() - INTERVAL {window}
        ORDER BY creation ASC
        LIMIT %s
        """.format(window=METADATA_FETCH_WINDOW),
        (METADATA_FETCH_BATCH,),
        as_dict=True,
    )
    if not rows:
        return

    with get_openrouter_client() as client:
        for row in rows:
            _try_fetch_metadata(client, row.name, row.generation_id)


def _try_fetch_metadata(client, log_name: str, generation_id: str):
    try:
        gen = client.generations.get_generation(id=generation_id)
    except NotFoundResponseError:
        # Not ready yet — leave for a later run.
        return
    except Exception:
        frappe.log_error(title=f"OpenRouter metadata fetch failed for {generation_id}")
        return

    data = gen.data
    update = {
        "total_cost": data.total_cost or 0,
        "cache_discount": data.cache_discount or 0,
        "generation_time_ms": int(data.generation_time) if data.generation_time is not None else 0,
        "latency_ms": int(data.latency) if data.latency is not None else 0,
        "provider_name": data.provider_name,
        "metadata_fetched": 1,
    }
    frappe.db.set_value("OpenRouter Log", log_name, update, update_modified=False)
    frappe.db.commit()


@frappe.whitelist()
def get_available_models() -> list[str]:
    models = []
    with get_openrouter_client() as open_router:
        response = open_router.models.list()
        models = [model.id for model in response.data]

    return models
