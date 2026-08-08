"""Intent classification via the LLM, returning one of the fixed categories."""
from __future__ import annotations

import json

from src import llm

INTENTS = [
    "order_delivery_status",
    "product_specs_docs",
    "installation_maintenance",
    "warranty_amc",
    "complaint_issue",
    "payment_invoice",
    "spare_parts",
    "certifications_compliance",
    "general_query",
    "unknown",
]

_SYSTEM = (
    "You are an intent classifier for a medical-equipment customer-support "
    "chatbot. Classify the user's message into exactly one intent. "
    "Respond with STRICT JSON only: {\"intent\": <one of the labels>, "
    "\"confidence\": <0..1>}. No prose.\n\n"
    "Labels and meaning:\n"
    "- order_delivery_status: order tracking, delivery dates, delays, damage.\n"
    "- product_specs_docs: technical specs, manuals, compatibility, how-to.\n"
    "- installation_maintenance: schedule install, preventive maintenance, technician visit.\n"
    "- warranty_amc: warranty period, AMC enrollment/coverage/status, extensions.\n"
    "- complaint_issue: log faults/breakdowns, track ticket, escalate.\n"
    "- payment_invoice: invoices, receipts, overcharges, refunds, credit notes.\n"
    "- spare_parts: spare-part availability, replacements, accessory compatibility.\n"
    "- certifications_compliance: ISO/CE/FDA certificates, regulatory compliance.\n"
    "- general_query: business hours, contact options, documentation policy.\n"
    "- unknown: anything not covered above.\n"
)

_FEWSHOT = (
    "Examples:\n"
    "Message: Where is my CT scanner order? -> {\"intent\":\"order_delivery_status\",\"confidence\":0.95}\n"
    "Message: What is the field strength of the MagnaScan MRI? -> {\"intent\":\"product_specs_docs\",\"confidence\":0.93}\n"
    "Message: Is my warranty still valid? -> {\"intent\":\"warranty_amc\",\"confidence\":0.94}\n"
    "Message: My monitor won't turn on, log a complaint. -> {\"intent\":\"complaint_issue\",\"confidence\":0.95}\n"
    "Message: Can you send the FDA certificate? -> {\"intent\":\"certifications_compliance\",\"confidence\":0.92}\n"
    "Message: What are your business hours? -> {\"intent\":\"general_query\",\"confidence\":0.9}\n"
)


def classify(message: str) -> tuple[str, float]:
    raw = llm.complete(
        system=_SYSTEM,
        user=_FEWSHOT + "\nMessage: " + message + " ->",
        task="intent",
        temperature=0.0,
        max_tokens=60,
    )
    intent, conf = _parse(raw)
    if intent not in INTENTS:
        intent, conf = "unknown", 0.0
    return intent, conf


def _parse(raw: str) -> tuple[str, float]:
    try:
        start = raw.index("{")
        end = raw.rindex("}") + 1
        data = json.loads(raw[start:end])
        return str(data.get("intent", "unknown")), float(data.get("confidence", 0.0))
    except Exception:
        # last-ditch: match a bare label
        for label in INTENTS:
            if label in raw:
                return label, 0.5
        return "unknown", 0.0
