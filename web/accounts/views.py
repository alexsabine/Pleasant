"""Gentle onboarding: browse without an account; join if you want to save places,
set preferences or contribute. Every step is skippable and reversible."""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from atlas.models import AuditEntry, Resource, Submission

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
        AuditEntry.append({"event": "account_created", "user": user.get_username(), "timestamp": timezone.now().isoformat()})
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
    AuditEntry.append({"event": "role_requested", "user": request.user.get_username(), "role": "Contributors", "timestamp": timezone.now().isoformat()})
    messages.info(request, "Thanks. A steward will review your request; nothing changes until they do.")
    return redirect("accounts:my_atlas")
