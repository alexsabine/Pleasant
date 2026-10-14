"""Publishing writes an audit entry and bumps the projection version so every
derived cache (pin GeoJSON, Compass working context) is invalidated."""
from django.dispatch import receiver
from django.utils import timezone
from wagtail.signals import published, unpublished

from .models import AuditEntry, Event, ProjectionVersion, Resource


def _record(event_name, instance, **kwargs):
    version = ProjectionVersion.bump()
    AuditEntry.append({
        "event": event_name, "model": type(instance).__name__, "object_id": instance.pk,
        "name": getattr(instance, "name", getattr(instance, "title", "")),
        "revision_id": getattr(getattr(instance, "latest_revision", None), "pk", None),
        "projection_version": version, "timestamp": timezone.now().isoformat(),
    })


@receiver(published, sender=Resource)
@receiver(published, sender=Event)
def on_published(sender, instance, **kwargs):
    _record("published", instance)


@receiver(unpublished, sender=Resource)
@receiver(unpublished, sender=Event)
def on_unpublished(sender, instance, **kwargs):
    _record("unpublished", instance)
