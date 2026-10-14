from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls

from atlas import views as atlas_views

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("explore/", atlas_views.explore, name="explore"),
    path("this-week/", atlas_views.this_week, name="this_week"),
    path("local-help/", atlas_views.local_help, name="local_help"),
    path("about/", atlas_views.about, name="about"),
    path("resource/<slug:slug>/", atlas_views.resource_detail, name="resource_detail"),
    path("api/resources.json", atlas_views.api_resources, name="api_resources"),
    path("api/resources.geojson", atlas_views.api_resources_geojson, name="api_resources_geojson"),
    path("api/events.json", atlas_views.api_events, name="api_events"),
    path("api/h3.geojson", atlas_views.api_h3_aggregate, name="api_h3"),
    path("api/manifest.json", atlas_views.api_manifest, name="api_manifest"),
    path("api/boundaries/<slug:name>.geojson", atlas_views.api_boundary, name="api_boundary"),
    path("tiles/<slug:name>.pmtiles", atlas_views.serve_pmtiles, name="serve_pmtiles"),
    path("compass/", include("compass.urls")),
    path("", include(wagtail_urls)),
]
if settings.DEBUG:
    urlpatterns = static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + urlpatterns
