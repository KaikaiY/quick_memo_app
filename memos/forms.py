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


class ReparseMemoForm(forms.Form):
    reparse_text = forms.CharField(
        label="一文で再解析",
        max_length=255,
        widget=forms.TextInput(
            attrs={
                "placeholder": "例: !高 明日 病院",
                "aria-label": "一文で再解析",
            }
        ),
    )


class MemoForm(forms.ModelForm):
    status = forms.ChoiceField(
        choices=[choice for choice in Memo.STATUS_CHOICES if choice[0] not in {"done", "trash"}],
        label="状態",
    )
    reminder_at = forms.DateTimeField(
        required=False,
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        label="リマインダー",
    )

    class Meta:
        model = Memo
        fields = ["content", "priority", "status", "reminder_at"]
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
            "priority": "優先度",
        }
