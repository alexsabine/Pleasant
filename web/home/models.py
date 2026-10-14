from django.db import models
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page


class HomePage(Page):
    """Owner-editable home page: hero copy, one optional question, intro."""
    strapline = models.CharField(max_length=160, default="Things to do with kids in Del Norte County", blank=True)
    intro = RichTextField(blank=True)
    optional_question = models.CharField(max_length=120, default="Just show free things?", blank=True)

    content_panels = Page.content_panels + [FieldPanel("strapline"), FieldPanel("intro"), FieldPanel("optional_question")]
    template = "home/home_page.html"
    max_count = 1

    def get_context(self, request, *args, **kwargs):
        from atlas.models import Event, Resource
        from django.utils import timezone
        ctx = super().get_context(request, *args, **kwargs)
        ctx["featured"] = Resource.objects.filter(live=True, visibility="public").order_by("-last_verified_at")[:4]
        ctx["upcoming"] = Event.objects.filter(live=True, start_at__gte=timezone.now()).order_by("start_at")[:3]
        return ctx
