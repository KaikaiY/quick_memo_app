from datetime import datetime
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import override_settings
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import MemoForm
from .models import GoogleCalendarCredential, Memo
from .parser import parse_quick_memo


class MemoViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="taro", password="password123")
        self.client.force_login(self.user)

    def test_create_memo_from_top_page(self):
        response = self.client.post(
            reverse("memo_list"),
            {"text": "明日18時に牛乳を買う"},
        )

        self.assertRedirects(response, reverse("memo_list"))
        memo = Memo.objects.get()
        self.assertEqual(memo.content, "牛乳を買う")
        self.assertEqual(memo.user, self.user)
        self.assertEqual(memo.status, "today")
        self.assertIsNotNone(memo.reminder_at)

    def test_create_plain_memo_when_text_has_no_datetime(self):
        response = self.client.post(reverse("memo_list"), {"text": "旅行のアイデアを考える"})

        self.assertRedirects(response, reverse("memo_list"))
        memo = Memo.objects.get()
        self.assertEqual(memo.content, "旅行のアイデアを考える")
        self.assertEqual(memo.status, "inbox")
        self.assertIsNone(memo.reminder_at)

    def test_create_memo_with_priority_token(self):
        response = self.client.post(reverse("memo_list"), {"text": "!高 明日18時に病院"})

        self.assertRedirects(response, reverse("memo_list"))
        memo = Memo.objects.get()
        self.assertEqual(memo.content, "病院")
        self.assertEqual(memo.priority, "high")
        self.assertIsNotNone(memo.reminder_at)

    def test_create_memo_with_full_width_priority_token_and_date_only(self):
        response = self.client.post(reverse("memo_list"), {"text": "！中 明日 病院"})

        self.assertRedirects(response, reverse("memo_list"))
        memo = Memo.objects.get()
        self.assertEqual(memo.content, "病院")
        self.assertEqual(memo.priority, "middle")
        reminder_at = timezone.localtime(memo.reminder_at)
        self.assertEqual(reminder_at.hour, 9)
        self.assertEqual(reminder_at.minute, 0)

    def test_memo_list_shows_set_priority_but_not_unset_priority(self):
        Memo.objects.create(user=self.user, content="優先メモ", status="today", priority="high")
        Memo.objects.create(user=self.user, content="普通メモ", status="today", priority="unset")

        response = self.client.get(reverse("memo_list"))

        self.assertContains(response, "高")
        self.assertNotContains(response, "未設定")

    def test_done_action_marks_memo_completed(self):
        memo = Memo.objects.create(user=self.user, content="メールする", status="today")

        response = self.client.post(reverse("memo_done", args=[memo.pk]))

        self.assertRedirects(response, reverse("memo_list"))
        memo.refresh_from_db()
        self.assertEqual(memo.status, "done")
        self.assertIsNotNone(memo.completed_at)

    def test_nightly_review_shows_only_inbox_memos(self):
        Memo.objects.create(user=self.user, content="整理するメモ", status="inbox")
        Memo.objects.create(user=self.user, content="今日やるメモ", status="today")
        Memo.objects.create(user=self.user, content="完了メモ", status="done")

        response = self.client.get(reverse("nightly_review"))

        self.assertContains(response, "整理するメモ")
        self.assertNotContains(response, "今日やるメモ")
        self.assertNotContains(response, "完了メモ")

    def test_nightly_review_shows_set_priority(self):
        Memo.objects.create(user=self.user, content="整理するメモ", status="inbox", priority="high")

        response = self.client.get(reverse("nightly_review"))

        self.assertContains(response, "高")

    def test_done_action_can_redirect_back_to_nightly_review(self):
        memo = Memo.objects.create(user=self.user, content="整理するメモ", status="inbox")

        response = self.client.post(reverse("memo_done", args=[memo.pk]), {"next": reverse("nightly_review")})

        self.assertRedirects(response, reverse("nightly_review"))
        memo.refresh_from_db()
        self.assertEqual(memo.status, "done")

    def test_edit_page_can_reparse_memo_text(self):
        memo = Memo.objects.create(user=self.user, content="失敗した入力", status="inbox", priority="unset")

        response = self.client.post(
            reverse("memo_edit", args=[memo.pk]),
            {
                "action": "reparse",
                "reparse_text": "!高 明日 病院",
            },
        )

        self.assertRedirects(response, reverse("memo_list"))
        memo.refresh_from_db()
        reminder_at = timezone.localtime(memo.reminder_at)
        self.assertEqual(memo.content, "病院")
        self.assertEqual(memo.priority, "high")
        self.assertEqual(memo.status, "today")
        self.assertEqual(reminder_at.hour, 9)
        self.assertEqual(reminder_at.minute, 0)

    def test_reparse_keeps_user_on_edit_page_when_text_is_blank(self):
        memo = Memo.objects.create(user=self.user, content="失敗した入力", status="inbox")

        response = self.client.post(
            reverse("memo_edit", args=[memo.pk]),
            {
                "action": "reparse",
                "reparse_text": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        memo.refresh_from_db()
        self.assertEqual(memo.content, "失敗した入力")

    def test_memo_list_requires_login(self):
        self.client.logout()

        response = self.client.get(reverse("memo_list"))

        self.assertRedirects(response, f"{reverse('login')}?next={reverse('memo_list')}")

    def test_memo_list_only_shows_current_users_memos(self):
        other_user = User.objects.create_user(username="hanako", password="password123")
        Memo.objects.create(user=self.user, content="自分のメモ", status="today")
        Memo.objects.create(user=other_user, content="他人のメモ", status="today")

        response = self.client.get(reverse("memo_list"))

        self.assertContains(response, "自分のメモ")
        self.assertNotContains(response, "他人のメモ")

    def test_signup_creates_and_logs_in_user(self):
        self.client.logout()

        response = self.client.post(
            reverse("signup"),
            {
                "username": "newuser",
                "password1": "StrongPass123",
                "password2": "StrongPass123",
            },
        )

        self.assertRedirects(response, reverse("memo_list"))
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_logout_confirm_requires_login(self):
        self.client.logout()

        response = self.client.get(reverse("logout_confirm"))

        self.assertRedirects(response, f"{reverse('login')}?next={reverse('logout_confirm')}")

    def test_logout_confirm_page_is_visible_to_logged_in_user(self):
        response = self.client.get(reverse("logout_confirm"))

        self.assertContains(response, "ログアウトしますか？")

    def test_google_calendar_settings_requires_login(self):
        self.client.logout()

        response = self.client.get(reverse("google_calendar_settings"))

        self.assertRedirects(response, f"{reverse('login')}?next={reverse('google_calendar_settings')}")

    def test_google_calendar_settings_shows_disconnected_state(self):
        response = self.client.get(reverse("google_calendar_settings"))

        self.assertContains(response, "まだ接続されていません。")

    def test_google_calendar_connect_without_settings_redirects_back(self):
        response = self.client.get(reverse("google_calendar_connect"))

        self.assertRedirects(response, reverse("google_calendar_settings"))

    @override_settings(GOOGLE_OAUTH_CLIENT_ID="client-id", GOOGLE_OAUTH_CLIENT_SECRET="client-secret")
    @patch("memos.views.build_authorization_url", return_value=("https://accounts.google.com/o/oauth2/auth", "state-123"))
    def test_google_calendar_connect_stores_state_and_redirects(self, build_authorization_url):
        response = self.client.get(reverse("google_calendar_connect"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "https://accounts.google.com/o/oauth2/auth")
        self.assertEqual(self.client.session["google_oauth_state"], "state-123")
        build_authorization_url.assert_called_once()

    @patch("memos.views.fetch_credentials_json", return_value='{"token": "token"}')
    def test_google_calendar_callback_saves_credentials(self, fetch_credentials_json):
        session = self.client.session
        session["google_oauth_state"] = "state-123"
        session.save()

        response = self.client.get(reverse("google_calendar_callback"), {"state": "state-123", "code": "code"})

        self.assertRedirects(response, reverse("google_calendar_settings"))
        credential = GoogleCalendarCredential.objects.get(user=self.user)
        self.assertEqual(credential.credentials_json, '{"token": "token"}')
        fetch_credentials_json.assert_called_once()

    def test_google_calendar_disconnect_deletes_credentials(self):
        GoogleCalendarCredential.objects.create(user=self.user, credentials_json='{"token": "token"}')

        response = self.client.post(reverse("google_calendar_disconnect"))

        self.assertRedirects(response, reverse("google_calendar_settings"))
        self.assertFalse(GoogleCalendarCredential.objects.filter(user=self.user).exists())

    @patch(
        "memos.views.create_google_calendar_event",
        return_value={"id": "event-123", "htmlLink": "https://calendar.google.com/event?eid=123"},
    )
    def test_google_calendar_sync_creates_event_for_reminder_memo(self, create_google_calendar_event):
        credential = GoogleCalendarCredential.objects.create(user=self.user, credentials_json='{"token": "token"}')
        reminder_at = timezone.now() + timezone.timedelta(hours=2)
        memo = Memo.objects.create(user=self.user, content="病院", status="today", reminder_at=reminder_at)

        response = self.client.post(reverse("memo_google_calendar_sync", args=[memo.pk]))

        self.assertRedirects(response, reverse("memo_list"))
        memo.refresh_from_db()
        self.assertEqual(memo.google_event_id, "event-123")
        self.assertEqual(memo.google_event_link, "https://calendar.google.com/event?eid=123")
        self.assertIsNotNone(memo.google_synced_at)
        create_google_calendar_event.assert_called_once_with(memo, credential)

    @patch("memos.views.create_google_calendar_event")
    def test_google_calendar_sync_requires_google_connection(self, create_google_calendar_event):
        reminder_at = timezone.now() + timezone.timedelta(hours=2)
        memo = Memo.objects.create(user=self.user, content="病院", status="today", reminder_at=reminder_at)

        response = self.client.post(reverse("memo_google_calendar_sync", args=[memo.pk]))

        self.assertRedirects(response, reverse("google_calendar_settings"))
        memo.refresh_from_db()
        self.assertEqual(memo.google_event_id, "")
        create_google_calendar_event.assert_not_called()

    @patch("memos.views.create_google_calendar_event")
    def test_google_calendar_sync_requires_reminder(self, create_google_calendar_event):
        GoogleCalendarCredential.objects.create(user=self.user, credentials_json='{"token": "token"}')
        memo = Memo.objects.create(user=self.user, content="調べもの", status="inbox")

        response = self.client.post(reverse("memo_google_calendar_sync", args=[memo.pk]))

        self.assertRedirects(response, reverse("memo_list"))
        memo.refresh_from_db()
        self.assertEqual(memo.google_event_id, "")
        create_google_calendar_event.assert_not_called()

    def test_memo_list_shows_google_sync_button_for_reminder_memo(self):
        Memo.objects.create(
            user=self.user,
            content="病院",
            status="today",
            reminder_at=timezone.now() + timezone.timedelta(hours=2),
        )
        Memo.objects.create(user=self.user, content="調べもの", status="inbox")

        response = self.client.get(reverse("memo_list"))

        self.assertContains(response, "Googleへ追加")
        self.assertContains(response, reverse("memo_google_calendar_sync", args=[Memo.objects.get(content="病院").pk]))


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

    def test_is_synced_to_google_reflects_event_id(self):
        user = User.objects.create_user(username="default")
        memo = Memo.objects.create(user=user, content="病院")

        self.assertFalse(memo.is_synced_to_google)

        memo.google_event_id = "google-event-123"

        self.assertTrue(memo.is_synced_to_google)

    def test_google_calendar_credential_string(self):
        user = User.objects.create_user(username="taro")
        credential = GoogleCalendarCredential.objects.create(user=user, credentials_json="{}")

        self.assertEqual(str(credential), "Google Calendar: taro")


class MemoFormTest(TestCase):
    def test_category_is_not_editable(self):
        form = MemoForm()

        self.assertNotIn("category", form.fields)

    def test_done_and_trash_statuses_are_not_selectable(self):
        form = MemoForm()

        self.assertNotIn(("done", "完了"), form.fields["status"].choices)
        self.assertNotIn(("trash", "捨てる"), form.fields["status"].choices)


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

    def test_parse_priority_token(self):
        parsed = parse_quick_memo("!高 明日18時に病院", self.base_datetime)

        self.assertEqual(parsed.content, "病院")
        self.assertEqual(parsed.priority, "high")
        self.assertEqual(parsed.reminder_at.day, 15)

    def test_parse_priority_token_without_reminder(self):
        parsed = parse_quick_memo("!低 調べもの", self.base_datetime)

        self.assertEqual(parsed.content, "調べもの")
        self.assertEqual(parsed.priority, "low")
        self.assertIsNone(parsed.reminder_at)

    def test_parse_full_width_priority_token(self):
        parsed = parse_quick_memo("！中 明日 病院", self.base_datetime)

        self.assertEqual(parsed.content, "病院")
        self.assertEqual(parsed.priority, "middle")
        self.assertEqual(parsed.reminder_at.day, 15)
        self.assertEqual(parsed.reminder_at.hour, 9)
        self.assertEqual(parsed.reminder_at.minute, 0)

    def test_parse_today_without_time_uses_end_of_day(self):
        parsed = parse_quick_memo("今日 書類提出", self.base_datetime)

        self.assertEqual(parsed.content, "書類提出")
        self.assertEqual(parsed.reminder_at.day, 14)
        self.assertEqual(parsed.reminder_at.hour, 23)
        self.assertEqual(parsed.reminder_at.minute, 59)

    def test_parse_tomorrow_without_time_uses_morning(self):
        parsed = parse_quick_memo("明日 病院", self.base_datetime)

        self.assertEqual(parsed.content, "病院")
        self.assertEqual(parsed.reminder_at.day, 15)
        self.assertEqual(parsed.reminder_at.hour, 9)
        self.assertEqual(parsed.reminder_at.minute, 0)

    def test_parse_month_day_without_time_uses_morning(self):
        parsed = parse_quick_memo("5/20 書類提出", self.base_datetime)

        self.assertEqual(parsed.content, "書類提出")
        self.assertEqual(parsed.reminder_at.month, 5)
        self.assertEqual(parsed.reminder_at.day, 20)
        self.assertEqual(parsed.reminder_at.hour, 9)
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
