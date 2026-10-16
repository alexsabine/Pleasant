"""Compass working memory: bounded, lossy by design, never a source of facts.

Four-layer rule (architecture/02): evidence and claims live in the database;
the published projection is the only thing Compass reads; this module holds
the per-session WORKING CONTEXT, which is:
- a short list of recent turns (question, parsed intent, record ids shown),
- a compact preference summary (age, budget, access need) with timestamps,
- the projection version it was built against.
It is invalidated when the projection version changes, expires after a TTL,
is never written back to any record, and stores no record text.
"""
from __future__ import annotations

import time

KEY = "compass_ctx"
DEFAULTS = {"COMPASS_WORKING_CONTEXT_TURNS": 6, "COMPASS_SESSION_TTL_SECONDS": 6 * 3600}


def _setting(name):
    try:
        from django.conf import settings
        return getattr(settings, name, DEFAULTS[name])
    except Exception:  # not running under Django (reference checks)
        return DEFAULTS[name]


def _touch(session):
    if hasattr(session, "modified"):
        session.modified = True


def load(session, projection_version: int) -> dict:
    ctx = session.get(KEY) or {}
    now = time.time()
    if not ctx or ctx.get("projection_version") != projection_version or now - ctx.get("updated", 0) > _setting("COMPASS_SESSION_TTL_SECONDS"):
        ctx = {"projection_version": projection_version, "turns": [], "prefs": {}, "created": now, "updated": now,
               "invalidated_from": ctx.get("projection_version") if ctx else None}
    return ctx


def remember(session, ctx: dict, question: str, intent: dict, shown_ids: list[int], action: str) -> dict:
    ctx["turns"].append({"q": question[:200], "intent": intent, "shown": shown_ids, "action": action, "t": time.time()})
    # Compaction: keep the last N turns verbatim; older turns fold into prefs
    # (exponential-summary style, but of preferences, never of facts).
    while len(ctx["turns"]) > _setting("COMPASS_WORKING_CONTEXT_TURNS"):
        old = ctx["turns"].pop(0)
        for k in ("age", "free_only", "max_cost", "requires_accessibility", "community"):
            v = old["intent"].get(k)
            if v not in (None, False, [], ""):
                ctx["prefs"][k] = {"value": v, "t": old["t"]}
    ctx["updated"] = time.time()
    session[KEY] = ctx
    _touch(session)
    return ctx


def carry_forward(ctx: dict, intent) -> list[str]:
    """Fill missing intent fields from remembered preferences; report what was used."""
    used = []
    recent = list(reversed(ctx.get("turns", [])))
    for k in ("age", "free_only", "max_cost", "requires_accessibility", "community"):
        if getattr(intent, k) in (None, False):
            for t in recent:
                v = t["intent"].get(k)
                if v not in (None, False, [], ""):
                    setattr(intent, k, v)
                    used.append(f"{k} from an earlier question in this session")
                    break
            else:
                p = ctx.get("prefs", {}).get(k)
                if p:
                    setattr(intent, k, p["value"])
                    used.append(f"{k} from your earlier preference this session")
    return used


def forget(session) -> None:
    session.pop(KEY, None)
    _touch(session)


def purge_expired(now: float | None = None) -> int:
    """Delete conversation memory older than the TTL from every stored session (run nightly), so a
    conversation is never kept longer than promised, even if the person never comes back."""
    from django.contrib.sessions.backends.db import SessionStore
    from django.contrib.sessions.models import Session
    now = time.time() if now is None else now
    ttl = _setting("COMPASS_SESSION_TTL_SECONDS")
    purged = 0
    for row in Session.objects.all():
        ctx = row.get_decoded().get(KEY)
        if ctx and now - ctx.get("updated", 0) > ttl:
            store = SessionStore(session_key=row.session_key)
            store.pop(KEY, None)
            store.save()
            purged += 1
    return purged
