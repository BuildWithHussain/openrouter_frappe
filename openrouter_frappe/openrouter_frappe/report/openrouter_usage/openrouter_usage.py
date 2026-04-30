# Copyright (c) 2026, BHW and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import get_first_day, getdate, nowdate


def execute(filters=None):
    filters = frappe._dict(filters or {})
    from_date = getdate(filters.from_date or get_first_day(nowdate()))
    to_date = getdate(filters.to_date or nowdate())

    where = ["DATE(creation) BETWEEN %(from_date)s AND %(to_date)s"]
    params = {"from_date": from_date, "to_date": to_date}

    if filters.model:
        where.append("model = %(model)s")
        params["model"] = filters.model
    if filters.provider_name:
        where.append("provider_name = %(provider_name)s")
        params["provider_name"] = filters.provider_name

    where_clause = " AND ".join(where)

    rows = frappe.db.sql(
        f"""
        SELECT
            name,
            creation,
            generation_id,
            model,
            provider_name,
            prompt_tokens,
            cached_tokens,
            completion_tokens,
            reasoning_tokens,
            total_tokens,
            total_cost,
            generation_time_ms,
            latency_ms
        FROM `tabOpenRouter Log`
        WHERE {where_clause}
        ORDER BY creation DESC
        """,
        params,
        as_dict=True,
    )

    for row in rows:
        row["total_cost_display"] = _format_usd(row.get("total_cost"))

    columns = _get_columns()
    summary = _get_summary(rows)
    return columns, rows, None, None, summary


def _format_usd(value):
    """Format a USD amount with up to 9 dp, stripping trailing zeros (min 2 dp)."""
    if value is None:
        return ""
    s = f"{value:.9f}".rstrip("0")
    if s.endswith("."):
        s += "00"
    elif "." in s and len(s.split(".")[1]) == 1:
        s += "0"
    return f"$ {s}"


def _get_columns():
    return [
        {
            "fieldname": "creation",
            "label": _("Created"),
            "fieldtype": "Datetime",
            "width": 160,
        },
        {
            "fieldname": "name",
            "label": _("Log"),
            "fieldtype": "Link",
            "options": "OpenRouter Log",
            "width": 130,
        },
        {
            "fieldname": "generation_id",
            "label": _("Generation ID"),
            "fieldtype": "Data",
            "width": 240,
        },
        {
            "fieldname": "model",
            "label": _("Model"),
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "fieldname": "provider_name",
            "label": _("Provider"),
            "fieldtype": "Data",
            "width": 110,
        },
        {
            "fieldname": "prompt_tokens",
            "label": _("Prompt"),
            "fieldtype": "Int",
            "width": 90,
        },
        {
            "fieldname": "cached_tokens",
            "label": _("Cached"),
            "fieldtype": "Int",
            "width": 90,
        },
        {
            "fieldname": "completion_tokens",
            "label": _("Completion"),
            "fieldtype": "Int",
            "width": 100,
        },
        {
            "fieldname": "reasoning_tokens",
            "label": _("Reasoning"),
            "fieldtype": "Int",
            "width": 100,
        },
        {
            "fieldname": "total_tokens",
            "label": _("Total Tokens"),
            "fieldtype": "Int",
            "width": 110,
        },
        {
            "fieldname": "total_cost_display",
            "label": _("Cost (USD)"),
            "fieldtype": "Data",
            "align": "right",
            "width": 130,
        },
        {
            "fieldname": "generation_time_ms",
            "label": _("Gen (ms)"),
            "fieldtype": "Int",
            "width": 90,
        },
        {
            "fieldname": "latency_ms",
            "label": _("Latency (ms)"),
            "fieldtype": "Int",
            "width": 110,
        },
    ]


def _get_summary(rows):
    total_requests = len(rows)
    total_tokens = sum((r.get("total_tokens") or 0) for r in rows)
    reasoning_tokens = sum((r.get("reasoning_tokens") or 0) for r in rows)
    total_cost = sum((r.get("total_cost") or 0) for r in rows)
    pending = sum(1 for r in rows if not r.get("provider_name"))

    return [
        {
            "value": total_requests,
            "label": _("Requests"),
            "datatype": "Int",
            "indicator": "blue",
        },
        {
            "value": total_tokens,
            "label": _("Total Tokens"),
            "datatype": "Int",
            "indicator": "blue",
        },
        {
            "value": reasoning_tokens,
            "label": _("Reasoning Tokens"),
            "datatype": "Int",
            "indicator": "purple",
        },
        {
            "value": _format_usd(total_cost),
            "label": _("Total Cost (USD)"),
            "datatype": "Data",
            "indicator": "green",
        },
        {
            "value": pending,
            "label": _("Awaiting Cost Data"),
            "datatype": "Int",
            "indicator": "orange" if pending else "gray",
        },
    ]
