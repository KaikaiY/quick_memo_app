from django.db import models
from django.contrib.auth.models import User


class Memo(models.Model):
    CATEGORY_CHOICES = [
        ("task", "やること"),
        ("buy", "買うもの"),
        ("research", "調べる"),
        ("contact", "連絡"),
        ("idea", "アイデア"),
        ("worry", "不安"),
        ("other", "その他"),
    ]

    PRIORITY_CHOICES = [
        ("high", "高"),
        ("middle", "中"),
        ("low", "低"),
        ("unset", "未設定"),
    ]

    STATUS_CHOICES = [
        ("inbox", "未整理"),
        ("today", "今日やる"),
        ("week", "今週やる"),
        ("someday", "いつか"),
        ("done", "完了"),
        ("trash", "捨てる"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="other")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="unset")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="inbox")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.content