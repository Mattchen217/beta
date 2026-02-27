# src/time_parse.py
import re
from datetime import datetime, timedelta

_CN_NUM = {
    "零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10
}

def cn_to_int(s: str) -> int | None:
    """
    支持：三、两、十、十一、十二、二十、二十一、30
    """
    s = s.strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)

    # 简单处理 0-99 的中文数
    if s in _CN_NUM:
        return _CN_NUM[s]

    if "十" in s:
        parts = s.split("十")
        left = parts[0].strip()
        right = parts[1].strip() if len(parts) > 1 else ""
        tens = 1 if left == "" else _CN_NUM.get(left, None)
        if tens is None:
            return None
        ones = 0 if right == "" else _CN_NUM.get(right, None)
        if ones is None:
            return None
        return tens * 10 + ones

    return None


def day_range_of(dt: datetime):
    start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    end = dt.replace(hour=23, minute=59, second=59, microsecond=0)
    return start.isoformat(), end.isoformat()


def parse_time_range_cn(text: str, now: datetime | None = None):
    """
    从中文问题中解析一个粗略时间范围（start_ts, end_ts）
    覆盖：三天前/3天前/近三天/三天内/昨天/前天/上周/本周/上个月/本月
    """
    now = now or datetime.now()
    t = text.strip()

    # ===== 1) N天前 / N日前（支持中文数字与阿拉伯数字，允许空格）=====
    m = re.search(r"([零一二两三四五六七八九十\d]+)\s*天\s*(前|以前)|([零一二两三四五六七八九十\d]+)\s*日\s*前", t)
    if m:
        num_str = m.group(1) or m.group(3)
        days = cn_to_int(num_str)
        if days is not None:
            target = now - timedelta(days=days)
            return day_range_of(target)

    # ===== 2) 近N天 / N天内 / 最近N天 =====
    m = re.search(r"(近|最近)\s*([零一二两三四五六七八九十\d]+)\s*天|([零一二两三四五六七八九十\d]+)\s*天\s*内", t)
    if m:
        num_str = m.group(2) or m.group(3)
        days = cn_to_int(num_str)
        if days is not None:
            start = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
            return start.isoformat(), end.isoformat()

    # ===== 3) N小时前 =====
    m = re.search(r"([零一二两三四五六七八九十\d]+)\s*小\s*时\s*前", t)
    if m:
        hours = cn_to_int(m.group(1))
        if hours is not None:
            start = now - timedelta(hours=hours)
            end = now
            return start.isoformat(), end.isoformat()

    # ===== 4) 昨天 / 前天 =====
    if re.search(r"昨天|昨日", t):
        return day_range_of(now - timedelta(days=1))

    if "前天" in t:
        return day_range_of(now - timedelta(days=2))

    # ===== 5) 上周 / 本周（周一~周日）=====
    if "上周" in t:
        this_monday = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        last_monday = this_monday - timedelta(days=7)
        last_sunday_end = this_monday - timedelta(seconds=1)
        return last_monday.isoformat(), last_sunday_end.isoformat()

    if "本周" in t or "这周" in t:
        this_monday = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        return this_monday.isoformat(), now.isoformat()

    # ===== 6) 上个月 / 本月 =====
    if "本月" in t or "这个月" in t:
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return start.isoformat(), now.isoformat()

    if "上个月" in t:
        first_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_end = first_this_month - timedelta(seconds=1)
        last_month_start = last_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return last_month_start.isoformat(), last_month_end.isoformat()

    return None, None