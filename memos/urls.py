from django.urls import path

from . import views


urlpatterns = [
    path("", views.memo_list, name="memo_list"),
    path("signup/", views.signup, name="signup"),
    path("logout/", views.logout_confirm, name="logout_confirm"),
    path("google-calendar/", views.google_calendar_settings, name="google_calendar_settings"),
    path("google-calendar/connect/", views.google_calendar_connect, name="google_calendar_connect"),
    path("google-calendar/callback/", views.google_calendar_callback, name="google_calendar_callback"),
    path("google-calendar/disconnect/", views.google_calendar_disconnect, name="google_calendar_disconnect"),
    path("review/", views.nightly_review, name="nightly_review"),
    path("memos/<int:pk>/edit/", views.memo_edit, name="memo_edit"),
    path("memos/<int:pk>/google-calendar/", views.memo_google_calendar_sync, name="memo_google_calendar_sync"),
    path("memos/<int:pk>/done/", views.memo_done, name="memo_done"),
    path("memos/<int:pk>/delete/", views.memo_delete, name="memo_delete"),
]
