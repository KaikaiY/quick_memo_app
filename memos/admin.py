from django.contrib import admin

from .models import Memo


@admin.register(Memo)
class MemoAdmin(admin.ModelAdmin):
    list_display = ("content", "category", "priority", "status", "reminder_at", "created_at")
    list_filter = ("category", "priority", "status")
    search_fields = ("content",)
