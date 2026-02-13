"""URL configuration for playground example app."""

from django.urls import include, path
from django.views.generic import TemplateView

from django_agui.api.urls import urlpatterns as api_urlpatterns
from example_app.playground.views import (
    playground_config,
    threads_list,
    thread_detail,
)

urlpatterns = [
    path("api/", include(api_urlpatterns)),
    path("api/playground/config/", playground_config, name="playground-config"),
    path("api/playground/threads/", threads_list, name="threads-list"),
    path(
        "api/playground/threads/<str:thread_id>/", thread_detail, name="thread-detail"
    ),
    path("", TemplateView.as_view(template_name="playground.html"), name="playground"),
]
