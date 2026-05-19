from django import forms

from .models import Memo


class QuickMemoForm(forms.Form):
    text = forms.CharField(
        label="メモ",
        max_length=255,
        widget=forms.TextInput(
            attrs={
                "autofocus": True,
                "placeholder": "例: 明日の朝にゴミ出し",
                "aria-label": "メモ内容",
            }
        ),
    )


class MemoForm(forms.ModelForm):
    reminder_at = forms.DateTimeField(
        required=False,
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        label="リマインダー",
    )

    class Meta:
        model = Memo
        fields = ["content", "category", "priority", "status", "reminder_at"]
        widgets = {
            "content": forms.TextInput(
                attrs={
                    "autofocus": True,
                    "placeholder": "今すぐメモする",
                    "aria-label": "メモ内容",
                }
            ),
        }
        labels = {
            "content": "メモ",
            "category": "カテゴリ",
            "priority": "優先度",
            "status": "状態",
        }
