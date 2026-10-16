"""Crescent Compass endpoints. POST /compass/ask is the whole agent loop:
parse -> decide (tools over the projection) -> compose -> validate -> record."""
from __future__ import annotations

import json
import re
import uuid

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from atlas.models import AuditEntry, ProjectionVersion, ReviewNote, Submission, member_ref

from .guide import QUESTIONS

from . import adapter, honesty, memory, policy
from .tools import ALLOW_LIST

POLICY_VERSION = "compass-0.1"


@require_GET
def panel(request):
    return render(request, "compass/panel.html", {})


def _budget_ok() -> bool:
    today = timezone.now().date().isoformat()
    n = AuditEntry.objects.filter(payload__policy_version=POLICY_VERSION, payload__timestamp__startswith=today).count()
    return n < settings.COMPASS_DAILY_REQUEST_BUDGET


@require_POST
def ask(request):
    try:
        body = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid JSON"}, status=400)
    question = (body.get("question") or "").strip()
    if not question:
        return JsonResponse({"error": "question required"}, status=400)
    if len(question) > 1000:
        question = question[:1000]
    request_id = str(uuid.uuid4())
    pv = ProjectionVersion.current()
    ctx = memory.load(request.session, pv)

    if question.lower().strip(" .!") in ("forget that", "forget", "clear memory", "start over"):
        memory.forget(request.session)
        return JsonResponse({"request_id": request_id, "action": "forget", "text": "Done. I have cleared what I remembered from this session.",
                             "items": [], "events": [], "provenance": {"policy_version": POLICY_VERSION}})

    if not _budget_ok():
        return JsonResponse({"request_id": request_id, "action": "abstain", "text": "Lumen has reached today's request budget. Please use the Explore list.",
                             "items": [], "events": [], "provenance": {"policy_version": POLICY_VERSION}}, status=429)

    # 1. intent: rules first; LLM extraction only replaces fields it fills.
    intent = policy.parse_intent_rules(question)
    intent.text = question
    llm_intent = adapter.extract_intent(question)
    if llm_intent:
        for k, v in llm_intent.items():
            if v not in (None, False, [], "") and hasattr(intent, k):
                setattr(intent, k, v)
        intent.source = "llm+rules"
    used = memory.carry_forward(ctx, intent)
    max_items = 4
    if request.user.is_authenticated:
        prefs = getattr(request.user, "family_prefs", None)
        if prefs and prefs.compass_may_remember:
            span = prefs.age_filter()
            if intent.age is None and span:
                intent.age_span = span
                used.append("age bands from your saved settings")
            if not intent.free_only and prefs.budget == "free":
                intent.free_only = True
                used.append("free-only from your saved settings")
            if not intent.requires_accessibility and prefs.step_free:
                intent.requires_accessibility = True
                used.append("step-free from your saved settings")
            if not intent.community and prefs.community:
                intent.community = prefs.community
                used.append("community from your saved settings")
            max_items = prefs.max_items()

    # PREPARE (proposal p.6): a signed-in person can ask Lumen to draft a suggestion or
    # correction. It becomes a pending Submission for a steward; it never publishes.
    m_prep = re.match(r"^\s*(suggest|correct|report)\b[:\s]+(.{8,})$", question, re.I)
    if m_prep and request.user.is_authenticated:
        sub = Submission.objects.create(submitter=request.user, proposed_payload={"attribute": "correction" if m_prep.group(1).lower() != "suggest" else "suggestion",
                                                                                 "details": m_prep.group(2)[:1000], "via": "compass"})
        record = AuditEntry.append({
            "request_id": request_id, "retrieval_sources": [], "source_versions": {"projection_version": pv}, "policy_version": POLICY_VERSION,
            "assumptions": {"user": member_ref(request.user)}, "confidence_type": "n/a (draft prepared, not asserted)",
            "action_proposed": "prepare_submission", "user_approval": "explicit: user asked Lumen to draft it",
            "action_result": {"submission_id": sub.pk, "status": sub.status}, "timestamp": timezone.now().isoformat(),
            "limitations": ["A steward must review before anything changes publicly."]}, require_decision_fields=True)
        return JsonResponse({"request_id": request_id, "action": "prepare", "reason": "draft submission created for moderation",
                             "text": f"Drafted and sent for review (submission #{sub.pk}). A steward checks it against a source before anything changes publicly. You can see its status in My atlas.",
                             "items": [], "events": [], "provenance": {"policy_version": POLICY_VERSION, "audit_index": record.index, "audit_hash": record.hash,
                                                                        "tools": [], "allow_list": ALLOW_LIST, "llm_used": False, "memory_used": [], "limitations": ["moderated; never auto-published"]}})
    if m_prep:
        return JsonResponse({"request_id": request_id, "action": "ask", "reason": "suggestions need an account so a steward can follow up",
                             "text": "I can draft that as a suggestion for review once you are signed in (Join is free and asks nothing about children). Or use the public form under Suggest a place.",
                             "items": [], "events": [], "provenance": {"policy_version": POLICY_VERSION, "tools": [], "allow_list": ALLOW_LIST, "llm_used": False, "memory_used": []}})

    # 2. decide over the projection with the allow-listed tools.
    decision = policy.decide(intent, max_items=max_items)

    # 3. compose deterministically; optionally let the model rephrase, then validate.
    answer = honesty.compose(decision, used)
    llm_used, dropped = False, []
    if decision.action in ("show", "ask", "show_low_confidence") and adapter.enabled():
        sentences = adapter.phrase(question, {"items": decision.shown, "events": decision.events, "question": decision.question})
        if sentences:
            allowed = {d["id"]: d for d in decision.shown + decision.withheld}
            kept, dropped = honesty.validate_llm_sentences(sentences, allowed)
            if kept:
                answer["text"] = "\n".join(kept) + ("\n" + decision.question if decision.question else "")
                llm_used = True

    # 4. decision record: the eleven provenance fields, hash-chained.
    record = AuditEntry.append({
        "request_id": request_id,
        "retrieval_sources": decision.tool_calls,
        "source_versions": {"projection_version": decision.projection_version},
        "policy_version": POLICY_VERSION,
        "assumptions": {"intent": intent.as_dict(), "memory_used": used, "utilities": settings.COMPASS_UTILITIES},
        "confidence_type": "model: posterior-predictive survival per category; show test = Bayes act",
        "action_proposed": decision.action,
        "user_approval": None,
        "action_result": {"shown": [d["id"] for d in decision.shown], "withheld": [d["id"] for d in decision.withheld],
                          "events": [e["id"] for e in decision.events], "llm_used": llm_used, "sentences_dropped": dropped},
        "timestamp": timezone.now().isoformat(),
        "limitations": answer["limitations"],
    }, require_decision_fields=True)
    memory.remember(request.session, ctx, question, intent.as_dict(), [d["id"] for d in decision.shown], decision.action)

    return JsonResponse({
        "request_id": request_id, "action": decision.action, "reason": decision.reason,
        "text": answer["text"], "items": answer["items"], "withheld": answer["withheld"], "events": answer["events"],
        "question": answer["question"],
        "provenance": {"policy_version": POLICY_VERSION, "projection_version": decision.projection_version,
                       "tools": decision.tool_calls, "allow_list": ALLOW_LIST, "audit_index": record.index,
                       "audit_hash": record.hash, "llm_used": llm_used, "intent": intent.as_dict(), "memory_used": used,
                       "limitations": answer["limitations"]},
    })


@require_POST
def feedback(request):
    """Answers from the guide mode ('Help shape Lumen'). Stored as ReviewNote rows for the
    stewards, never published, never fed back into any answer. Anonymous replies are allowed
    so a reviewer need not create an account."""
    try:
        body = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid JSON"}, status=400)
    keys = {q["key"] for q in QUESTIONS}
    reviewer = (body.get("reviewer") or (request.user.get_username() if request.user.is_authenticated else "")).strip()[:80]
    saved = 0
    for a in (body.get("answers") or [])[:len(QUESTIONS)]:
        key, text = str(a.get("key", ""))[:40], (a.get("answer") or "").strip()[:4000]
        if key in keys and text:
            ReviewNote.objects.create(question_key=f"compass:{key}", reviewer=reviewer, response=text)
            saved += 1
    AuditEntry.append({"event": "compass_guide_feedback", "saved": saved, "reviewer": reviewer or None, "timestamp": timezone.now().isoformat()})
    return JsonResponse({"saved": saved})
