"""URL configuration for django-agui API."""

from django.urls import path

from django_agui.api.views import AgentListView, AgentRestView, AgentStreamView

urlpatterns = [
    path("agents/", AgentListView.as_view(), name="agent-list"),
    path("agents/<str:agent_name>/", AgentStreamView.as_view(), name="agent-run"),
    path(
        "agents/<str:agent_name>/run/", AgentRestView.as_view(), name="agent-run-rest"
    ),
]
