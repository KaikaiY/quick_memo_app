from django.contrib import messages
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import MemoForm, QuickMemoForm, ReparseMemoForm
from .models import Memo
from .parser import parse_quick_memo


def get_default_user():
    user, _ = User.objects.get_or_create(
        username="default",
        defaults={"email": "default@example.com"},
    )
    return user


def get_safe_next_url(request, method="POST"):
    next_url = request.POST.get("next") if method == "POST" else request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return next_url
    return None


def memo_list(request):
    user = get_default_user()

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


def nightly_review(request):
    user = get_default_user()
    review_memos = Memo.objects.filter(user=user, status="inbox").order_by("-created_at")

    context = {
        "review_memos": review_memos,
    }
    return render(request, "memos/nightly_review.html", context)


def memo_edit(request, pk):
    user = get_default_user()
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
def memo_done(request, pk):
    user = get_default_user()
    memo = get_object_or_404(Memo, pk=pk, user=user)
    memo.mark_done()
    messages.success(request, "完了にしました。")
    return redirect(get_safe_next_url(request) or "memo_list")


@require_POST
def memo_delete(request, pk):
    user = get_default_user()
    memo = get_object_or_404(Memo, pk=pk, user=user)
    memo.status = "trash"
    memo.save(update_fields=["status", "updated_at"])
    messages.success(request, "メモを削除しました。")
    return redirect(get_safe_next_url(request) or "memo_list")
