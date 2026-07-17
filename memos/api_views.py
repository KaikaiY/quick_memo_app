from rest_framework.authtoken.models import Token
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .api_serializers import (
    LoginSerializer,
    MemoSerializer,
    MemoUpdateSerializer,
    QuickMemoCreateSerializer,
    UserSerializer,
)
from .models import Memo


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _created = Token.objects.get_or_create(user=user)
        return Response(
            {
                "token": token.key,
                "user": UserSerializer(user).data,
            }
        )


class LogoutView(APIView):
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class MemoViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        queryset = Memo.objects.filter(user=self.request.user).exclude(status="trash")
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            return QuickMemoCreateSerializer
        if self.action in {"update", "partial_update"}:
            return MemoUpdateSerializer
        return MemoSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        memo = serializer.save()
        return Response(MemoSerializer(memo).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        memo = self.get_object()
        serializer = self.get_serializer(memo, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        memo = serializer.save()
        return Response(MemoSerializer(memo).data)

    @action(detail=True, methods=["post"])
    def done(self, request, pk=None):
        memo = self.get_object()
        services.complete_memo(memo)
        return Response(MemoSerializer(memo).data)

    @action(detail=True, methods=["post"])
    def delete(self, request, pk=None):
        memo = self.get_object()
        services.trash_memo(memo)
        return Response(MemoSerializer(memo).data)
