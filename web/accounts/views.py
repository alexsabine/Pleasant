"""Gentle onboarding: browse without an account; join if you want to save places,
set preferences or contribute. Every step is skippable and reversible."""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from atlas.models import AuditEntry, Resource, Submission, member_ref

from .forms import FamilyForm, HelpForm, QuietForm, SignupForm
from .models import STAGES, FamilyPreferences, SavedPlace

STEP_FORMS = {1: HelpForm, 2: FamilyForm, 3: QuietForm}
STEP_TITLES = {1: "What kind of help would be welcome?", 2: "For my family", 3: "How much, and how quietly"}


def signup(request):
    if request.user.is_authenticated:
        return redirect("accounts:my_atlas")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        AuditEntry.append({"event": "account_created", "user": member_ref(user), "timestamp": timezone.now().isoformat()})
        return redirect("accounts:welcome_step", step=1)
    return render(request, "accounts/signup.html", {"form": form})


@login_required
def welcome(request, step: int = 1):
    prefs, _ = FamilyPreferences.objects.get_or_create(user=request.user)
    step = max(1, min(3, step))
    Form = STEP_FORMS[step]
    if request.method == "POST":
        if "skip" in request.POST:
            return _advance(request, prefs, step)
        form = Form(request.POST, instance=prefs)
        if form.is_valid():
            form.save()
            return _advance(request, prefs, step)
    else:
        form = Form(instance=prefs)
    return render(request, "accounts/welcome.html", {"form": form, "step": step, "title": STEP_TITLES[step], "total": 3})


def _advance(request, prefs, step):
    if step >= 3:
        prefs.onboarding_done = True
        prefs.save()
        messages.success(request, "Welcome. You can change any of this at any time from My atlas.")
        return redirect("accounts:my_atlas")
    return redirect("accounts:welcome_step", step=step + 1)


@login_required
def my_atlas(request):
    prefs, _ = FamilyPreferences.objects.get_or_create(user=request.user)
    saved = SavedPlace.objects.filter(user=request.user).select_related("resource")
    pending = Submission.objects.filter(submitter=request.user).order_by("-submitted_at")[:10]
    stages = [{"key": k, "label": v, "current": k == prefs.stage} for k, v in STAGES]
    return render(request, "accounts/my_atlas.html", {"prefs": prefs, "saved": saved, "pending": pending, "stages": stages})


@login_required
@require_POST
def toggle_saved(request, resource_id):
    r = get_object_or_404(Resource, pk=resource_id, live=True, visibility="public")
    obj, created = SavedPlace.objects.get_or_create(user=request.user, resource=r)
    if not created:
        obj.delete()
    nxt = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/explore/"
    return redirect(nxt)


@login_required
@require_POST
def request_contributor(request):
    """Asking for contributor rights is a moderated submission; a steward grants it. Never automatic."""
    Submission.objects.create(submitter=request.user, proposed_payload={"attribute": "role_request", "role": "Contributors",
                                                                        "note": request.POST.get("note", "")[:300]})
    AuditEntry.append({"event": "role_requested", "user": member_ref(request.user), "role": "Contributors", "timestamp": timezone.now().isoformat()})
    messages.info(request, "Thanks. A steward will review your request; nothing changes until they do.")
    return redirect("accounts:my_atlas")


@login_required
def download_my_data(request):
    """Everything we hold about the signed-in person, as one file."""
    u = request.user
    prefs = FamilyPreferences.objects.filter(user=u).first()
    data = {
        "account": {"username": u.get_username(), "email": u.email, "joined": u.date_joined.isoformat(),
                    "last_sign_in": u.last_login.isoformat() if u.last_login else None, "log_reference": member_ref(u)},
        "settings": {f: getattr(prefs, f) for f in ("display_name", "help_kinds", "age_bands", "budget", "step_free", "community",
                                                    "dosage", "compass_may_remember", "notifications")} if prefs else {},
        "saved_places": [{"place": s.resource.name, "note": s.note, "saved_at": s.saved_at.isoformat()}
                         for s in SavedPlace.objects.filter(user=u).select_related("resource")],
        "suggestions": [{"submitted_at": s.submitted_at.isoformat(), "status": s.status, "details": s.proposed_payload}
                        for s in Submission.objects.filter(submitter=u)],
        "note": "Lumen keeps the current conversation in your session for up to 6 hours. The log records what Lumen showed, not what you typed, and refers to you only by your log reference.",
    }
    resp = JsonResponse(data, json_dumps_params={"indent": 2})
    resp["Content-Disposition"] = 'attachment; filename="crescent-compass-my-data.json"'
    return resp


@login_required
@require_POST
def delete_account(request):
    """Delete the account, settings, saved places and unreviewed suggestions. Reviewed
    suggestions stay with no name attached; the log only ever held a member number."""
    if request.POST.get("confirm", "").strip().lower() != "delete":
        messages.info(request, 'Nothing was deleted. Type "delete" in the box to confirm.')
        return redirect("accounts:my_atlas")
    u = request.user
    Submission.objects.filter(submitter=u, status__in=["pending", "needs_clarification"]).delete()
    ref = member_ref(u)
    logout(request)
    u.delete()
    AuditEntry.append({"event": "account_deleted", "user": ref, "timestamp": timezone.now().isoformat()})
    messages.success(request, "Your account and everything linked to it have been deleted.")
    return redirect("/")
