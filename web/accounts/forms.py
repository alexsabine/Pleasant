from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from atlas.models import COMMUNITIES

from .models import AGE_BANDS, BUDGET, DOSAGE, HELP_KINDS, FamilyPreferences

User = get_user_model()


class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text="Used only to sign in and, if you choose, for summaries you turn on.")
    adult = forms.BooleanField(required=True, label="I am 18 or over, and a caregiver, resident or community member (this site has no accounts for children).")

    class Meta:
        model = User
        fields = ("username", "email")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            FamilyPreferences.objects.get_or_create(user=user)
        return user


class HelpForm(forms.ModelForm):
    help_kinds = forms.MultipleChoiceField(choices=HELP_KINDS, widget=forms.CheckboxSelectMultiple, required=False, label="What kind of help would be welcome?")

    class Meta:
        model = FamilyPreferences
        fields = ("display_name", "help_kinds")
        labels = {"display_name": "What should we call you? (optional)"}


class FamilyForm(forms.ModelForm):
    age_bands = forms.MultipleChoiceField(choices=AGE_BANDS, widget=forms.CheckboxSelectMultiple, required=False, label="Age bands you are looking for (not a child profile)")
    community = forms.ChoiceField(choices=[("", "Anywhere in Del Norte")] + COMMUNITIES, required=False, label="Closest community")

    class Meta:
        model = FamilyPreferences
        fields = ("age_bands", "budget", "step_free", "community")
        labels = {"budget": "Budget", "step_free": "Only places verified step-free or wheelchair accessible"}
        widgets = {"budget": forms.RadioSelect}


class QuietForm(forms.ModelForm):
    class Meta:
        model = FamilyPreferences
        fields = ("dosage", "compass_may_remember", "notifications")
        labels = {"dosage": "How much at once?", "compass_may_remember": "Crescent Compass may use these settings when I ask it something",
                  "notifications": "Send me an email summary of new verified places and events (off by default)"}
        widgets = {"dosage": forms.RadioSelect}
