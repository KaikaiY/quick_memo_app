from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Memo


class MemoViewsTest(TestCase):
    def test_create_memo_from_top_page(self):
        response = self.client.post(
            reverse("memo_list"),
            {
                "content": "牛乳を買う",
                "category": "buy",
                "priority": "middle",
                "status": "today",
                "reminder_at": "2026-05-12T18:30",
            },
        )

        self.assertRedirects(response, reverse("memo_list"))
        memo = Memo.objects.get()
        self.assertEqual(memo.content, "牛乳を買う")
        self.assertEqual(memo.user.username, "default")
        self.assertEqual(memo.status, "today")
        self.assertIsNotNone(memo.reminder_at)

    def test_done_action_marks_memo_completed(self):
        user = User.objects.create_user(username="default")
        memo = Memo.objects.create(user=user, content="メールする", status="today")

        response = self.client.post(reverse("memo_done", args=[memo.pk]))

        self.assertRedirects(response, reverse("memo_list"))
        memo.refresh_from_db()
        self.assertEqual(memo.status, "done")
        self.assertIsNotNone(memo.completed_at)


class MemoModelTest(TestCase):
    def test_overdue_is_false_for_done_memo(self):
        user = User.objects.create_user(username="default")
        memo = Memo.objects.create(
            user=user,
            content="支払い",
            status="done",
            reminder_at=timezone.now() - timezone.timedelta(hours=1),
        )

        self.assertFalse(memo.is_overdue)
