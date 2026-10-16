"""Django settings for the Pleasant Crescent web platform (first iteration).

Development defaults use SpatiaLite so the vertical slice runs anywhere; staging
and production use PostGIS (set DATABASE_URL-style env vars below). Secrets come
from the environment only. See design/backend_system.md.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent          # web/
REPO_ROOT = BASE_DIR.parent                                 # repository root
sys.path.insert(0, str(REPO_ROOT / "backend"))             # makes `pc_core` importable

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [h for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h]
CSRF_TRUSTED_ORIGINS = [o for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o]

INSTALLED_APPS = [
    "home",
    "accounts",
    "atlas",
    "compass",
    "wagtail.contrib.settings",
    "wagtail.embeds",
    "wagtail.sites",
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail",
    "modelcluster",
    "taggit",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "pleasant.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
        "wagtail.contrib.settings.context_processors.settings",
        "atlas.context_processors.site_tokens",
        "atlas.context_processors.living_logo",
    ]},
}]
WSGI_APPLICATION = "pleasant.wsgi.application"

if os.environ.get("POSTGRES_HOST"):
    DATABASES = {"default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": os.environ.get("POSTGRES_DB", "pleasant_crescent"),
        "USER": os.environ.get("POSTGRES_USER", "pleasant_dev"),
        "PASSWORD": os.environ["POSTGRES_PASSWORD"],
        "HOST": os.environ["POSTGRES_HOST"],
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }}
else:
    DATABASES = {"default": {
        "ENGINE": "django.contrib.gis.db.backends.spatialite",
        "NAME": os.environ.get("SQLITE_PATH", str(BASE_DIR / "db.sqlite3")),
    }}
SPATIALITE_LIBRARY_PATH = os.environ.get("SPATIALITE_LIBRARY_PATH", "mod_spatialite.so")

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Los_Angeles"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SESSION_COOKIE_SAMESITE = "Lax"
X_FRAME_OPTIONS = "SAMEORIGIN"

# --- Wagtail ---------------------------------------------------------------
WAGTAIL_SITE_NAME = "Crescent Compass"
WAGTAILADMIN_BASE_URL = os.environ.get("WAGTAILADMIN_BASE_URL", "http://localhost:8000")
WAGTAILSEARCH_BACKENDS = {"default": {"BACKEND": "wagtail.search.backends.database"}}
WAGTAILDOCS_EXTENSIONS = ["pdf", "txt", "csv"]
WAGTAILIMAGES_EXTENSIONS = ["jpg", "jpeg", "png", "webp"]
WAGTAILIMAGES_MAX_UPLOAD_SIZE = 10 * 1024 * 1024
WAGTAIL_GRAVATAR_PROVIDER_URL = None      # no third-party avatar requests from the admin
WAGTAIL_ENABLE_UPDATE_CHECK = False       # no version-check call to releases.wagtail.org
# EXIF is stripped from every public rendition by Wagtail/Pillow renditions; originals stay private.

# --- Pleasant Crescent -----------------------------------------------------
TILES_DIR = Path(os.environ.get("PC_TILES_DIR", REPO_ROOT / "data" / "tiles"))
BOUNDARIES_DIR = REPO_ROOT / "data" / "boundaries"
INGEST_LOG = REPO_ROOT / "data" / "ingest_log.json"
LAYER_MANIFEST = REPO_ROOT / "data" / "layer_manifest.json"
PC_PRIVATE_MODE = os.environ.get("PC_PRIVATE_MODE", "1") == "1"   # first iteration is private
PC_MAP_CENTER = [-124.195, 41.755]
PC_MAP_ZOOM = 12.2
PC_STATIC_BASE = os.environ.get("PC_STATIC_BASE", "/Pleasant/")   # path prefix of the static (GitHub Pages) export
PC_REVIEW_EMAIL = os.environ.get("PC_REVIEW_EMAIL", "")            # where static-preview review replies are addressed (optional)

# Crescent Compass agent: read-only, allow-listed tools, feature-flagged LLM.
COMPASS_LLM_ENABLED = os.environ.get("COMPASS_LLM_ENABLED", "0") == "1"
COMPASS_MODEL = os.environ.get("COMPASS_MODEL", "claude-opus-5-5")
COMPASS_MAX_TOKENS = int(os.environ.get("COMPASS_MAX_TOKENS", "2000"))
COMPASS_DAILY_REQUEST_BUDGET = int(os.environ.get("COMPASS_DAILY_REQUEST_BUDGET", "200"))
COMPASS_UTILITIES = {"show_true": 1.0, "show_false": -3.0, "abstain": 0.0}
COMPASS_WORKING_CONTEXT_TURNS = 6
COMPASS_SESSION_TTL_SECONDS = 60 * 60 * 6   # Lumen's conversation memory; purged nightly by purge_lumen_memory

LOGGING = {
    "version": 1, "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO")},
}

LOGIN_URL = "/accounts/sign-in/"
LOGIN_REDIRECT_URL = "/accounts/my-atlas/"
LOGOUT_REDIRECT_URL = "/"
