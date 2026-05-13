from django.urls import path

from . import views


urlpatterns = [
    path("", views.memo_list, name="memo_list"),
    path("memos/<int:pk>/edit/", views.memo_edit, name="memo_edit"),
    path("memos/<int:pk>/done/", views.memo_done, name="memo_done"),
    path("memos/<int:pk>/delete/", views.memo_delete, name="memo_delete"),
]
