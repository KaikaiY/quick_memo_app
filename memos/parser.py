import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from django.utils import timezone


@dataclass
class ParsedMemo:
    content: str
    reminder_at: Optional[datetime] = None


DAY_OFFSETS = {
    "今日": 0,
    "明日": 1,
    "明後日": 2,
}

DAY_PART_TIMES = {
    "朝": (9, 0),
    "昼": (12, 0),
    "夕方": (18, 0),
    "夜": (20, 0),
}

TIME_PATTERN = (
    r"(?:(?P<hour>\d{1,2})(?:(?::(?P<minute>\d{2}))|時(?:(?P<jp_minute>\d{1,2})分?)?)"
    r"|(?P<day_part>朝|昼|夕方|夜))"
)

RELATIVE_PATTERN = re.compile(
    rf"^(?P<relative_day>今日|明日|明後日)\s*(?:の)?\s*{TIME_PATTERN}\s*(?:に)?\s*(?P<content>.+)$"
)
DATE_PATTERN = re.compile(
    rf"^(?P<month>\d{{1,2}})/(?P<date_day>\d{{1,2}})\s*{TIME_PATTERN}\s*(?:に)?\s*(?P<content>.+)$"
)


def parse_quick_memo(text, base_datetime=None):
    raw_text = text.strip()
    if not raw_text:
        return ParsedMemo(content="")

    now = timezone.localtime(base_datetime or timezone.now())

    for pattern in (RELATIVE_PATTERN, DATE_PATTERN):
        match = pattern.match(raw_text)
        if match:
            try:
                reminder_at = _build_reminder_at(match, now)
            except ValueError:
                return ParsedMemo(content=raw_text)
            content = match.group("content").strip()
            return ParsedMemo(content=content or raw_text, reminder_at=reminder_at)

    return ParsedMemo(content=raw_text)


def _build_reminder_at(match, now):
    if match.group("day_part"):
        hour, minute = DAY_PART_TIMES[match.group("day_part")]
    else:
        hour = int(match.group("hour"))
        minute = int(match.group("minute") or match.group("jp_minute") or 0)

    if match.groupdict().get("month"):
        month = int(match.group("month"))
        day = int(match.group("date_day"))
        reminder_at = now.replace(month=month, day=day, hour=hour, minute=minute, second=0, microsecond=0)
        if reminder_at < now:
            reminder_at = reminder_at.replace(year=reminder_at.year + 1)
        return reminder_at

    days = DAY_OFFSETS[match.group("relative_day")]
    reminder_at = now + timezone.timedelta(days=days)
    return reminder_at.replace(hour=hour, minute=minute, second=0, microsecond=0)
