from django.contrib import messages
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import MemoForm, QuickMemoForm
from .models import Memo
from .parser import parse_quick_memo


def get_default_user():
    user, _ = User.objects.get_or_create(
        username="default",
        defaults={"email": "default@example.com"},
    )
    return user


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
                priority="unset",
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


def memo_edit(request, pk):
    user = get_default_user()
    memo = get_object_or_404(Memo, pk=pk, user=user)

    if request.method == "POST":
        form = MemoForm(request.POST, instance=memo)
        if form.is_valid():
            form.save()
            messages.success(request, "メモを更新しました。")
            return redirect("memo_list")
    else:
        form = MemoForm(instance=memo)

    return render(request, "memos/memo_edit.html", {"form": form, "memo": memo})


@require_POST
def memo_done(request, pk):
    user = get_default_user()
    memo = get_object_or_404(Memo, pk=pk, user=user)
    memo.mark_done()
    messages.success(request, "完了にしました。")
    return redirect("memo_list")


@require_POST
def memo_delete(request, pk):
    user = get_default_user()
    memo = get_object_or_404(Memo, pk=pk, user=user)
    memo.status = "trash"
    memo.save(update_fields=["status", "updated_at"])
    messages.success(request, "メモを削除しました。")
    return redirect("memo_list")
