"""Nightly: delete Lumen conversation memory older than six hours from every session."""
from django.core.management.base import BaseCommand

from compass.memory import purge_expired


class Command(BaseCommand):
    help = "Delete Lumen conversation memory older than COMPASS_SESSION_TTL_SECONDS (run nightly)."

    def handle(self, *args, **options):
        self.stdout.write(f"purged {purge_expired()} expired conversation(s)")
