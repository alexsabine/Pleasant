"""Optional Claude phrasing/intent adapter for Crescent Compass.

Off by default (COMPASS_LLM_ENABLED=0). When on, the model does two narrow,
schema-constrained jobs and nothing else:
1. extract_intent: turn the question into the Intent schema (no retrieval).
2. phrase: rewrite the deterministic answer as friendlier sentences, each
   tagged with the record ids it relies on, which honesty.py then validates.
The model never sees private claims, never calls tools, never writes.
Any failure falls back to the deterministic path and is recorded.
"""
from __future__ import annotations

import json
import logging

from django.conf import settings

log = logging.getLogger(__name__)

INTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "age": {"type": ["integer", "null"]},
        "free_only": {"type": "boolean"},
        "max_cost": {"type": ["number", "null"]},
        "requires_accessibility": {"type": "boolean"},
        "categories": {"type": "array", "items": {"type": "string", "enum": [
            "playground", "indoor_play", "library", "trail", "class", "sport", "arts", "family_service", "health", "food", "childcare", "event_venue"]}},
        "community": {"type": ["string", "null"], "enum": ["crescent_city", "smith_river", "gasquet", "klamath", "fort_dick", "hiouchi", "countywide", None]},
        "wants_events": {"type": "boolean"},
    },
    "required": ["age", "free_only", "max_cost", "requires_accessibility", "categories", "community", "wants_events"],
    "additionalProperties": False,
}
PHRASE_SCHEMA = {
    "type": "object",
    "properties": {"sentences": {"type": "array", "items": {
        "type": "object",
        "properties": {"text": {"type": "string"}, "resource_ids": {"type": "array", "items": {"type": "integer"}}},
        "required": ["text", "resource_ids"], "additionalProperties": False}}},
    "required": ["sentences"], "additionalProperties": False,
}
SYSTEM = ("You are Crescent Compass, a quiet guide to a verified family-resources directory for Del Norte County. "
          "You only restate facts present in the JSON records you are given. You never add places, hours, prices, "
          "or accessibility claims that are not in the records, and you say 'access unknown' when the record says unknown. "
          "Warm, brief, plain language. Do not give medical, legal or emergency advice.")


def enabled() -> bool:
    return bool(settings.COMPASS_LLM_ENABLED)


def _client():
    import anthropic
    return anthropic.Anthropic()


def _json_text(response) -> dict | None:
    if response.stop_reason == "refusal":
        log.warning("compass: model refused (%s)", getattr(response.stop_details, "category", None))
        return None
    text = next((b.text for b in response.content if b.type == "text"), None)
    return json.loads(text) if text else None


def extract_intent(question: str) -> dict | None:
    if not enabled():
        return None
    try:
        client = _client()
        resp = client.beta.messages.create(
            model=settings.COMPASS_MODEL, max_tokens=512,
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",
            system=SYSTEM + " Extract the family's request as JSON. Unknown fields are null/false/empty.",
            messages=[{"role": "user", "content": question[:1000]}],
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": INTENT_SCHEMA}},
        )
        return _json_text(resp)
    except Exception as e:  # any API error: deterministic path continues
        log.warning("compass: intent extraction failed: %s", e)
        return None


def phrase(question: str, decision_payload: dict) -> list[dict] | None:
    if not enabled():
        return None
    try:
        client = _client()
        resp = client.beta.messages.create(
            model=settings.COMPASS_MODEL, max_tokens=settings.COMPASS_MAX_TOKENS,
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",
            system=SYSTEM + " Rewrite the answer as short sentences. Tag every sentence with the ids of the records it uses. "
                            "A sentence with no record must contain no factual claim about any place.",
            messages=[{"role": "user", "content": json.dumps({"question": question[:1000], "answer": decision_payload})}],
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": PHRASE_SCHEMA}},
        )
        data = _json_text(resp)
        return data["sentences"] if data else None
    except Exception as e:
        log.warning("compass: phrasing failed: %s", e)
        return None
