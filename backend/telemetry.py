"""运行监控：把终端里刷的日志收进内存，供管理员数据大屏可视化。

记录三类信息：
    HTTP 请求   每个接口的状态码与耗时
    接口报错    异常、约束冲突、鉴权失败等
    模型调用    大模型的耗时、是否降级（对应 AI 小管家 / 食物估算 / 图片识别）

数据只保存在进程内存里（环形缓冲，最多 300 条日志），重启后清空；
账号数、记录数等累计量在生成快照时直接从数据库统计。
"""

from __future__ import annotations

import threading
import time
import traceback
from collections import deque
from datetime import datetime, timedelta

MAX_LOGS = 300
MAX_REQUESTS = 5000
MAX_AI = 500

_lock = threading.Lock()
_started = time.time()
_logs = deque(maxlen=MAX_LOGS)
_requests = deque(maxlen=MAX_REQUESTS)
_ai_calls = deque(maxlen=MAX_AI)


def _stamp(ts=None):
    return datetime.fromtimestamp(ts or time.time()).strftime("%m-%d %H:%M:%S")


def _push(level, kind, text, ts=None):
    _logs.append({
        "time": _stamp(ts),
        "level": level,
        "kind": kind,
        "text": text,
    })


def record_request(method, path, status, ms, user_id=None):
    """记录一次接口请求。"""
    ts = time.time()
    ok = status < 400
    with _lock:
        _requests.append((ts, ok, ms))
        if status >= 500:
            level = "ERROR"
        elif not ok:
            level = "WARN"
        else:
            level = "INFO"
        _push(level, "http", "%s %s → %d · %d ms%s" % (
            method, path, status, round(ms),
            " · 用户#%s" % user_id if user_id else "",
        ), ts)


def record_error(message, path="", detail=""):
    """记录一次接口异常（5xx 或未捕获异常）。"""
    ts = time.time()
    with _lock:
        text = message if not path else "%s %s：%s" % (path, message, detail)
        _push("ERROR", "error", text.strip(), ts)


def record_ai(ms, ok, model="", kind="chat", error=""):
    """记录一次大模型调用。"""
    ts = time.time()
    with _lock:
        _ai_calls.append((ts, ms, ok, model, kind))
        if ok:
            text = "%s 调用成功 · %d ms · %s" % (kind, round(ms), model or "-")
            _push("INFO", "ai", text, ts)
        else:
            text = "%s 调用失败 · %d ms · %s · %s" % (kind, round(ms), model or "-", error)
            _push("WARN", "ai", text, ts)


def _count(conn, sql, params=()):
    try:
        row = conn.execute(sql, params).fetchone()
        return int(row[0]) if row else 0
    except Exception:
        return 0


def _hourly(events, hours=12):
    """按小时聚合，返回 (labels, values)。"""
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    slots = [now - timedelta(hours=hours - 1 - i) for i in range(hours)]
    values = [0] * hours
    for ts, *_rest in events:
        delta = int((ts - slots[0].timestamp()) // 3600)
        if 0 <= delta < hours:
            values[delta] += 1
    labels = [moment.strftime("%H:00") for moment in slots]
    return labels, values


def snapshot(conn=None):
    """生成数据大屏所需的全部指标。"""
    now = time.time()
    with _lock:
        requests = list(_requests)
        ai_calls = list(_ai_calls)
        logs = list(_logs)[-80:]

    total = len(requests)
    errors = sum(1 for item in requests if not item[1])
    avg_ms = round(sum(item[2] for item in requests) / total) if total else 0

    hour_labels, hour_requests = _hourly([(item[0],) for item in requests])

    # 错误按小时统计（这里用成功标记筛出失败请求）
    fail_events = [(item[0],) for item in requests if not item[1]]
    _labels2, hour_errors = _hourly(fail_events)

    ai_ok = [item for item in ai_calls if item[2]]
    ai_avg = round(sum(item[1] for item in ai_ok) / len(ai_ok)) if ai_ok else 0
    ai_series = [
        {"time": _stamp(item[0]), "ms": round(item[1]), "ok": bool(item[2]),
         "model": item[3], "kind": item[4]}
        for item in ai_calls[-20:]
    ]
    ai_ok_rate = round(len(ai_ok) * 100 / len(ai_calls)) if ai_calls else 100

    data = {"requests24h": total, "errors24h": errors, "avgMs": avg_ms,
            "uptime": int(now - _started)}

    if conn is not None:
        today = datetime.now().strftime("%Y-%m-%d")
        data.update({
            "users": _count(conn, "SELECT COUNT(*) FROM users"),
            "usersToday": _count(conn, "SELECT COUNT(*) FROM users WHERE created_at LIKE ?",
                                  (today + "%",)),
            "online": _count(conn, "SELECT COUNT(DISTINCT user_id) FROM sessions "
                                   "WHERE expires_at > ?",
                             (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),)),
            "meals": _count(conn, "SELECT COUNT(*) FROM meal_records"),
            "weights": _count(conn, "SELECT COUNT(*) FROM weight_records"),
            "sports": _count(conn, "SELECT COUNT(*) FROM sport_records"),
            "sleeps": _count(conn, "SELECT COUNT(*) FROM sleep_records"),
            "moods": _count(conn, "SELECT COUNT(*) FROM mood_records"),
            "reports": _count(conn, "SELECT COUNT(*) FROM report_records"),
            "uploads": _count(conn, "SELECT COUNT(*) FROM uploads"),
            "aiMessages": _count(conn, "SELECT COUNT(*) FROM ai_messages"),
        })

    data.update({
        "hours": hour_labels,
        "hourRequests": hour_requests,
        "hourErrors": hour_errors,
        "aiCalls": len(ai_calls),
        "aiAvgMs": ai_avg,
        "aiOkRate": ai_ok_rate,
        "aiSeries": ai_series,
        "logs": logs,
    })
    return data


def exception_text():
    """当前异常的简短描述（最多取最后一行）。"""
    lines = traceback.format_exc().strip().splitlines()
    return lines[-1] if lines else "未知错误"
