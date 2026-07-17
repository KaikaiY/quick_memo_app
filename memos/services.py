"""メモのライフサイクル操作（完了・取消・論理削除・復元・完全削除）を一元管理する。

完了/削除の状態遷移をビューへ散らばらせず、ここに集約する。
将来 Google カレンダー連携を追加する際は、対応する予定の作成・削除も
この関数群の中で扱えるようにする（今回は API 連携自体は実装しない）。
"""

from django.utils import timezone


def _default_active_status(memo):
    """未完了に戻すときの状態。リマインダーがあれば今日、なければ未整理。"""
    return "today" if memo.reminder_at else "inbox"


def complete_memo(memo):
    memo.status = "done"
    memo.completed_at = timezone.now()
    memo.save(update_fields=["status", "completed_at", "updated_at"])


def uncomplete_memo(memo):
    memo.status = _default_active_status(memo)
    memo.completed_at = None
    memo.save(update_fields=["status", "completed_at", "updated_at"])


def trash_memo(memo):
    memo.status = "trash"
    memo.deleted_at = timezone.now()
    memo.save(update_fields=["status", "deleted_at", "updated_at"])


def restore_memo(memo):
    memo.status = _default_active_status(memo)
    memo.deleted_at = None
    memo.save(update_fields=["status", "deleted_at", "updated_at"])


def purge_memo(memo):
    # 将来: 連携済みの場合はここで Google カレンダーの予定も削除する。
    memo.delete()
