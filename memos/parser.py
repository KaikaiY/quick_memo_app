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

KANJI_DIGITS = {
    "〇": 0,
    "零": 0,
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}

# 日時に使う数値。アラビア数字または簡単な漢数字（0〜99）を許容する。
NUM = r"(?:\d{1,2}|[〇零一二三四五六七八九十]{1,3})"

# 日時を削除した後、本文の先頭に残りやすい記号・空白。
LEADING_JUNK = "、。，．・：:　 \t　"

PRIORITY_PATTERN = re.compile(r"^[!！](?P<priority>高|中|低)\s*")

TIME_PATTERN = (
    rf"(?:(?P<ampm>午前|午後)?\s*(?P<hour>{NUM})"
    rf"(?:(?::(?P<minute>\d{{2}}))|時(?:(?P<jp_minute>{NUM})分?)?)"
    r"|(?P<day_part>朝|昼|夕方|夜))"
)

RELATIVE_PATTERN = re.compile(
    rf"^(?P<relative_day>今日|明日|明後日)\s*(?:の)?\s*{TIME_PATTERN}\s*(?:に)?\s*(?P<content>.+)$"
)
SLASH_DATE_PATTERN = re.compile(
    rf"^(?P<month>\d{{1,2}})/(?P<date_day>\d{{1,2}})\s*{TIME_PATTERN}\s*(?:に)?\s*(?P<content>.+)$"
)
KANJI_DATE_PATTERN = re.compile(
    rf"^(?P<month>{NUM})月(?P<date_day>{NUM})日\s*{TIME_PATTERN}\s*(?:に)?\s*(?P<content>.+)$"
)
RELATIVE_DATE_ONLY_PATTERN = re.compile(
    r"^(?P<relative_day>今日|明日|明後日)\s*(?:に)?\s*(?P<content>.+)$"
)
SLASH_DATE_ONLY_PATTERN = re.compile(
    r"^(?P<month>\d{1,2})/(?P<date_day>\d{1,2})\s*(?:に)?\s*(?P<content>.+)$"
)
KANJI_DATE_ONLY_PATTERN = re.compile(
    rf"^(?P<month>{NUM})月(?P<date_day>{NUM})日\s*(?:に)?\s*(?P<content>.+)$"
)

PATTERNS = (
    RELATIVE_PATTERN,
    SLASH_DATE_PATTERN,
    KANJI_DATE_PATTERN,
    RELATIVE_DATE_ONLY_PATTERN,
    SLASH_DATE_ONLY_PATTERN,
    KANJI_DATE_ONLY_PATTERN,
)


def parse_quick_memo(text, base_datetime=None):
    raw_text = text.strip()
    if not raw_text:
        return ParsedMemo(content="")

    priority, memo_text = _extract_priority(raw_text)
    now = timezone.localtime(base_datetime or timezone.now())

    for pattern in PATTERNS:
        match = pattern.match(memo_text)
        if match:
            try:
                reminder_at = _build_reminder_at(match, now)
            except ValueError:
                return ParsedMemo(content=memo_text, priority=priority)
            content = _clean_content(match.group("content"))
            return ParsedMemo(content=content or memo_text, reminder_at=reminder_at, priority=priority)

    return ParsedMemo(content=memo_text, priority=priority)


def _extract_priority(text):
    match = PRIORITY_PATTERN.match(text)
    if not match:
        return "unset", text

    priority = PRIORITY_TOKENS[match.group("priority")]
    content = text[match.end() :].strip()
    return priority, content or text


def _clean_content(text):
    return text.strip().lstrip(LEADING_JUNK).strip()


def _kanji_to_int(token):
    """アラビア数字または簡単な漢数字（0〜99）を int に変換する。"""
    if token is None:
        return None
    if token.isdigit():
        return int(token)
    try:
        if "十" in token:
            tens, _, ones = token.partition("十")
            tens_value = KANJI_DIGITS[tens] if tens else 1
            ones_value = KANJI_DIGITS[ones] if ones else 0
            return tens_value * 10 + ones_value
        return KANJI_DIGITS[token]
    except KeyError as exc:
        raise ValueError(f"unrecognized numeral: {token}") from exc


def _build_reminder_at(match, now):
    groups = match.groupdict()
    day_part = groups.get("day_part")
    hour_token = groups.get("hour")

    if day_part:
        hour, minute = DAY_PART_TIMES[day_part]
    elif hour_token is not None:
        hour = _kanji_to_int(hour_token)
        minute_token = groups.get("minute") or groups.get("jp_minute")
        minute = _kanji_to_int(minute_token) if minute_token else 0
        hour = _apply_ampm(groups.get("ampm"), hour)
    else:
        hour, minute = _default_time(match)

    if groups.get("month"):
        month = _kanji_to_int(groups["month"])
        day = _kanji_to_int(groups["date_day"])
        reminder_at = now.replace(month=month, day=day, hour=hour, minute=minute, second=0, microsecond=0)
        if reminder_at < now:
            reminder_at = reminder_at.replace(year=reminder_at.year + 1)
        return reminder_at

    days = DAY_OFFSETS[groups["relative_day"]]
    reminder_at = now + timezone.timedelta(days=days)
    return reminder_at.replace(hour=hour, minute=minute, second=0, microsecond=0)


def _apply_ampm(ampm, hour):
    if ampm == "午前" and hour == 12:
        return 0
    if ampm == "午後" and hour < 12:
        return hour + 12
    return hour


def _default_time(match):
    if match.groupdict().get("relative_day") == "今日":
        return 23, 59
    return 9, 0
