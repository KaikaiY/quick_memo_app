from django.urls import path
from rest_framework.routers import DefaultRouter

from .api_views import LoginView, LogoutView, MeView, MemoViewSet


router = DefaultRouter()
router.register("memos", MemoViewSet, basename="api_memo")

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="api_login"),
    path("auth/logout/", LogoutView.as_view(), name="api_logout"),
    path("auth/me/", MeView.as_view(), name="api_me"),
]
urlpatterns += router.urls
