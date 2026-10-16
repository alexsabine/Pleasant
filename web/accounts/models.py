"""Onboarding and personal settings: adult-directed, optional, revocable.

Proposal cross-reference: five voluntary stages (arrive, orient, settle,
contribute, steward) are participation CHOICES, not a trust score; no child
accounts, no child profiles, no location tracking; quiet is a real choice.
Kim's brief: contributor role with moderated submissions; two independent admins.
Kit rule 8: user-controlled attention, optional personal settings.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

AGE_BANDS = [("0_2", "Babies and toddlers (0 to 2)"), ("3_5", "Preschool (3 to 5)"), ("6_11", "Primary (6 to 11)"), ("12_18", "Teens (12 to 18)")]
BUDGET = [("free", "Free things only"), ("low", "Free or low cost"), ("any", "Any cost")]
DOSAGE = [("few", "A few suggestions"), ("standard", "A standard shortlist"), ("all", "Show me everything")]
HELP_KINDS = [("family", "Family support"), ("orientation", "Local orientation"), ("events", "Community events"), ("practical", "Practical guidance")]
STAGES = [("explore", "Explore"), ("choose", "Choose"), ("settle", "Settle"), ("contribute", "Contribute"), ("steward", "Steward")]


class FamilyPreferences(models.Model):
    """Explicit adult choices. Nothing here identifies a child."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="family_prefs")
    display_name = models.CharField(max_length=60, blank=True)
    help_kinds = models.JSONField(default=list, blank=True)          # subset of HELP_KINDS keys
    age_bands = models.JSONField(default=list, blank=True)           # subset of AGE_BANDS keys
    budget = models.CharField(max_length=8, choices=BUDGET, default="low")
    step_free = models.BooleanField(default=False, help_text="Only show places verified step-free / wheelchair accessible")
    community = models.CharField(max_length=32, blank=True)
    dosage = models.CharField(max_length=8, choices=DOSAGE, default="standard")
    compass_may_remember = models.BooleanField(default=True, help_text="Let Lumen use these settings when answering")
    notifications = models.BooleanField(default=False, help_text="Email summaries (off unless you turn them on)")
    onboarding_done = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Preferences for {self.user.get_username()}"

    @property
    def stage(self) -> str:
        """The participation stage currently available to this person: a description of
        rights they hold, never a score."""
        u = self.user
        if u.is_superuser or u.groups.filter(name="Moderators").exists():
            return "steward"
        if u.groups.filter(name__in=["Editors", "Contributors"]).exists():
            return "contribute"
        if self.onboarding_done:
            return "settle"
        return "choose"

    @property
    def age_band_labels(self) -> list[str]:
        return [dict(AGE_BANDS).get(b, b) for b in self.age_bands]

    @property
    def help_kind_labels(self) -> list[str]:
        return [dict(HELP_KINDS).get(k, k) for k in self.help_kinds]

    def age_filter(self) -> tuple[int, int] | None:
        """Widest age span covered by the chosen bands, or None."""
        spans = {"0_2": (0, 2), "3_5": (3, 5), "6_11": (6, 11), "12_18": (12, 18)}
        picked = [spans[b] for b in self.age_bands if b in spans]
        if not picked:
            return None
        return min(p[0] for p in picked), max(p[1] for p in picked)

    def max_items(self) -> int:
        return {"few": 2, "standard": 4, "all": 8}[self.dosage]


class SavedPlace(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_places")
    resource = models.ForeignKey("atlas.Resource", on_delete=models.CASCADE, related_name="saved_by")
    note = models.CharField(max_length=300, blank=True, help_text="Private, only visible to you")
    saved_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("user", "resource")]
        ordering = ["-saved_at"]

    def __str__(self):
        return f"{self.user.get_username()} saved {self.resource.name}"


STEWARD_AGREEMENT_VERSION = "2026-10"


def is_steward(user) -> bool:
    return bool(user and user.is_authenticated and (user.is_superuser or user.groups.filter(name="Moderators").exists()))


class StewardAgreement(models.Model):
    """A steward's signed agreement, one row per version signed. Stewards' map instructions to Lumen
    are recorded only while they hold a signature for the current version."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="steward_agreements")
    version = models.CharField(max_length=16)
    signed_name = models.CharField(max_length=120)
    signed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-signed_at"]
        unique_together = [("user", "version")]

    def __str__(self):
        return f"{self.signed_name} signed steward agreement {self.version}"

    @classmethod
    def current_for(cls, user):
        if not (user and user.is_authenticated):
            return None
        return cls.objects.filter(user=user, version=STEWARD_AGREEMENT_VERSION).first()
