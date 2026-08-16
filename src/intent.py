"""Intent classification: fast rules-first, LLM fallback for ambiguity.

A high-precision keyword classifier resolves the common, unambiguous phrasings
with ZERO LLM latency. Only genuinely ambiguous messages fall through to the
LLM. `route_for()` then decides SQL vs RAG and, crucially, sends policy/how-to
phrasings to the documents (RAG) even when the topic (e.g. warranty) is
otherwise a structured-data intent — so "is my warranty active" hits SQL while
"what warranty comes with new equipment" hits the policy doc.
"""
from __future__ import annotations

import json

import config
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

# High-precision keyword rules, evaluated in order (first match wins).
_RULES = [
    ("complaint_issue", ["complaint", "ticket", "broken", "not working", "doesn't work",
                         "won't turn on", "not powering", "fault", "faulty", "breakdown",
                         "malfunction", "escalate"]),
    ("order_delivery_status", ["order status", "my order", "delivery", "deliver", "shipment",
                               "shipped", "tracking", "track my", "arrive", "dispatch",
                               "in transit", "where is my order"]),
    ("payment_invoice", ["invoice", "payment", "refund", "overcharge", "receipt",
                         "credit note", " bill", "amount due", "overdue"]),
    ("warranty_amc", ["warranty", "amc", "annual maintenance contract", "coverage",
                      "warranty period"]),
    ("spare_parts", ["spare part", "spare", "replacement part", "accessory", "probe",
                     "ecg cable", "in stock", "part availability", "order a part"]),
    ("installation_maintenance", ["installation", "install ", "schedule", "preventive maintenance",
                                  "technician visit", "book a", "maintenance visit",
                                  "service visit"]),
    ("certifications_compliance", ["iso ", "ce mark", "ce certificate", "fda", "certificate",
                                   "certification", "compliance", "regulatory", "regulation"]),
    ("product_specs_docs", ["specification", "specs", "manual", "compatible", "compatibility",
                            "field strength", "software version", "how do i", "how to",
                            "clean the", "user manual", "datasheet"]),
    ("general_query", ["business hours", "opening hours", "contact", "support hours",
                       "phone number", "email address", "documentation policy", "reach support"]),
]

# Phrasings that signal a POLICY / document question -> force RAG route.
_POLICY_SIGNALS = ["policy", "comes with", "come with", "how long", "terms", "what warranty",
                   "standard warranty", "included with", "new equipment", "how do i", "how to",
                   "what is the", "what are the", "explain", "process for", "procedure"]
# Phrasings that signal a personal-record LOOKUP -> keep SQL route.
_LOOKUP_SIGNALS = ["my ", "our ", "mine", "for my", "i have", "we have", "status of",
                   "is my", "when does my", "track", "number", " id "]


def _rule_match(message: str):
    text = " " + message.lower().strip() + " "
    for intent, kws in _RULES:
        if any(k in text for k in kws):
            return intent
    return None


def classify(message: str) -> tuple[str, float]:
    """Rules-first; fall back to the LLM only when no rule matches."""
    hit = _rule_match(message)
    if hit:
        return hit, 0.95
    return _llm_classify(message)


def route_for(intent: str, message: str) -> str:
    """Decide SQL | RAG | FALLBACK. Policy/how-to phrasings go to documents."""
    if intent == "unknown":
        return "FALLBACK"
    if intent in config.RAG_INTENTS:
        return "RAG"
    if intent in config.SQL_INTENTS:
        text = " " + message.lower() + " "
        policy = any(s in text for s in _POLICY_SIGNALS)
        lookup = any(s in text for s in _LOOKUP_SIGNALS)
        if policy and not lookup:
            return "RAG"
        return "SQL"
    return "FALLBACK"


# --------------------------------------------------------------------------- #
# LLM fallback (used only for ambiguous messages the rules can't resolve)
# --------------------------------------------------------------------------- #
_SYSTEM = (
    "You are an intent classifier for a medical-equipment customer-support "
    "chatbot. Classify the user's message into exactly one intent. "
    "Respond with STRICT JSON only: {\"intent\": <one of the labels>, "
    "\"confidence\": <0..1>}. No prose.\n\n"
    "Labels: order_delivery_status, product_specs_docs, installation_maintenance, "
    "warranty_amc, complaint_issue, payment_invoice, spare_parts, "
    "certifications_compliance, general_query, unknown."
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


def _llm_classify(message: str) -> tuple[str, float]:
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
        for label in INTENTS:
            if label in raw:
                return label, 0.5
        return "unknown", 0.0
