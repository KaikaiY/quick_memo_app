from django.contrib import admin

from .models import GoogleCalendarCredential, Memo


@admin.register(Memo)
class MemoAdmin(admin.ModelAdmin):
    list_display = (
        "content",
        "priority",
        "status",
        "reminder_at",
        "google_event_id",
        "google_synced_at",
        "created_at",
    )
    list_filter = ("category", "priority", "status")
    search_fields = ("content",)


@admin.register(GoogleCalendarCredential)
class GoogleCalendarCredentialAdmin(admin.ModelAdmin):
    list_display = ("user", "calendar_id", "connected_at", "updated_at")
    search_fields = ("user__username", "calendar_id")
