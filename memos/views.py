from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from . import services
from .forms import MemoForm, QuickMemoForm, ReparseMemoForm
from .google_calendar import (
    GoogleCalendarSyncError,
    build_authorization_url,
    create_google_calendar_event,
    fetch_credentials_json,
    is_google_oauth_configured,
)
from .models import GoogleCalendarCredential, Memo
from .parser import looks_like_datetime, parse_quick_memo


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


def categorize_memos(memos, now):
    """アクティブなメモを日時の状態ごとに分類し、各群を並べ替えて返す。"""
    end_of_today = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    overdue, today, upcoming, no_date = [], [], [], []

    for memo in memos:
        if memo.reminder_at is None:
            no_date.append(memo)
            continue
        reminder = timezone.localtime(memo.reminder_at)
        if reminder < now:
            overdue.append(memo)
        elif reminder <= end_of_today:
            today.append(memo)
        else:
            upcoming.append(memo)

    for group in (overdue, today, upcoming):
        group.sort(key=lambda memo: (timezone.localtime(memo.reminder_at), memo.priority_rank))

    # 日時なしは優先度順、同順位内は新しい順。
    no_date.sort(key=lambda memo: memo.created_at, reverse=True)
    no_date.sort(key=lambda memo: memo.priority_rank)

    return {"overdue": overdue, "today": today, "upcoming": upcoming, "no_date": no_date}


@login_required
def memo_preview(request):
    text = request.GET.get("text", "")
    parsed = parse_quick_memo(text)

    reminder = None
    if parsed.reminder_at:
        reminder = timezone.localtime(parsed.reminder_at).strftime("%m/%d %H:%M")

    priority_labels = dict(Memo.PRIORITY_CHOICES)
    warning = bool(text.strip()) and parsed.reminder_at is None and looks_like_datetime(text)

    return JsonResponse(
        {
            "content": parsed.content,
            "priority": parsed.priority,
            "priority_display": priority_labels.get(parsed.priority, ""),
            "reminder": reminder,
            "has_reminder": parsed.reminder_at is not None,
            "warning": warning,
        }
    )


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
    current_status = request.GET.get("status","")
    valid_statuses = dict(Memo.STATUS_CHOICES)
    if current_status in valid_statuses:
        active_memos = active_memos.filter(status=current_status)
    sorted_memos = sorted(
        active_memos,
        key=lambda memo: (memo.priority_rank, memo.reminder_at is None, memo.reminder_at or timezone.localtime()),
    )
    done_memos = memos.filter(status="done").order_by("-completed_at")[:10]

    undo_memo = None
    undo_pk = request.session.pop("undo_memo_pk", None)
    if undo_pk:
        undo_memo = Memo.objects.filter(user=user, pk=undo_pk, status="done").first()

    context = {
        "quick_form": quick_form,
        "memos": sorted_memos,
        "done_memos": done_memos,
        "undo_memo": undo_memo,
        "current_status":current_status,
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
    services.complete_memo(memo)
    messages.success(request, "完了にしました。")
    next_url = get_safe_next_url(request)
    if next_url:
        return redirect(next_url)
    request.session["undo_memo_pk"] = memo.pk
    return redirect("memo_list")


@require_POST
@login_required
def memo_uncomplete(request, pk):
    user = request.user
    memo = get_object_or_404(Memo, pk=pk, user=user, status="done")
    services.uncomplete_memo(memo)
    messages.success(request, "未完了に戻しました。")
    return redirect(get_safe_next_url(request) or "memo_list")


@require_POST
@login_required
def memo_delete(request, pk):
    user = request.user
    memo = get_object_or_404(Memo, pk=pk, user=user)
    services.trash_memo(memo)
    messages.success(request, "ゴミ箱に移動しました。")
    return redirect(get_safe_next_url(request) or "memo_list")


@login_required
def trash_list(request):
    trashed_memos = Memo.objects.filter(user=request.user, status="trash").order_by("-deleted_at", "-updated_at")
    return render(request, "memos/trash_list.html", {"trashed_memos": trashed_memos})


@require_POST
@login_required
def memo_restore(request, pk):
    memo = get_object_or_404(Memo, pk=pk, user=request.user, status="trash")
    services.restore_memo(memo)
    messages.success(request, "メモを復元しました。")
    return redirect("trash_list")


@login_required
def memo_purge(request, pk):
    memo = get_object_or_404(Memo, pk=pk, user=request.user, status="trash")
    if request.method == "POST":
        services.purge_memo(memo)
        messages.success(request, "完全に削除しました。")
        return redirect("trash_list")
    return render(request, "memos/trash_purge_confirm.html", {"memo": memo})
