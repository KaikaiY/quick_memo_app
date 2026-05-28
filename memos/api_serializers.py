from django.contrib.auth import authenticate
from rest_framework import serializers

from .models import Memo
from .parser import parse_quick_memo


ACTIVE_STATUS_CHOICES = [
    (value, label)
    for value, label in Memo.STATUS_CHOICES
    if value not in {"done", "trash"}
]


class MemoSerializer(serializers.ModelSerializer):
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    is_done = serializers.BooleanField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    is_synced_to_google = serializers.BooleanField(read_only=True)

    class Meta:
        model = Memo
        fields = [
            "id",
            "content",
            "category",
            "priority",
            "priority_display",
            "status",
            "status_display",
            "reminder_at",
            "completed_at",
            "is_done",
            "is_overdue",
            "google_event_link",
            "google_synced_at",
            "is_synced_to_google",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class QuickMemoCreateSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=255, trim_whitespace=True)

    def validate_text(self, value):
        if not value.strip():
            raise serializers.ValidationError("メモを入力してください。")
        return value

    def create(self, validated_data):
        parsed_memo = parse_quick_memo(validated_data["text"])
        return Memo.objects.create(
            user=self.context["request"].user,
            content=parsed_memo.content,
            reminder_at=parsed_memo.reminder_at,
            category="other",
            priority=parsed_memo.priority,
            status="today" if parsed_memo.reminder_at else "inbox",
        )


class MemoUpdateSerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(choices=ACTIVE_STATUS_CHOICES, required=False)

    class Meta:
        model = Memo
        fields = [
            "content",
            "priority",
            "status",
            "reminder_at",
        ]
        extra_kwargs = {
            "content": {"required": False},
            "priority": {"required": False},
            "reminder_at": {"required": False, "allow_null": True},
        }

    def validate_content(self, value):
        if not value.strip():
            raise serializers.ValidationError("メモを入力してください。")
        return value


class UserSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False, write_only=True)

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            username=attrs["username"],
            password=attrs["password"],
        )
        if not user:
            raise serializers.ValidationError("ユーザー名またはパスワードが違います。")
        attrs["user"] = user
        return attrs
