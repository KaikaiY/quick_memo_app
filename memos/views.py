from django.contrib import messages
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import MemoForm
from .models import Memo


def get_default_user():
    user, _ = User.objects.get_or_create(
        username="default",
        defaults={"email": "default@example.com"},
    )
    return user


def memo_list(request):
    user = get_default_user()

    if request.method == "POST":
        form = MemoForm(request.POST)
        if form.is_valid():
            memo = form.save(commit=False)
            memo.user = user
            memo.save()
            messages.success(request, "メモを追加しました。")
            return redirect("memo_list")
    else:
        form = MemoForm(initial={"status": "inbox", "priority": "unset", "category": "other"})

    memos = Memo.objects.filter(user=user).exclude(status="trash")
    active_memos = memos.exclude(status="done")
    done_memos = memos.filter(status="done")[:10]

    context = {
        "form": form,
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
