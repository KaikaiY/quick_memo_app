from django import forms

from .models import Memo


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
