"""URL routing for notifications and preferences."""

from __future__ import annotations

from django.urls import path

from apps.notifications.api.views import (
    EvaluateNotificationsTriggerView,
    NotificationListView,
    NotificationPreferenceView,
    NotificationReadAllView,
    NotificationReadView,
    NotificationUnreadCountView,
)

urlpatterns = [
    path("notifications/", NotificationListView.as_view(), name="notifications-list"),
    path(
        "notifications/<uuid:pk>/read/",
        NotificationReadView.as_view(),
        name="notification-read",
    ),
    path(
        "notifications/read-all/",
        NotificationReadAllView.as_view(),
        name="notifications-read-all",
    ),
    path(
        "notifications/unread-count/",
        NotificationUnreadCountView.as_view(),
        name="notifications-unread-count",
    ),
    path(
        "notifications/evaluate/",
        EvaluateNotificationsTriggerView.as_view(),
        name="notifications-evaluate",
    ),
    path(
        "notification-preferences/",
        NotificationPreferenceView.as_view(),
        name="notification-preferences",
    ),
]
