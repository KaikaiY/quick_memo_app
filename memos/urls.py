from django.urls import path

from . import views


urlpatterns = [
    path("", views.memo_list, name="memo_list"),
    path("signup/", views.signup, name="signup"),
    path("logout/", views.logout_confirm, name="logout_confirm"),
    path("review/", views.nightly_review, name="nightly_review"),
    path("memos/<int:pk>/edit/", views.memo_edit, name="memo_edit"),
    path("memos/<int:pk>/done/", views.memo_done, name="memo_done"),
    path("memos/<int:pk>/delete/", views.memo_delete, name="memo_delete"),
]
