"""URL configuration for example app."""

from django.urls import include, path

from django_agui.api.urls import urlpatterns as api_urlpatterns

urlpatterns = [
    path("api/", include(api_urlpatterns)),
]
