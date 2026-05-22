import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from django.utils import timezone


@dataclass
class ParsedMemo:
    content: str
    reminder_at: Optional[datetime] = None
    priority: str = "unset"


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

PRIORITY_TOKENS = {
    "高": "high",
    "中": "middle",
    "低": "low",
}

PRIORITY_PATTERN = re.compile(r"^[!！](?P<priority>高|中|低)\s*")

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
RELATIVE_DATE_ONLY_PATTERN = re.compile(
    r"^(?P<relative_day>今日|明日|明後日)\s*(?:に)?\s*(?P<content>.+)$"
)
DATE_ONLY_PATTERN = re.compile(
    r"^(?P<month>\d{1,2})/(?P<date_day>\d{1,2})\s*(?:に)?\s*(?P<content>.+)$"
)


def parse_quick_memo(text, base_datetime=None):
    raw_text = text.strip()
    if not raw_text:
        return ParsedMemo(content="")

    priority, memo_text = _extract_priority(raw_text)
    now = timezone.localtime(base_datetime or timezone.now())

    for pattern in (RELATIVE_PATTERN, DATE_PATTERN, RELATIVE_DATE_ONLY_PATTERN, DATE_ONLY_PATTERN):
        match = pattern.match(memo_text)
        if match:
            try:
                reminder_at = _build_reminder_at(match, now)
            except ValueError:
                return ParsedMemo(content=memo_text, priority=priority)
            content = match.group("content").strip()
            return ParsedMemo(content=content or memo_text, reminder_at=reminder_at, priority=priority)

    return ParsedMemo(content=memo_text, priority=priority)


def _extract_priority(text):
    match = PRIORITY_PATTERN.match(text)
    if not match:
        return "unset", text

    priority = PRIORITY_TOKENS[match.group("priority")]
    content = text[match.end() :].strip()
    return priority, content or text


def _build_reminder_at(match, now):
    if "day_part" not in match.groupdict():
        hour, minute = _default_time(match)
    elif match.group("day_part"):
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


def _default_time(match):
    if match.groupdict().get("relative_day") == "今日":
        return 23, 59
    return 9, 0
