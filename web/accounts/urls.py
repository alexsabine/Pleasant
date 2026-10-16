from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "accounts"
urlpatterns = [
    path("join/", views.signup, name="signup"),
    path("sign-in/", auth_views.LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("sign-out/", auth_views.LogoutView.as_view(), name="logout"),
    path("welcome/", views.welcome, name="welcome"),
    path("welcome/<int:step>/", views.welcome, name="welcome_step"),
    path("my-atlas/", views.my_atlas, name="my_atlas"),
    path("save/<int:resource_id>/", views.toggle_saved, name="toggle_saved"),
    path("my-data/", views.download_my_data, name="my_data"),
    path("delete/", views.delete_account, name="delete_account"),
    path("request-contributor/", views.request_contributor, name="request_contributor"),
]
