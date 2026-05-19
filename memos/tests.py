from datetime import datetime

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Memo
from .parser import parse_quick_memo


class MemoViewsTest(TestCase):
    def test_create_memo_from_top_page(self):
        response = self.client.post(
            reverse("memo_list"),
            {"text": "明日18時に牛乳を買う"},
        )

        self.assertRedirects(response, reverse("memo_list"))
        memo = Memo.objects.get()
        self.assertEqual(memo.content, "牛乳を買う")
        self.assertEqual(memo.user.username, "default")
        self.assertEqual(memo.status, "today")
        self.assertIsNotNone(memo.reminder_at)

    def test_create_plain_memo_when_text_has_no_datetime(self):
        response = self.client.post(reverse("memo_list"), {"text": "旅行のアイデアを考える"})

        self.assertRedirects(response, reverse("memo_list"))
        memo = Memo.objects.get()
        self.assertEqual(memo.content, "旅行のアイデアを考える")
        self.assertEqual(memo.status, "inbox")
        self.assertIsNone(memo.reminder_at)

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


class QuickMemoParserTest(TestCase):
    def setUp(self):
        self.base_datetime = timezone.make_aware(datetime(2026, 5, 14, 10, 0))

    def test_parse_tomorrow_with_japanese_hour(self):
        parsed = parse_quick_memo("明日18時に牛乳買う", self.base_datetime)

        self.assertEqual(parsed.content, "牛乳買う")
        self.assertEqual(parsed.reminder_at.month, 5)
        self.assertEqual(parsed.reminder_at.day, 15)
        self.assertEqual(parsed.reminder_at.hour, 18)
        self.assertEqual(parsed.reminder_at.minute, 0)

    def test_parse_day_after_tomorrow(self):
        parsed = parse_quick_memo("明後日10時に病院", self.base_datetime)

        self.assertEqual(parsed.content, "病院")
        self.assertEqual(parsed.reminder_at.month, 5)
        self.assertEqual(parsed.reminder_at.day, 16)
        self.assertEqual(parsed.reminder_at.hour, 10)
        self.assertEqual(parsed.reminder_at.minute, 0)

    def test_parse_today_night(self):
        parsed = parse_quick_memo("今日の夜に洗濯", self.base_datetime)

        self.assertEqual(parsed.content, "洗濯")
        self.assertEqual(parsed.reminder_at.month, 5)
        self.assertEqual(parsed.reminder_at.day, 14)
        self.assertEqual(parsed.reminder_at.hour, 20)
        self.assertEqual(parsed.reminder_at.minute, 0)

    def test_parse_tomorrow_morning(self):
        parsed = parse_quick_memo("明日の朝にゴミ出し", self.base_datetime)

        self.assertEqual(parsed.content, "ゴミ出し")
        self.assertEqual(parsed.reminder_at.month, 5)
        self.assertEqual(parsed.reminder_at.day, 15)
        self.assertEqual(parsed.reminder_at.hour, 9)
        self.assertEqual(parsed.reminder_at.minute, 0)

    def test_parse_month_day_with_colon_time(self):
        parsed = parse_quick_memo("5/20 14:30 歯医者", self.base_datetime)

        self.assertEqual(parsed.content, "歯医者")
        self.assertEqual(parsed.reminder_at.month, 5)
        self.assertEqual(parsed.reminder_at.day, 20)
        self.assertEqual(parsed.reminder_at.hour, 14)
        self.assertEqual(parsed.reminder_at.minute, 30)

    def test_parse_month_day_with_day_part(self):
        parsed = parse_quick_memo("5/20 夜に歯医者", self.base_datetime)

        self.assertEqual(parsed.content, "歯医者")
        self.assertEqual(parsed.reminder_at.month, 5)
        self.assertEqual(parsed.reminder_at.day, 20)
        self.assertEqual(parsed.reminder_at.hour, 20)
        self.assertEqual(parsed.reminder_at.minute, 0)

    def test_parse_plain_text_without_reminder(self):
        parsed = parse_quick_memo("あとで買うものを整理する", self.base_datetime)

        self.assertEqual(parsed.content, "あとで買うものを整理する")
        self.assertIsNone(parsed.reminder_at)

    def test_invalid_date_falls_back_to_plain_memo(self):
        parsed = parse_quick_memo("13/40 10:00 予定", self.base_datetime)

        self.assertEqual(parsed.content, "13/40 10:00 予定")
        self.assertIsNone(parsed.reminder_at)
