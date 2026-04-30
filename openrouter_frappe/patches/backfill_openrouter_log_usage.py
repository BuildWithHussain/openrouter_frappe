import json

import frappe

from openrouter_frappe.utils import extract_log_fields


def execute():
    """Populate the new usage / metadata fields on existing OpenRouter Log rows.

    Older logs were stored by passing a Pydantic model straight to ``frappe.as_json``,
    which falls back on ``__iter__`` and produces a list of ``[key, value]`` pairs
    instead of a JSON object. Normalize that back into a dict before extracting.
    """
    rows = frappe.db.get_all("OpenRouter Log", fields=["name", "reply"])
    for row in rows:
        raw = row.get("reply")
        if not raw:
            continue

        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
        except (TypeError, ValueError):
            continue

        normalized = _pairs_to_obj(parsed)
        if not isinstance(normalized, dict):
            continue

        update = extract_log_fields(normalized)
        update["reply"] = frappe.as_json(normalized)
        frappe.db.set_value("OpenRouter Log", row.name, update, update_modified=False)


def _pairs_to_obj(value):
    """Recursively convert lists of ``[key, value]`` pairs back into dicts."""
    if isinstance(value, list):
        if value and all(
            isinstance(item, (list, tuple)) and len(item) == 2 and isinstance(item[0], str)
            for item in value
        ):
            return {k: _pairs_to_obj(v) for k, v in value}
        return [_pairs_to_obj(item) for item in value]
    if isinstance(value, dict):
        return {k: _pairs_to_obj(v) for k, v in value.items()}
    return value
