from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import MemoForm, QuickMemoForm, ReparseMemoForm
from .google_calendar import (
    GoogleCalendarSyncError,
    build_authorization_url,
    create_google_calendar_event,
    fetch_credentials_json,
    is_google_oauth_configured,
)
from .models import GoogleCalendarCredential, Memo
from .parser import parse_quick_memo


def get_safe_next_url(request, method="POST"):
    next_url = request.POST.get("next") if method == "POST" else request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return next_url
    return None


def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "アカウントを作成しました。")
            return redirect("memo_list")
    else:
        form = UserCreationForm()

    return render(request, "registration/signup.html", {"form": form})


@login_required
def logout_confirm(request):
    return render(request, "registration/logout_confirm.html")


@login_required
def google_calendar_settings(request):
    credential = GoogleCalendarCredential.objects.filter(user=request.user).first()
    return render(
        request,
        "memos/google_calendar_settings.html",
        {
            "credential": credential,
            "is_google_oauth_configured": is_google_oauth_configured(),
        },
    )


@login_required
def google_calendar_connect(request):
    try:
        authorization_url, state = build_authorization_url(request)
    except ImproperlyConfigured:
        messages.error(request, "Google連携の設定がまだありません。環境変数を設定してください。")
        return redirect("google_calendar_settings")

    request.session["google_oauth_state"] = state
    return redirect(authorization_url)


@login_required
def google_calendar_callback(request):
    try:
        credentials_json = fetch_credentials_json(request)
    except (ImproperlyConfigured, ValueError):
        messages.error(request, "Google連携に失敗しました。もう一度試してください。")
        return redirect("google_calendar_settings")

    GoogleCalendarCredential.objects.update_or_create(
        user=request.user,
        defaults={
            "credentials_json": credentials_json,
            "calendar_id": settings.GOOGLE_CALENDAR_ID,
            "connected_at": timezone.now(),
        },
    )
    request.session.pop("google_oauth_state", None)
    messages.success(request, "Googleカレンダーと連携しました。")
    return redirect("google_calendar_settings")


@require_POST
@login_required
def google_calendar_disconnect(request):
    GoogleCalendarCredential.objects.filter(user=request.user).delete()
    messages.success(request, "Googleカレンダー連携を解除しました。")
    return redirect("google_calendar_settings")


@require_POST
@login_required
def memo_google_calendar_sync(request, pk):
    user = request.user
    memo = get_object_or_404(Memo, pk=pk, user=user)
    next_url = get_safe_next_url(request) or "memo_list"

    if not memo.reminder_at:
        messages.error(request, "リマインダーがあるメモだけGoogleカレンダーに追加できます。")
        return redirect(next_url)

    if memo.is_synced_to_google:
        messages.info(request, "このメモはすでにGoogleカレンダーに追加済みです。")
        return redirect(next_url)

    credential = GoogleCalendarCredential.objects.filter(user=user).first()
    if not credential:
        messages.error(request, "先にGoogleカレンダー連携をしてください。")
        return redirect("google_calendar_settings")

    try:
        event = create_google_calendar_event(memo, credential)
    except (GoogleCalendarSyncError, ValueError):
        messages.error(request, "Googleカレンダーへの追加に失敗しました。もう一度試してください。")
        return redirect(next_url)

    memo.google_event_id = event.get("id", "")
    memo.google_event_link = event.get("htmlLink", "")
    memo.google_synced_at = timezone.now()
    memo.save(update_fields=["google_event_id", "google_event_link", "google_synced_at", "updated_at"])
    messages.success(request, "Googleカレンダーに予定を追加しました。")
    return redirect(next_url)


@login_required
def memo_list(request):
    user = request.user

    if request.method == "POST":
        quick_form = QuickMemoForm(request.POST)
        if quick_form.is_valid():
            parsed_memo = parse_quick_memo(quick_form.cleaned_data["text"])
            Memo.objects.create(
                user=user,
                content=parsed_memo.content,
                reminder_at=parsed_memo.reminder_at,
                category="other",
                priority=parsed_memo.priority,
                status="today" if parsed_memo.reminder_at else "inbox",
            )
            if parsed_memo.reminder_at:
                messages.success(request, "リマインダー付きメモを追加しました。")
            else:
                messages.success(request, "メモを追加しました。")
            return redirect("memo_list")
    else:
        quick_form = QuickMemoForm()

    memos = Memo.objects.filter(user=user).exclude(status="trash")
    active_memos = memos.exclude(status="done")
    done_memos = memos.filter(status="done")[:10]

    context = {
        "quick_form": quick_form,
        "active_memos": active_memos,
        "done_memos": done_memos,
        "status_choices": Memo.STATUS_CHOICES,
    }
    return render(request, "memos/memo_list.html", context)


@login_required
def nightly_review(request):
    user = request.user
    review_memos = Memo.objects.filter(user=user, status="inbox").order_by("-created_at")

    context = {
        "review_memos": review_memos,
    }
    return render(request, "memos/nightly_review.html", context)


@login_required
def memo_edit(request, pk):
    user = request.user
    memo = get_object_or_404(Memo, pk=pk, user=user)
    next_url = get_safe_next_url(request) if request.method == "POST" else get_safe_next_url(request, "GET")

    if request.method == "POST":
        if request.POST.get("action") == "reparse":
            reparse_form = ReparseMemoForm(request.POST)
            form = MemoForm(instance=memo)
            if reparse_form.is_valid():
                parsed_memo = parse_quick_memo(reparse_form.cleaned_data["reparse_text"])
                memo.content = parsed_memo.content
                memo.reminder_at = parsed_memo.reminder_at
                memo.priority = parsed_memo.priority
                memo.status = "today" if parsed_memo.reminder_at else "inbox"
                memo.save(update_fields=["content", "reminder_at", "priority", "status", "updated_at"])
                messages.success(request, "一文から再解析しました。")
                return redirect(next_url or "memo_list")
        else:
            form = MemoForm(request.POST, instance=memo)
            reparse_form = ReparseMemoForm()
            if form.is_valid():
                form.save()
                messages.success(request, "メモを更新しました。")
                return redirect(next_url or "memo_list")
    else:
        form = MemoForm(instance=memo)
        reparse_form = ReparseMemoForm()

    return render(
        request,
        "memos/memo_edit.html",
        {"form": form, "reparse_form": reparse_form, "memo": memo, "next_url": next_url},
    )


@require_POST
@login_required
def memo_done(request, pk):
    user = request.user
    memo = get_object_or_404(Memo, pk=pk, user=user)
    memo.mark_done()
    messages.success(request, "完了にしました。")
    return redirect(get_safe_next_url(request) or "memo_list")


@require_POST
@login_required
def memo_delete(request, pk):
    user = request.user
    memo = get_object_or_404(Memo, pk=pk, user=user)
    memo.status = "trash"
    memo.save(update_fields=["status", "updated_at"])
    messages.success(request, "メモを削除しました。")
    return redirect(get_safe_next_url(request) or "memo_list")
