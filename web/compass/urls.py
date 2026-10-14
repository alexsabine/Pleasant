from django.urls import path

from . import views

app_name = "compass"
urlpatterns = [
    path("", views.panel, name="panel"),
    path("ask", views.ask, name="ask"),
]
