# src/query.py
from datetime import datetime
from src.a_memory.search import MemorySearch
from src.a_memory.db import connect
from src.a_memory.time_parse import parse_time_range_cn
import re

def load_conversations():
    """从 DB 加载会话元信息，用于自动识别 conv_id。"""
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT conv_id, title, participants FROM conversations")
    rows = cur.fetchall()
    conn.close()

    convs = []
    for cid, title, participants in rows:
        title = title or ""
        participants = participants or ""
        convs.append({
            "conv_id": cid,
            "title": title,
            "participants": [p.strip() for p in participants.split(",") if p.strip()],
        })
    return convs

def detect_conv_id(query: str, convs):
    """
    从用户问题中自动识别 conv_id。
    优先级：
    1) title 的“主关键词”命中（例如 '客户A' / '项目群B' / '产品设计'）
    2) title 全量/部分命中
    3) participant 命中（例如 'coo'/'pm'/'designer'）
    """
    q = query.strip()

    # 1) 先抽取 title 主关键词：取 " - " 前面的部分（如 "客户A - 合同与报价" -> "客户A"）
    for c in convs:
        main_key = c["title"].split(" - ")[0].strip()
        if main_key and main_key in q:
            return c["conv_id"], f"title主关键词命中: {main_key}"

    # 2) title 里任意连续 2~4 个字的片段命中（防止标题较长）
    for c in convs:
        title = c["title"].strip()
        if not title:
            continue
        # 粗略拆分：中文/英文都兼容
        # 取短 token（避免把“合同与报价”这种也能命中）
        candidates = []
        # 中文连续词块
        candidates += re.findall(r"[\u4e00-\u9fff]{2,6}", title)
        # 英文/数字词块
        candidates += re.findall(r"[A-Za-z0-9_]{2,20}", title)

        for token in candidates:
            if token in q:
                return c["conv_id"], f"title片段命中: {token}"

    # 3) participant 命中
    q_tokens = set(re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]{1,6}", q))
    for c in convs:
        for p in c["participants"]:
            if p in q_tokens:
                return c["conv_id"], f"participant命中: {p}"

    return None, "未识别"

def detect_conv_from_query(query: str):
    """
    如果用户问题中包含会话标题关键词，则返回 conv_id
    """
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT conv_id, title FROM conversations")
    rows = cur.fetchall()
    conn.close()

    for cid, title in rows:
        # 简单匹配（后续可以做模糊匹配）
        if title and title.split(" ")[0] in query:
            return cid
    return None

def conv_title(conv_id: str) -> str:
    """把 conv_id 转成可读的会话标题（客户A/项目群B）。"""
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT title FROM conversations WHERE conv_id=?", (conv_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row and row[0] else conv_id


def normalize_date_input(s: str, is_start: bool) -> str | None:
    """
    支持用户手动输入：
    - YYYY-MM-DD
    - YYYY-MM-DDTHH:MM:SS
    返回 ISO 字符串
    """
    s = s.strip()
    if not s:
        return None
    # 只输入日期
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        return s + ("T00:00:00" if is_start else "T23:59:59")
    # 已经是带时间的 ISO
    return s


def main():
    ms = MemorySearch()

    while True:
        q = input("\n请输入问题（q退出）：").strip()
        if not q:
            continue
        if q.lower() == "q":
            break

        # 你可以改成 datetime.now()；为了复现“3天前”等效果，先固定 now
        now = datetime(2026, 2, 19, 20, 0, 0)
        auto_start, auto_end = parse_time_range_cn(q, now=now)

        convs = load_conversations()
        auto_conv, conv_reason = detect_conv_id(q, convs)
        if auto_conv:
            print(f"自动识别会话：{conv_title(auto_conv)}（{conv_reason}）")
        else:
            print("自动识别会话：未识别")
        if auto_conv:
            conv = auto_conv
            print("✅ 已自动选择会话，跳过手动输入。")
        else:
            conv = input("限定会话conv_id（回车不限定）：").strip() or None

        # 自动时间范围已在上面得到：auto_start, auto_end
        # 如果识别到了，就直接用；否则才问用户
        if auto_start and auto_end:
            start_ts, end_ts = auto_start, auto_end
            print("✅ 已自动填充时间范围，跳过手动输入。")
        else:
            start_in = input("开始时间(YYYY-MM-DD 或 ISO 或回车=不限制)：").strip()
            end_in = input("结束时间(YYYY-MM-DD 或 ISO 或回车=不限制)：").strip()
            start_ts = normalize_date_input(start_in, is_start=True)
            end_ts = normalize_date_input(end_in, is_start=False)

        hits = ms.search(q, top_k=5, conv_id=conv, start_ts=start_ts, end_ts=end_ts)

        print("\n--- 检索结果 ---")
        if not hits:
            print("（无结果）你可以：1) 去掉时间限制 2) 填更宽的时间范围 3) 加人名/群名关键词")
            continue

        for i, h in enumerate(hits, 1):
            title = conv_title(h["conv_id"])
            print(f"\n[{i}] conf={h['confidence']} score={h['score']:.3f} conv={title} ({h['conv_id']}) time={h['time_range']}")
            print(h["text"])
            print("引用消息IDs:", h["message_ids"])


if __name__ == "__main__":
    main()