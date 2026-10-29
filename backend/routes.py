"""REST 接口层：路由表 + 各功能模块的读写逻辑。

约定：
- 处理函数返回 dict 即为 200，返回 (状态码, dict) 可自定义状态码；
- 出错时抛出 ApiError，由 app.py 统一转成 JSON；
- 所有业务接口都要求登录，数据按 user_id 隔离。
"""

from __future__ import annotations

import base64
import json
import os
import re
from datetime import datetime, timedelta

from . import ai, auth, db
from .errors import ApiError

# ==========================================================
# 路由注册与分发
# ==========================================================
ROUTES = []


def route(method, pattern, auth_required=True):
    """把一个处理函数注册到 方法 + 路径模板 上。"""

    def decorator(func):
        ROUTES.append((method.upper(), pattern, auth_required, func))
        return func

    return decorator


def split_path(path):
    return [part for part in path.strip("/").split("/") if part]


def match_path(pattern, parts):
    pattern_parts = split_path(pattern)
    if len(pattern_parts) != len(parts):
        return None
    params = {}
    for expected, actual in zip(pattern_parts, parts):
        if expected.startswith("<") and expected.endswith(">"):
            params[expected[1:-1]] = actual
        elif expected != actual:
            return None
    return params


class Context:
    """一次请求的上下文。"""

    def __init__(self, conn, user, token, body, query, params, raw_body, headers):
        self.conn = conn
        self.user = user
        self.token = token
        self.body = body if isinstance(body, dict) else {}
        self.query = query
        self.params = params
        self.raw_body = raw_body
        self.headers = headers

    @property
    def user_id(self):
        return self.user["id"]


def dispatch(conn, method, path, *, user=None, token=None, body=None, query=None,
             raw_body=b"", headers=None):
    parts = split_path(path)
    matched_path = False

    for route_method, pattern, auth_required, handler in ROUTES:
        params = match_path(pattern, parts)
        if params is None:
            continue
        matched_path = True
        if route_method != method:
            continue
        if auth_required and user is None:
            raise ApiError(401, "请先登录", "unauthorized")

        ctx = Context(conn, user, token, body, query or {}, params, raw_body, headers or {})
        result = handler(ctx)
        if isinstance(result, tuple):
            return result
        return 200, result

    if matched_path:
        raise ApiError(405, "该接口不支持此请求方法", "method_not_allowed")
    raise ApiError(404, "接口不存在", "not_found")


# ==========================================================
# 参数解析小工具
# ==========================================================

def to_float(value, name, minimum=None, maximum=None, default=None):
    if value is None or value == "":
        if default is not None:
            return default
        raise ApiError(400, "缺少参数：%s" % name)
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ApiError(400, "参数 %s 必须是数字" % name)
    if minimum is not None and number < minimum:
        raise ApiError(400, "参数 %s 不能小于 %s" % (name, minimum))
    if maximum is not None and number > maximum:
        raise ApiError(400, "参数 %s 不能大于 %s" % (name, maximum))
    return number


def to_int(value, name, minimum=None, maximum=None, default=None):
    number = to_float(value, name, minimum, maximum, default)
    return int(round(number))


def to_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("1", "true", "yes", "on")


def clean_text(value, name, max_length=200, required=False):
    text = str(value or "").strip()
    if required and not text:
        raise ApiError(400, "缺少参数：%s" % name)
    if len(text) > max_length:
        raise ApiError(400, "参数 %s 不能超过 %d 个字符" % (name, max_length))
    return text


DATE_FORMATS = ("%Y-%m-%d", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S")


def clean_date(value, name="date", default=None):
    if value in (None, ""):
        if default is not None:
            return default
        raise ApiError(400, "缺少参数：%s" % name)
    text = str(value).strip()
    for fmt in DATE_FORMATS:
        try:
            datetime.strptime(text, fmt)
            return text
        except ValueError:
            continue
    raise ApiError(400, "参数 %s 的日期格式应为 YYYY-MM-DD 或 YYYY-MM-DD HH:MM" % name)


def day_cutoff(days):
    """近 N 天（含今天）的起始日期。"""
    days = to_int(days, "days", 1, 3650, default=30)
    return (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")


def query_value(ctx, key, default=None):
    value = ctx.query.get(key)
    if isinstance(value, list):
        return value[0] if value else default
    return default if value is None else value


# ==========================================================
# 健康检查 / 接口索引
# ==========================================================

@route("GET", "/api/health", auth_required=False)
def api_health(_ctx):
    return {
        "ok": True,
        "service": "健康管理系统后端",
        "version": "2.0",
        "time": db.now(),
        "storage": "sqlite",
    }


@route("GET", "/api", auth_required=False)
def api_index(_ctx):
    groups = {}
    for method, pattern, _need_auth, _handler in ROUTES:
        groups.setdefault(pattern, []).append(method)
    endpoints = [
        {"path": path, "methods": sorted(methods)}
        for path, methods in sorted(groups.items())
    ]
    return {"endpoints": endpoints, "count": len(endpoints)}


# ==========================================================
# 账号
# ==========================================================

@route("POST", "/api/auth/register", auth_required=False)
def auth_register(ctx):
    if auth.user_from_token(ctx.conn, ctx.token):
        raise ApiError(409, "当前已登录，无需重复注册")
    account = ctx.body.get("account")
    password = ctx.body.get("password")
    nickname = clean_text(ctx.body.get("nickname"), "nickname", 30, required=False)
    user = auth.register(ctx.conn, account, password, nickname)
    token = auth.create_session(ctx.conn, user["id"])
    return 201, {
        "token": token,
        "cookie": auth.cookie_header(token),
        "user": auth.public_user(user),
    }


@route("POST", "/api/auth/login", auth_required=False)
def auth_login(ctx):
    user = auth.login(ctx.conn, ctx.body.get("account"), ctx.body.get("password"))
    token = auth.create_session(ctx.conn, user["id"])
    return {
        "token": token,
        "cookie": auth.cookie_header(token),
        "user": auth.public_user(user),
    }


@route("POST", "/api/auth/logout")
def auth_logout(ctx):
    auth.logout(ctx.conn, ctx.token)
    return {"ok": True, "cookie": auth.clear_cookie_header()}


@route("GET", "/api/auth/me")
def auth_me(ctx):
    profile = ctx.conn.execute(
        "SELECT * FROM profiles WHERE user_id = ?", (ctx.user_id,)
    ).fetchone()
    return {"user": auth.public_user(ctx.user), "profile": profile_json(profile)}


@route("POST", "/api/auth/password")
def auth_password(ctx):
    auth.change_password(
        ctx.conn,
        ctx.user,
        ctx.body.get("oldPassword"),
        ctx.body.get("newPassword"),
        keep_token=ctx.token,
    )
    return {"ok": True}


# ==========================================================
# 个人档案
# ==========================================================
PROFILE_COLUMNS = {
    "nickname": "nickname",
    "name": "name",
    "avatar": "avatar",
    "avatarImage": "avatar_image",
    "gender": "gender",
    "height": "height",
    "weight": "weight",
    "birthday": "birthday",
    "phone": "phone",
}


def profile_json(row):
    if row is None:
        return {
            "nickname": "",
            "name": "",
            "avatar": 0,
            "avatarImage": None,
            "gender": "",
            "height": 0,
            "weight": 0,
            "birthday": "",
            "phone": "",
        }
    return {
        "nickname": row["nickname"] or "",
        "name": row["name"] or "",
        "avatar": row["avatar"] or 0,
        "avatarImage": row["avatar_image"],
        "gender": row["gender"] or "",
        "height": row["height"] or 0,
        "weight": row["weight"] or 0,
        "birthday": row["birthday"] or "",
        "phone": row["phone"] or "",
    }


def read_profile(conn, user_id):
    return conn.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()


@route("GET", "/api/profile")
def profile_get(ctx):
    return {"profile": profile_json(read_profile(ctx.conn, ctx.user_id))}


@route("PUT", "/api/profile")
def profile_update(ctx):
    values = {}

    for key in ("nickname", "name", "birthday", "phone"):
        if key in ctx.body:
            values[key] = clean_text(ctx.body[key], key, 50)

    if "avatar" in ctx.body:
        values["avatar"] = to_int(ctx.body["avatar"], "avatar", 0, 99, default=0)

    if "avatarImage" in ctx.body:
        image = ctx.body["avatarImage"]
        if image in (None, ""):
            values["avatar_image"] = None
        else:
            text = str(image)
            if not text.startswith("data:image/"):
                raise ApiError(400, "头像必须是 data:image/... 的图片数据")
            if len(text) > 2_000_000:
                raise ApiError(400, "头像图片过大，请压缩后再上传")
            values["avatar_image"] = text

    if "gender" in ctx.body:
        gender = clean_text(ctx.body["gender"], "gender", 4)
        if gender and gender not in ("男", "女"):
            raise ApiError(400, "性别只能是 男 或 女")
        values["gender"] = gender

    if "height" in ctx.body:
        values["height"] = round(to_float(ctx.body["height"], "height", 0, 300, default=0), 1)

    if "weight" in ctx.body:
        values["weight"] = round(to_float(ctx.body["weight"], "weight", 0, 500, default=0), 1)

    row = read_profile(ctx.conn, ctx.user_id)
    if row is None:
        ctx.conn.execute(
            "INSERT INTO profiles(user_id, updated_at) VALUES (?, ?)", (ctx.user_id, db.now())
        )
        row = read_profile(ctx.conn, ctx.user_id)

    if values:
        pairs = [(PROFILE_COLUMNS[key], value) for key, value in values.items()]
        pairs.append(("updated_at", db.now()))
        assignments = ", ".join("%s = ?" % column for column, _value in pairs)
        ctx.conn.execute(
            "UPDATE profiles SET %s WHERE user_id = ?" % assignments,
            [value for _column, value in pairs] + [ctx.user_id],
        )

    if "nickname" in values:
        ctx.conn.execute(
            "UPDATE users SET nickname = ? WHERE id = ?", (values["nickname"], ctx.user_id)
        )

    return {"profile": profile_json(read_profile(ctx.conn, ctx.user_id))}


# ==========================================================
# 体重趋势
# ==========================================================
def weight_json(row):
    return {"id": row["id"], "date": row["date"], "weight": row["weight"]}


@route("GET", "/api/weight")
def weight_list(ctx):
    days = query_value(ctx, "days", 30)
    cutoff = day_cutoff(days)
    rows = ctx.conn.execute(
        "SELECT * FROM weight_records WHERE user_id = ? AND date >= ? ORDER BY date, id",
        (ctx.user_id, cutoff),
    ).fetchall()
    records = [weight_json(row) for row in rows]
    return {
        "records": records,
        "latest": records[-1]["weight"] if records else None,
        "days": int(days),
    }


@route("POST", "/api/weight")
def weight_create(ctx):
    weight = round(to_float(ctx.body.get("weight"), "weight", 20, 200), 1)
    date = clean_date(ctx.body.get("date"), "date", default=db.today())
    cursor = ctx.conn.execute(
        "INSERT INTO weight_records(user_id, date, weight, created_at) VALUES (?, ?, ?, ?)",
        (ctx.user_id, date, weight, db.now()),
    )
    return 201, {"record": {"id": cursor.lastrowid, "date": date, "weight": weight}}


@route("DELETE", "/api/weight/<record_id>")
def weight_delete(ctx):
    cursor = ctx.conn.execute(
        "DELETE FROM weight_records WHERE id = ? AND user_id = ?",
        (ctx.params["record_id"], ctx.user_id),
    )
    if cursor.rowcount == 0:
        raise ApiError(404, "记录不存在")
    return {"ok": True}


# ==========================================================
# 体征记录（体脂 / BMI / 血压 / 血糖）
# ==========================================================
VITAL_TYPES = ("fat", "bmi", "bp", "glucose")


def vital_json(row):
    return {
        "id": row["id"],
        "type": row["type"],
        "date": row["date"],
        "value": row["value"],
        "value2": row["value2"],
        "text": row["text"] or "",
    }


def latest_vitals(conn, user_id):
    bp = db.state_get(conn, user_id, "bp")
    glucose = db.state_get(conn, user_id, "glucose")
    return {"bp": bp, "glucose": glucose}


@route("GET", "/api/vitals")
def vital_list(ctx):
    vital_type = query_value(ctx, "type")
    if vital_type and vital_type not in VITAL_TYPES:
        raise ApiError(400, "type 只能是 %s 之一" % " / ".join(VITAL_TYPES))

    cutoff = day_cutoff(query_value(ctx, "days", 30))
    if vital_type:
        rows = ctx.conn.execute(
            "SELECT * FROM vital_records WHERE user_id = ? AND type = ? AND date >= ? "
            "ORDER BY date, id",
            (ctx.user_id, vital_type, cutoff),
        ).fetchall()
        return {"type": vital_type, "records": [vital_json(row) for row in rows]}

    rows = ctx.conn.execute(
        "SELECT * FROM vital_records WHERE user_id = ? AND date >= ? ORDER BY date, id",
        (ctx.user_id, cutoff),
    ).fetchall()
    grouped = {name: [] for name in VITAL_TYPES}
    for row in rows:
        grouped[row["type"]].append(vital_json(row))
    return {"records": grouped, "latest": latest_vitals(ctx.conn, ctx.user_id)}


@route("POST", "/api/vitals")
def vital_create(ctx):
    vital_type = clean_text(ctx.body.get("type"), "type", 10, required=True)
    if vital_type not in VITAL_TYPES:
        raise ApiError(400, "type 只能是 %s 之一" % " / ".join(VITAL_TYPES))

    date = clean_date(ctx.body.get("date"), "date", default=db.now()[:16])
    value = None if ctx.body.get("value") in (None, "") else to_float(ctx.body["value"], "value")
    value2 = None if ctx.body.get("value2") in (None, "") else to_float(ctx.body["value2"], "value2")

    if vital_type == "bp":
        systolic = to_float(ctx.body.get("systolic", value), "systolic", 40, 300)
        diastolic = to_float(ctx.body.get("diastolic", value2), "diastolic", 20, 200)
        if diastolic >= systolic:
            raise ApiError(400, "舒张压应小于收缩压")
        text = "%g/%g" % (systolic, diastolic)
        db.state_set(ctx.conn, ctx.user_id, "bp", {
            "systolic": systolic, "diastolic": diastolic, "date": date,
        })
        value, value2 = systolic, diastolic
    elif vital_type == "glucose":
        value = to_float(value, "value", 1, 40)
        text = "空腹血糖 %g mmol/L" % value
        db.state_set(ctx.conn, ctx.user_id, "glucose", {"value": value, "date": date})
    else:
        value = to_float(value, "value", 0, 200)
        text = clean_text(ctx.body.get("text"), "text", 100) or (
            "体脂率 %g%%" % value if vital_type == "fat" else "BMI %g" % value
        )

    cursor = ctx.conn.execute(
        "INSERT INTO vital_records(user_id, type, date, value, value2, text, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (ctx.user_id, vital_type, date, value, value2, text, db.now()),
    )
    return 201, {
        "record": {"id": cursor.lastrowid, "type": vital_type, "date": date,
                   "value": value, "value2": value2, "text": text},
        "latest": latest_vitals(ctx.conn, ctx.user_id),
    }


@route("DELETE", "/api/vitals/<record_id>")
def vital_delete(ctx):
    cursor = ctx.conn.execute(
        "DELETE FROM vital_records WHERE id = ? AND user_id = ?",
        (ctx.params["record_id"], ctx.user_id),
    )
    if cursor.rowcount == 0:
        raise ApiError(404, "记录不存在")
    return {"ok": True}


@route("GET", "/api/vitals/latest")
def vital_latest(ctx):
    return latest_vitals(ctx.conn, ctx.user_id)


# ==========================================================
# 饮食记录
# ==========================================================
MEALS = ("早餐", "午餐", "晚餐", "加餐")


def meal_json(row):
    return {
        "id": row["id"],
        "date": row["date"],
        "meal": row["meal"],
        "text": row["text"],
        "kcal": row["kcal"],
        "protein": row["protein"],
        "carb": row["carb"],
        "fat": row["fat"],
        "fiber": row["fiber"],
        "image": row["image"] or "",
    }


@route("GET", "/api/meals")
def meal_list(ctx):
    date = query_value(ctx, "date")
    if date:
        date = clean_date(date)
        rows = ctx.conn.execute(
            "SELECT * FROM meal_records WHERE user_id = ? AND date = ? ORDER BY id",
            (ctx.user_id, date),
        ).fetchall()
    else:
        cutoff = day_cutoff(query_value(ctx, "days", 30))
        rows = ctx.conn.execute(
            "SELECT * FROM meal_records WHERE user_id = ? AND date >= ? ORDER BY date, id",
            (ctx.user_id, cutoff),
        ).fetchall()
    return {"records": [meal_json(row) for row in rows]}


@route("POST", "/api/meals")
def meal_create(ctx):
    meal = clean_text(ctx.body.get("meal"), "meal", 10, required=True)
    if meal not in MEALS:
        raise ApiError(400, "meal 只能是 %s 之一" % " / ".join(MEALS))
    text = clean_text(ctx.body.get("text"), "text", 100, required=True)
    date = clean_date(ctx.body.get("date"), "date", default=db.today())

    nutrition = ctx.body.get("nutrition")
    if not isinstance(nutrition, dict):
        nutrition = ctx.body

    values = {
        "kcal": round(to_float(nutrition.get("kcal"), "kcal", 0, 5000, default=0), 1),
        "protein": round(to_float(nutrition.get("protein"), "protein", 0, 1000, default=0), 1),
        "carb": round(to_float(nutrition.get("carb"), "carb", 0, 1000, default=0), 1),
        "fat": round(to_float(nutrition.get("fat"), "fat", 0, 1000, default=0), 1),
        "fiber": round(to_float(nutrition.get("fiber"), "fiber", 0, 500, default=0), 1),
    }

    cursor = ctx.conn.execute(
        "INSERT INTO meal_records(user_id, date, meal, text, kcal, protein, carb, fat, fiber, image, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (ctx.user_id, date, meal, text, values["kcal"], values["protein"], values["carb"],
         values["fat"], values["fiber"], clean_text(ctx.body.get("image"), "image", 500), db.now()),
    )
    record = dict(values, id=cursor.lastrowid, date=date, meal=meal, text=text,
                  image=clean_text(ctx.body.get("image"), "image", 500))
    return 201, {"record": record}


@route("DELETE", "/api/meals/<record_id>")
def meal_delete(ctx):
    cursor = ctx.conn.execute(
        "DELETE FROM meal_records WHERE id = ? AND user_id = ?",
        (ctx.params["record_id"], ctx.user_id),
    )
    if cursor.rowcount == 0:
        raise ApiError(404, "记录不存在")
    return {"ok": True}


# ==========================================================
# 运动：目标 + 每日实际数据
# ==========================================================
def sport_json(row):
    return {
        "id": row["id"],
        "date": row["date"],
        "kcal": row["kcal"],
        "steps": row["steps"],
        "minutes": row["minutes"],
    }


def sport_goal(conn, user_id):
    row = conn.execute(
        "SELECT * FROM sport_goals WHERE user_id = ?", (user_id,)
    ).fetchone()
    if row is None:
        return {"kcal": 500, "steps": 8000, "minutes": 60}
    return {"kcal": row["kcal"], "steps": row["steps"], "minutes": row["minutes"]}


@route("GET", "/api/sport")
def sport_get(ctx):
    days = to_int(query_value(ctx, "days", 7), "days", 1, 3650)
    cutoff = day_cutoff(days)
    rows = ctx.conn.execute(
        "SELECT * FROM sport_records WHERE user_id = ? AND date >= ? ORDER BY date",
        (ctx.user_id, cutoff),
    ).fetchall()
    records = [sport_json(row) for row in rows]
    return {
        "goal": sport_goal(ctx.conn, ctx.user_id),
        "records": records,
        "history": {
            item["date"]: {"kcal": item["kcal"], "steps": item["steps"], "minutes": item["minutes"]}
            for item in records
        },
        "days": days,
    }


@route("PUT", "/api/sport/goal")
def sport_goal_update(ctx):
    kcal = to_int(ctx.body.get("kcal"), "kcal", 1, 10000)
    steps = to_int(ctx.body.get("steps"), "steps", 1, 200000)
    minutes = to_int(ctx.body.get("minutes"), "minutes", 1, 1440)
    ctx.conn.execute(
        "INSERT INTO sport_goals(user_id, kcal, steps, minutes, updated_at) VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET kcal = excluded.kcal, steps = excluded.steps, "
        "minutes = excluded.minutes, updated_at = excluded.updated_at",
        (ctx.user_id, kcal, steps, minutes, db.now()),
    )
    return {"goal": {"kcal": kcal, "steps": steps, "minutes": minutes}}


@route("GET", "/api/sport/records")
def sport_records(ctx):
    start = query_value(ctx, "from")
    end = query_value(ctx, "to")
    sql = "SELECT * FROM sport_records WHERE user_id = ?"
    args = [ctx.user_id]
    if start:
        sql += " AND date >= ?"
        args.append(clean_date(start, "from"))
    if end:
        sql += " AND date <= ?"
        args.append(clean_date(end, "to"))
    if not start and not end:
        sql += " AND date >= ?"
        args.append(day_cutoff(query_value(ctx, "days", 7)))
    rows = ctx.conn.execute(sql + " ORDER BY date", args).fetchall()
    return {"records": [sport_json(row) for row in rows]}


@route("POST", "/api/sport/records")
def sport_record_save(ctx):
    date = clean_date(ctx.body.get("date"), "date", default=db.today())
    kcal = to_int(ctx.body.get("kcal"), "kcal", 0, 10000, default=0)
    steps = to_int(ctx.body.get("steps"), "steps", 0, 200000, default=0)
    minutes = to_int(ctx.body.get("minutes"), "minutes", 0, 1440, default=0)

    ctx.conn.execute(
        "INSERT INTO sport_records(user_id, date, kcal, steps, minutes, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(user_id, date) DO UPDATE SET kcal = excluded.kcal, steps = excluded.steps, "
        "minutes = excluded.minutes",
        (ctx.user_id, date, kcal, steps, minutes, db.now()),
    )
    row = ctx.conn.execute(
        "SELECT * FROM sport_records WHERE user_id = ? AND date = ?", (ctx.user_id, date)
    ).fetchone()
    return {"record": sport_json(row)}


@route("DELETE", "/api/sport/records/<date>")
def sport_record_delete(ctx):
    date = clean_date(ctx.params["date"])
    cursor = ctx.conn.execute(
        "DELETE FROM sport_records WHERE user_id = ? AND date = ?", (ctx.user_id, date)
    )
    if cursor.rowcount == 0:
        raise ApiError(404, "当天没有运动记录")
    return {"ok": True}


# ==========================================================
# 心情
# ==========================================================
MOODS = ("开心", "平静", "疲惫", "焦虑", "低落")


def mood_json(row):
    return {"date": row["date"], "mood": row["mood"], "note": row["note"] or ""}


@route("GET", "/api/mood")
def mood_list(ctx):
    days = to_int(query_value(ctx, "days", 7), "days", 1, 3650)
    cutoff = day_cutoff(days)
    rows = ctx.conn.execute(
        "SELECT * FROM mood_records WHERE user_id = ? AND date >= ? ORDER BY date",
        (ctx.user_id, cutoff),
    ).fetchall()
    records = [mood_json(row) for row in rows]
    return {
        "records": {item["date"]: {"mood": item["mood"], "note": item["note"]} for item in records},
        "list": records,
        "days": days,
    }


@route("GET", "/api/mood/<date>")
def mood_one(ctx):
    date = clean_date(ctx.params["date"])
    row = ctx.conn.execute(
        "SELECT * FROM mood_records WHERE user_id = ? AND date = ?", (ctx.user_id, date)
    ).fetchone()
    return {"record": mood_json(row) if row else None}


@route("PUT", "/api/mood")
def mood_save(ctx):
    date = clean_date(ctx.body.get("date"), "date", default=db.today())
    mood = clean_text(ctx.body.get("mood"), "mood", 10, required=True)
    if mood not in MOODS:
        raise ApiError(400, "心情只能是 %s 之一" % " / ".join(MOODS))
    note = clean_text(ctx.body.get("note"), "note", 500)

    ctx.conn.execute(
        "INSERT INTO mood_records(user_id, date, mood, note, created_at) VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(user_id, date) DO UPDATE SET mood = excluded.mood, note = excluded.note",
        (ctx.user_id, date, mood, note, db.now()),
    )
    return {"record": {"date": date, "mood": mood, "note": note}}


@route("DELETE", "/api/mood/<date>")
def mood_delete(ctx):
    date = clean_date(ctx.params["date"])
    cursor = ctx.conn.execute(
        "DELETE FROM mood_records WHERE user_id = ? AND date = ?", (ctx.user_id, date)
    )
    if cursor.rowcount == 0:
        raise ApiError(404, "这一天没有心情记录")
    return {"ok": True}


# ==========================================================
# 睡眠
# ==========================================================
def sleep_json(row):
    return {
        "id": row["id"],
        "date": row["date"],
        "hours": row["hours"],
        "quality": row["quality"] or "",
        "note": row["note"] or "",
    }


@route("GET", "/api/sleep")
def sleep_list(ctx):
    cutoff = day_cutoff(query_value(ctx, "days", 30))
    rows = ctx.conn.execute(
        "SELECT * FROM sleep_records WHERE user_id = ? AND date >= ? ORDER BY date",
        (ctx.user_id, cutoff),
    ).fetchall()
    return {"records": [sleep_json(row) for row in rows]}


@route("POST", "/api/sleep")
def sleep_save(ctx):
    date = clean_date(ctx.body.get("date"), "date", default=db.today())
    hours = round(to_float(ctx.body.get("hours"), "hours", 0, 24, default=0), 1)
    quality = clean_text(ctx.body.get("quality"), "quality", 20)
    note = clean_text(ctx.body.get("note"), "note", 200)

    ctx.conn.execute(
        "INSERT INTO sleep_records(user_id, date, hours, quality, note, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(user_id, date) DO UPDATE SET hours = excluded.hours, "
        "quality = excluded.quality, note = excluded.note",
        (ctx.user_id, date, hours, quality, note, db.now()),
    )
    row = ctx.conn.execute(
        "SELECT * FROM sleep_records WHERE user_id = ? AND date = ?", (ctx.user_id, date)
    ).fetchone()
    return {"record": sleep_json(row)}


@route("DELETE", "/api/sleep/<date>")
def sleep_delete(ctx):
    date = clean_date(ctx.params["date"])
    cursor = ctx.conn.execute(
        "DELETE FROM sleep_records WHERE user_id = ? AND date = ?", (ctx.user_id, date)
    )
    if cursor.rowcount == 0:
        raise ApiError(404, "这一天没有睡眠记录")
    return {"ok": True}


# ==========================================================
# 综合设置：活动水平、最新血压与血糖
# ==========================================================
ACTIVITY_LEVELS = (1.2, 1.375, 1.55, 1.725)


def settings_json(ctx):
    return {
        "dietActivity": db.state_get(ctx.conn, ctx.user_id, "dietActivity", 1.375),
        "bp": db.state_get(ctx.conn, ctx.user_id, "bp"),
        "glucose": db.state_get(ctx.conn, ctx.user_id, "glucose"),
        "activityLevels": list(ACTIVITY_LEVELS),
    }


@route("GET", "/api/settings")
def settings_get(ctx):
    return settings_json(ctx)


@route("PUT", "/api/settings")
def settings_update(ctx):
    if "dietActivity" in ctx.body or "activity" in ctx.body:
        raw = ctx.body.get("dietActivity", ctx.body.get("activity"))
        activity = round(to_float(raw, "dietActivity", 0.9, 2.5), 3)
        db.state_set(ctx.conn, ctx.user_id, "dietActivity", activity)

    if "bp" in ctx.body:
        bp = ctx.body.get("bp")
        if bp in (None, ""):
            db.state_delete(ctx.conn, ctx.user_id, "bp")
        elif isinstance(bp, dict):
            systolic = to_float(bp.get("systolic"), "systolic", 40, 300)
            diastolic = to_float(bp.get("diastolic"), "diastolic", 20, 200)
            if diastolic >= systolic:
                raise ApiError(400, "舒张压应小于收缩压")
            db.state_set(ctx.conn, ctx.user_id, "bp", {
                "systolic": systolic, "diastolic": diastolic, "date": db.now()[:16],
            })
        else:
            raise ApiError(400, "bp 需要是包含 systolic / diastolic 的对象")

    if "glucose" in ctx.body:
        glucose = ctx.body.get("glucose")
        if glucose in (None, ""):
            db.state_delete(ctx.conn, ctx.user_id, "glucose")
        else:
            value = to_float(glucose, "glucose", 1, 40)
            db.state_set(ctx.conn, ctx.user_id, "glucose", {"value": value, "date": db.now()[:16]})

    return settings_json(ctx)


# ==========================================================
# 关怀提醒
# ==========================================================
def reminder_json(row):
    return {
        "id": row["id"],
        "memberId": row["member_id"],
        "title": row["title"],
        "date": row["date"],
        "done": bool(row["done"]),
    }


@route("GET", "/api/reminders")
def reminder_list(ctx):
    member_id = query_value(ctx, "memberId")
    pending = query_value(ctx, "pending")

    sql = "SELECT * FROM reminders WHERE user_id = ?"
    args = [ctx.user_id]
    if member_id:
        sql += " AND member_id = ?"
        args.append(member_id)
    if pending not in (None, "", "0"):
        sql += " AND done = 0"
    rows = ctx.conn.execute(sql + " ORDER BY date, created_at", args).fetchall()
    return {"reminders": [reminder_json(row) for row in rows]}


def ensure_member(conn, user_id, member_id):
    if not member_id:
        return
    row = conn.execute(
        "SELECT id FROM family_members WHERE id = ? AND user_id = ?", (member_id, user_id)
    ).fetchone()
    if row is None:
        raise ApiError(400, "指定的家人不存在")


@route("POST", "/api/reminders")
def reminder_create(ctx):
    title = clean_text(ctx.body.get("title"), "title", 60, required=True)
    member_id = clean_text(ctx.body.get("memberId"), "memberId", 20) or None
    ensure_member(ctx.conn, ctx.user_id, member_id)

    raw_dates = ctx.body.get("dates")
    if isinstance(raw_dates, list) and raw_dates:
        dates = [clean_date(item, "dates") for item in raw_dates][:30]
    else:
        dates = [clean_date(ctx.body.get("date"), "date", default=db.today())]

    created = []
    for date in dict.fromkeys(dates):
        reminder_id = "r" + db.new_id()
        ctx.conn.execute(
            "INSERT INTO reminders(id, user_id, member_id, title, date, done, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, 0, ?, ?)",
            (reminder_id, ctx.user_id, member_id, title, date, db.now(), db.now()),
        )
        created.append({"id": reminder_id, "memberId": member_id, "title": title,
                        "date": date, "done": False})
    return 201, {"reminders": created}


@route("PATCH", "/api/reminders/<reminder_id>")
def reminder_update(ctx):
    row = ctx.conn.execute(
        "SELECT * FROM reminders WHERE id = ? AND user_id = ?",
        (ctx.params["reminder_id"], ctx.user_id),
    ).fetchone()
    if row is None:
        raise ApiError(404, "提醒不存在")

    updates = {}
    if "title" in ctx.body:
        updates["title"] = clean_text(ctx.body["title"], "title", 60, required=True)
    if "date" in ctx.body:
        updates["date"] = clean_date(ctx.body["date"], "date")
    if "done" in ctx.body:
        updates["done"] = 1 if to_bool(ctx.body["done"]) else 0
    if "memberId" in ctx.body:
        member_id = clean_text(ctx.body["memberId"], "memberId", 20) or None
        ensure_member(ctx.conn, ctx.user_id, member_id)
        updates["member_id"] = member_id

    if updates:
        updates["updated_at"] = db.now()
        assignments = ", ".join("%s = ?" % key for key in updates)
        ctx.conn.execute(
            "UPDATE reminders SET %s WHERE id = ? AND user_id = ?" % assignments,
            list(updates.values()) + [ctx.params["reminder_id"], ctx.user_id],
        )

    row = ctx.conn.execute(
        "SELECT * FROM reminders WHERE id = ? AND user_id = ?",
        (ctx.params["reminder_id"], ctx.user_id),
    ).fetchone()
    return {"reminder": reminder_json(row)}


@route("DELETE", "/api/reminders/<reminder_id>")
def reminder_delete(ctx):
    cursor = ctx.conn.execute(
        "DELETE FROM reminders WHERE id = ? AND user_id = ?",
        (ctx.params["reminder_id"], ctx.user_id),
    )
    if cursor.rowcount == 0:
        raise ApiError(404, "提醒不存在")
    return {"ok": True}


@route("DELETE", "/api/reminders")
def reminder_clear(ctx):
    if query_value(ctx, "done") in ("1", "true"):
        cursor = ctx.conn.execute(
            "DELETE FROM reminders WHERE user_id = ? AND done = 1", (ctx.user_id,)
        )
    else:
        cursor = ctx.conn.execute(
            "DELETE FROM reminders WHERE user_id = ?", (ctx.user_id,)
        )
    return {"ok": True, "removed": cursor.rowcount}


# ==========================================================
# 常用提醒
# ==========================================================
def quick_json(row):
    return {"id": row["id"], "label": row["label"], "text": row["text"]}


@route("GET", "/api/quick-reminders")
def quick_list(ctx):
    rows = ctx.conn.execute(
        "SELECT * FROM quick_reminders WHERE user_id = ? ORDER BY sort, created_at",
        (ctx.user_id,),
    ).fetchall()
    return {"reminders": [quick_json(row) for row in rows]}


@route("POST", "/api/quick-reminders")
def quick_create(ctx):
    label = clean_text(ctx.body.get("label"), "label", 30, required=True)
    text = clean_text(ctx.body.get("text"), "text", 100) or label

    exists = ctx.conn.execute(
        "SELECT id FROM quick_reminders WHERE user_id = ? AND (text = ? OR label = ?)",
        (ctx.user_id, text, label),
    ).fetchone()
    if exists:
        raise ApiError(409, "这条常用提醒已存在", "conflict")

    reminder_id = "q" + db.new_id()
    sort = ctx.conn.execute(
        "SELECT COALESCE(MAX(sort), -1) + 1 AS next FROM quick_reminders WHERE user_id = ?",
        (ctx.user_id,),
    ).fetchone()["next"]
    ctx.conn.execute(
        "INSERT INTO quick_reminders(id, user_id, label, text, sort, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (reminder_id, ctx.user_id, label, text, sort, db.now()),
    )
    return 201, {"reminder": {"id": reminder_id, "label": label, "text": text}}


@route("DELETE", "/api/quick-reminders/<reminder_id>")
def quick_delete(ctx):
    cursor = ctx.conn.execute(
        "DELETE FROM quick_reminders WHERE id = ? AND user_id = ?",
        (ctx.params["reminder_id"], ctx.user_id),
    )
    if cursor.rowcount == 0:
        raise ApiError(404, "常用提醒不存在")
    return {"ok": True}


# ==========================================================
# 家人健康：成员与健康记录
# ==========================================================
MEMBER_FIELDS = {
    "relation": ("relation", 20),
    "name": ("name", 30),
    "conditions": ("conditions", 200),
    "medications": ("medications", 200),
    "emergencyName": ("emergency_name", 50),
    "emergencyPhone": ("emergency_phone", 30),
}


def member_json(row):
    return {
        "id": row["id"],
        "relation": row["relation"],
        "name": row["name"] or "",
        "age": row["age"] or 0,
        "conditions": row["conditions"] or "",
        "medications": row["medications"] or "",
        "emergencyName": row["emergency_name"] or "",
        "emergencyPhone": row["emergency_phone"] or "",
    }


@route("GET", "/api/family/members")
def family_members(ctx):
    rows = ctx.conn.execute(
        "SELECT * FROM family_members WHERE user_id = ? ORDER BY created_at, id", (ctx.user_id,)
    ).fetchall()
    return {"members": [member_json(row) for row in rows]}


@route("POST", "/api/family/members")
def family_member_create(ctx):
    relation = clean_text(ctx.body.get("relation"), "relation", 20, required=True)
    member_id = "m" + db.new_id()
    age = to_int(ctx.body.get("age"), "age", 0, 150, default=0)

    values = {}
    for key, (column, limit) in MEMBER_FIELDS.items():
        if key != "relation":
            values[column] = clean_text(ctx.body.get(key), key, limit)

    ctx.conn.execute(
        "INSERT INTO family_members(id, user_id, relation, name, age, conditions, medications, "
        "emergency_name, emergency_phone, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (member_id, ctx.user_id, relation, values["name"], age, values["conditions"],
         values["medications"], values["emergency_name"], values["emergency_phone"],
         db.now(), db.now()),
    )
    row = ctx.conn.execute(
        "SELECT * FROM family_members WHERE id = ?", (member_id,)
    ).fetchone()
    return 201, {"member": member_json(row)}


@route("PUT", "/api/family/members/<member_id>")
def family_member_update(ctx):
    row = ctx.conn.execute(
        "SELECT * FROM family_members WHERE id = ? AND user_id = ?",
        (ctx.params["member_id"], ctx.user_id),
    ).fetchone()
    if row is None:
        raise ApiError(404, "家人档案不存在")

    updates = {}
    for key, (column, limit) in MEMBER_FIELDS.items():
        if key in ctx.body:
            updates[column] = clean_text(ctx.body[key], key, limit)
    if "age" in ctx.body:
        updates["age"] = to_int(ctx.body["age"], "age", 0, 150, default=0)

    if updates:
        updates["updated_at"] = db.now()
        assignments = ", ".join("%s = ?" % key for key in updates)
        ctx.conn.execute(
            "UPDATE family_members SET %s WHERE id = ? AND user_id = ?" % assignments,
            list(updates.values()) + [ctx.params["member_id"], ctx.user_id],
        )

    row = ctx.conn.execute(
        "SELECT * FROM family_members WHERE id = ? AND user_id = ?",
        (ctx.params["member_id"], ctx.user_id),
    ).fetchone()
    return {"member": member_json(row)}


@route("DELETE", "/api/family/members/<member_id>")
def family_member_delete(ctx):
    member_id = ctx.params["member_id"]
    row = ctx.conn.execute(
        "SELECT id FROM family_members WHERE id = ? AND user_id = ?", (member_id, ctx.user_id)
    ).fetchone()
    if row is None:
        raise ApiError(404, "家人档案不存在")

    ctx.conn.execute("DELETE FROM family_records WHERE user_id = ? AND member_id = ?",
                     (ctx.user_id, member_id))
    ctx.conn.execute("DELETE FROM reminders WHERE user_id = ? AND member_id = ?",
                     (ctx.user_id, member_id))
    ctx.conn.execute("DELETE FROM family_members WHERE id = ? AND user_id = ?",
                     (member_id, ctx.user_id))
    return {"ok": True}


def family_record_json(row):
    return {
        "id": row["id"],
        "memberId": row["member_id"],
        "type": row["type"],
        "date": row["date"],
        "content": row["content"] or "",
    }


@route("GET", "/api/family/records")
def family_records(ctx):
    member_id = query_value(ctx, "memberId")
    sql = "SELECT * FROM family_records WHERE user_id = ?"
    args = [ctx.user_id]
    if member_id:
        sql += " AND member_id = ?"
        args.append(member_id)
    rows = ctx.conn.execute(sql + " ORDER BY date DESC, created_at DESC", args).fetchall()
    return {"records": [family_record_json(row) for row in rows]}


@route("POST", "/api/family/records")
def family_record_create(ctx):
    member_id = clean_text(ctx.body.get("memberId"), "memberId", 20, required=True)
    ensure_member(ctx.conn, ctx.user_id, member_id)

    record_type = clean_text(ctx.body.get("type"), "type", 20, required=True)
    date = clean_date(ctx.body.get("date"), "date", default=db.today())
    content = clean_text(ctx.body.get("content"), "content", 200)

    record_id = "f" + db.new_id()
    ctx.conn.execute(
        "INSERT INTO family_records(id, user_id, member_id, type, date, content, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (record_id, ctx.user_id, member_id, record_type, date, content, db.now()),
    )
    return 201, {
        "record": {"id": record_id, "memberId": member_id, "type": record_type,
                   "date": date, "content": content}
    }


@route("DELETE", "/api/family/records/<record_id>")
def family_record_delete(ctx):
    cursor = ctx.conn.execute(
        "DELETE FROM family_records WHERE id = ? AND user_id = ?",
        (ctx.params["record_id"], ctx.user_id),
    )
    if cursor.rowcount == 0:
        raise ApiError(404, "健康记录不存在")
    return {"ok": True}


# ==========================================================
# 文件上传：头像、餐食图片等
# ==========================================================
MAX_UPLOAD_BYTES = 12 * 1024 * 1024
DATA_URL_RE = re.compile(r"^data:([\w.+-]+/[\w.+-]+);base64,(.+)$", re.S)
MIME_EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def save_upload(conn, user_id, original_name, mime, data):
    ext = MIME_EXT.get(mime) or os.path.splitext(original_name or "")[1][:10] or ".bin"
    filename = db.new_id() + ext
    os.makedirs(db.UPLOAD_DIR, exist_ok=True)
    with open(os.path.join(db.UPLOAD_DIR, filename), "wb") as handle:
        handle.write(data)

    file_id = "u" + db.new_id()
    conn.execute(
        "INSERT INTO uploads(id, user_id, filename, original_name, mime, size, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (file_id, user_id, filename, original_name or filename, mime, len(data), db.now()),
    )
    return {
        "id": file_id,
        "name": original_name or filename,
        "url": "/uploads/" + filename,
        "mime": mime,
        "size": len(data),
    }


@route("POST", "/api/uploads")
def upload_create(ctx):
    from urllib.parse import unquote

    content_type = (ctx.headers.get("Content-Type") or "").split(";")[0].strip().lower()

    if content_type == "application/json":
        name = unquote(ctx.headers.get("X-File-Name") or "") or ctx.body.get("name") or "upload"
        data_url = ctx.body.get("dataUrl") or ctx.body.get("data")
        matched = DATA_URL_RE.match(str(data_url or ""))
        if not matched:
            raise ApiError(400, "dataUrl 需要是 data:<mime>;base64,<数据> 格式")
        mime = matched.group(1)
        try:
            data = base64.b64decode(matched.group(2), validate=True)
        except (ValueError, TypeError):
            raise ApiError(400, "图片数据无法解析")
    else:
        name = unquote(ctx.headers.get("X-File-Name") or "") or "upload"
        mime = content_type or "application/octet-stream"
        data = ctx.raw_body

    if not data:
        raise ApiError(400, "没有收到文件内容")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ApiError(413, "文件超过 12MB，请压缩后再上传")

    return 201, {"file": save_upload(ctx.conn, ctx.user_id, name, mime, data)}


@route("GET", "/api/uploads")
def upload_list(ctx):
    rows = ctx.conn.execute(
        "SELECT * FROM uploads WHERE user_id = ? ORDER BY created_at DESC", (ctx.user_id,)
    ).fetchall()
    return {
        "files": [
            {"id": row["id"], "name": row["original_name"], "url": "/uploads/" + row["filename"],
             "mime": row["mime"], "size": row["size"], "createdAt": row["created_at"]}
            for row in rows
        ]
    }


@route("DELETE", "/api/uploads/<file_id>")
def upload_delete(ctx):
    row = ctx.conn.execute(
        "SELECT * FROM uploads WHERE id = ? AND user_id = ?", (ctx.params["file_id"], ctx.user_id)
    ).fetchone()
    if row is None:
        raise ApiError(404, "文件不存在")

    path = os.path.join(db.UPLOAD_DIR, row["filename"])
    if os.path.isfile(path):
        os.remove(path)
    ctx.conn.execute("DELETE FROM uploads WHERE id = ? AND user_id = ?",
                     (ctx.params["file_id"], ctx.user_id))
    return {"ok": True}


# ==========================================================
# AI 健康助手：接口占位，后续接入大模型后替换 chat 逻辑
# ==========================================================
AI_PLACEHOLDER_REPLY = (
    "AI 健康助手接口已经就绪，但目前还没有接入大模型服务。"
    "接入后，这里会根据你的体重、饮食、运动与睡眠数据给出个性化建议。"
)


def ai_message_json(row):
    return {"id": row["id"], "role": row["role"], "content": row["content"],
            "createdAt": row["created_at"]}


@route("GET", "/api/ai/history")
def ai_history(ctx):
    limit = to_int(query_value(ctx, "limit", 50), "limit", 1, 200)
    rows = ctx.conn.execute(
        "SELECT * FROM ai_messages WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (ctx.user_id, limit),
    ).fetchall()
    return {"messages": [ai_message_json(row) for row in reversed(rows)],
            "configured": ai.is_configured()}


@route("POST", "/api/ai/chat")
def ai_chat(ctx):
    message = clean_text(ctx.body.get("message"), "message", 2000, required=True)
    reply, configured = ai.generate_reply(message)

    ctx.conn.execute(
        "INSERT INTO ai_messages(user_id, role, content, created_at) VALUES (?, 'user', ?, ?)",
        (ctx.user_id, message, db.now()),
    )
    ctx.conn.execute(
        "INSERT INTO ai_messages(user_id, role, content, created_at) VALUES (?, 'assistant', ?, ?)",
        (ctx.user_id, reply, db.now()),
    )
    return {
        "reply": reply,
        "configured": configured,
        "provider": None if not configured else "doubao",
        "hint": "接入大模型时修改 backend/ai.py 即可，接口保持不变",
    }


@route("DELETE", "/api/ai/history")
def ai_clear(ctx):
    cursor = ctx.conn.execute("DELETE FROM ai_messages WHERE user_id = ?", (ctx.user_id,))
    return {"ok": True, "removed": cursor.rowcount}


# ==========================================================
# 首次填写与饮食偏好
# ==========================================================
def clean_list(value, name, max_items=30, max_length=30):
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise ApiError(400, "参数 %s 需要是数组" % name)
    items = []
    for item in value[:max_items]:
        text = clean_text(item, name, max_length)
        if text:
            items.append(text)
    return items


def load_list(text):
    try:
        value = json.loads(text or "[]")
    except (TypeError, ValueError):
        return []
    return value if isinstance(value, list) else []


def preference_json(row):
    if row is None:
        return {
            "sleepQuality": "一般",
            "exerciseFrequency": "每周 1-2 次",
            "goal": "减脂塑形",
            "conditions": [],
            "taste": "清淡",
            "dietType": "均衡饮食",
            "restrictions": [],
        }
    return {
        "sleepQuality": row["sleep_quality"] or "",
        "exerciseFrequency": row["exercise_frequency"] or "",
        "goal": row["goal"] or "",
        "conditions": load_list(row["conditions"]),
        "taste": row["taste"] or "",
        "dietType": row["diet_type"] or "",
        "restrictions": load_list(row["restrictions"]),
    }


PREFERENCE_COLUMNS = {
    "sleepQuality": "sleep_quality",
    "exerciseFrequency": "exercise_frequency",
    "goal": "goal",
    "taste": "taste",
    "dietType": "diet_type",
}


@route("GET", "/api/preferences")
def preferences_get(ctx):
    row = ctx.conn.execute(
        "SELECT * FROM preferences WHERE user_id = ?", (ctx.user_id,)
    ).fetchone()
    return {"preferences": preference_json(row)}


@route("PUT", "/api/preferences")
def preferences_update(ctx):
    updates = {}
    for key, column in PREFERENCE_COLUMNS.items():
        if key in ctx.body:
            updates[column] = clean_text(ctx.body[key], key, 40)
    if "conditions" in ctx.body:
        updates["conditions"] = json.dumps(
            clean_list(ctx.body["conditions"], "conditions"), ensure_ascii=False)
    if "restrictions" in ctx.body:
        updates["restrictions"] = json.dumps(
            clean_list(ctx.body["restrictions"], "restrictions"), ensure_ascii=False)

    row = ctx.conn.execute(
        "SELECT user_id FROM preferences WHERE user_id = ?", (ctx.user_id,)
    ).fetchone()
    if row is None:
        ctx.conn.execute(
            "INSERT INTO preferences(user_id, updated_at) VALUES (?, ?)",
            (ctx.user_id, db.now()),
        )
    if updates:
        pairs = list(updates.items()) + [("updated_at", db.now())]
        assignments = ", ".join("%s = ?" % column for column, _value in pairs)
        ctx.conn.execute(
            "UPDATE preferences SET %s WHERE user_id = ?" % assignments,
            [value for _column, value in pairs] + [ctx.user_id],
        )

    row = ctx.conn.execute(
        "SELECT * FROM preferences WHERE user_id = ?", (ctx.user_id,)
    ).fetchone()
    return {"preferences": preference_json(row)}


# ==========================================================
# 女性健康档案
# ==========================================================
@route("GET", "/api/female/profile")
def female_profile_get(ctx):
    row = ctx.conn.execute(
        "SELECT * FROM female_profiles WHERE user_id = ?", (ctx.user_id,)
    ).fetchone()
    if row is None:
        return {"profile": {"periodDays": 5, "cycleDays": 28, "lastPeriodStart": ""}}
    return {"profile": {
        "periodDays": row["period_days"],
        "cycleDays": row["cycle_days"],
        "lastPeriodStart": row["last_period_start"] or "",
    }}


@route("PUT", "/api/female/profile")
def female_profile_update(ctx):
    updates = {}
    if "periodDays" in ctx.body:
        updates["period_days"] = to_int(ctx.body["periodDays"], "periodDays", 1, 15)
    if "cycleDays" in ctx.body:
        updates["cycle_days"] = to_int(ctx.body["cycleDays"], "cycleDays", 15, 60)
    if "lastPeriodStart" in ctx.body:
        updates["last_period_start"] = clean_date(
            ctx.body["lastPeriodStart"], "lastPeriodStart", default="")

    row = ctx.conn.execute(
        "SELECT user_id FROM female_profiles WHERE user_id = ?", (ctx.user_id,)
    ).fetchone()
    if row is None:
        ctx.conn.execute(
            "INSERT INTO female_profiles(user_id, updated_at) VALUES (?, ?)",
            (ctx.user_id, db.now()),
        )
    if updates:
        pairs = list(updates.items()) + [("updated_at", db.now())]
        assignments = ", ".join("%s = ?" % column for column, _value in pairs)
        ctx.conn.execute(
            "UPDATE female_profiles SET %s WHERE user_id = ?" % assignments,
            [value for _column, value in pairs] + [ctx.user_id],
        )

    return female_profile_get(ctx)


def female_status_json(row):
    return {"date": row["date"], "tags": load_list(row["tags"]), "note": row["note"] or ""}


@route("GET", "/api/female/status")
def female_status_list(ctx):
    cutoff = day_cutoff(query_value(ctx, "days", 90))
    rows = ctx.conn.execute(
        "SELECT * FROM female_status WHERE user_id = ? AND date >= ? ORDER BY date DESC",
        (ctx.user_id, cutoff),
    ).fetchall()
    return {"records": [female_status_json(row) for row in rows]}


@route("POST", "/api/female/status")
def female_status_save(ctx):
    date = clean_date(ctx.body.get("date"), "date", default=db.today())
    tags = clean_list(ctx.body.get("tags"), "tags", 20, 20)
    note = clean_text(ctx.body.get("note"), "note", 200)

    ctx.conn.execute(
        "INSERT INTO female_status(user_id, date, tags, note, created_at) VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(user_id, date) DO UPDATE SET tags = excluded.tags, note = excluded.note",
        (ctx.user_id, date, json.dumps(tags, ensure_ascii=False), note, db.now()),
    )
    return {"record": {"date": date, "tags": tags, "note": note}}


@route("DELETE", "/api/female/status/<date>")
def female_status_delete(ctx):
    date = clean_date(ctx.params["date"])
    cursor = ctx.conn.execute(
        "DELETE FROM female_status WHERE user_id = ? AND date = ?", (ctx.user_id, date)
    )
    if cursor.rowcount == 0:
        raise ApiError(404, "这一天没有状态记录")
    return {"ok": True}


# ==========================================================
# 体检报告
# ==========================================================
def report_json(row):
    return {
        "id": row["id"],
        "date": row["date"],
        "weight": row["weight"],
        "fat": row["fat"],
        "systolic": row["systolic"],
        "diastolic": row["diastolic"],
        "glucose": row["glucose"],
        "imageUrl": row["image_url"] or "",
    }


def optional_number(body, key, minimum, maximum):
    if body.get(key) in (None, ""):
        return None
    return round(to_float(body[key], key, minimum, maximum), 1)


@route("GET", "/api/reports")
def report_list(ctx):
    cutoff = day_cutoff(query_value(ctx, "days", 365))
    rows = ctx.conn.execute(
        "SELECT * FROM report_records WHERE user_id = ? AND date >= ? ORDER BY date DESC",
        (ctx.user_id, cutoff),
    ).fetchall()
    return {"records": [report_json(row) for row in rows]}


@route("POST", "/api/reports")
def report_create(ctx):
    date = clean_date(ctx.body.get("date"), "date", default=db.today())
    values = {
        "weight": optional_number(ctx.body, "weight", 20, 200),
        "fat": optional_number(ctx.body, "fat", 0, 70),
        "systolic": optional_number(ctx.body, "systolic", 40, 300),
        "diastolic": optional_number(ctx.body, "diastolic", 20, 200),
        "glucose": optional_number(ctx.body, "glucose", 1, 40),
    }
    if not any(value is not None for value in values.values()):
        raise ApiError(400, "至少填写一项体检指标")
    if values["systolic"] is not None and values["diastolic"] is not None \
            and values["diastolic"] >= values["systolic"]:
        raise ApiError(400, "舒张压应小于收缩压")
    image_url = clean_text(ctx.body.get("imageUrl"), "imageUrl", 500)

    cursor = ctx.conn.execute(
        "INSERT INTO report_records(user_id, date, weight, fat, systolic, diastolic, glucose, "
        "image_url, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (ctx.user_id, date, values["weight"], values["fat"], values["systolic"],
         values["diastolic"], values["glucose"], image_url, db.now()),
    )
    return 201, {"record": dict(values, id=cursor.lastrowid, date=date, imageUrl=image_url)}


@route("DELETE", "/api/reports/<record_id>")
def report_delete(ctx):
    cursor = ctx.conn.execute(
        "DELETE FROM report_records WHERE id = ? AND user_id = ?",
        (ctx.params["record_id"], ctx.user_id),
    )
    if cursor.rowcount == 0:
        raise ApiError(404, "体检记录不存在")
    return {"ok": True}


# ==========================================================
# 数据迁移与备份
# 前端此前把数据存在 localStorage，登录后可用 import 一次性迁移到数据库
# ==========================================================
def safe_float(value, minimum=None, maximum=None):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if minimum is not None and number < minimum:
        return None
    if maximum is not None and number > maximum:
        return None
    return round(number, 1)


def safe_text(value, limit=200, default=""):
    text = str(value if value is not None else "").strip()[:limit]
    return text or default


def safe_int(value, minimum=0, maximum=1000000, default=0):
    number = safe_float(value, minimum, maximum)
    return int(number) if number is not None else default


def safe_day(value, default=None):
    text = str(value or "").strip()[:19]
    for fmt in DATE_FORMATS:
        try:
            datetime.strptime(text, fmt)
            return text
        except ValueError:
            continue
    return default


@route("POST", "/api/sync/import")
def sync_import(ctx):
    body = ctx.body
    conn = ctx.conn
    uid = ctx.user_id
    counts = {}

    if to_bool(body.get("replace", True)):
        for table in ("weight_records", "vital_records", "meal_records", "sport_records",
                      "mood_records", "sleep_records", "reminders", "quick_reminders",
                      "family_records", "family_members"):
            conn.execute("DELETE FROM %s WHERE user_id = ?" % table, (uid,))

    # ---- 个人档案 ----
    profile = body.get("profile") or {}
    if isinstance(profile, dict) and profile:
        values = {}
        for key, column in PROFILE_COLUMNS.items():
            if key not in profile or key == "avatarImage":
                continue
            if key == "avatar":
                values["avatar"] = safe_int(profile[key], 0, 99)
            elif key in ("height", "weight"):
                number = safe_float(profile[key], 0, 500)
                if number is not None:
                    values[column] = number
            else:
                values[column] = safe_text(profile[key], 50)
        if profile.get("avatarImage"):
            image = str(profile["avatarImage"])
            if image.startswith("data:image/") and len(image) < 2_000_000:
                values["avatar_image"] = image

        if conn.execute("SELECT user_id FROM profiles WHERE user_id = ?", (uid,)).fetchone() is None:
            conn.execute("INSERT INTO profiles(user_id, updated_at) VALUES (?, ?)", (uid, db.now()))
        if values:
            pairs = list(values.items()) + [("updated_at", db.now())]
            conn.execute(
                "UPDATE profiles SET %s WHERE user_id = ?"
                % ", ".join("%s = ?" % column for column, _value in pairs),
                [value for _column, value in pairs] + [uid],
            )
        counts["profile"] = 1

    # ---- 体重趋势 ----
    imported = 0
    for item in body.get("weightHistory") or []:
        if not isinstance(item, dict):
            continue
        date = safe_day(item.get("date"), db.today())
        weight = safe_float(item.get("weight"), 20, 200)
        if date is None or weight is None:
            continue
        conn.execute(
            "INSERT INTO weight_records(user_id, date, weight, created_at) VALUES (?, ?, ?, ?)",
            (uid, date[:10], weight, db.now()),
        )
        imported += 1
    counts["weight"] = imported

    # ---- 体征历史 ----
    imported = 0
    vitals = body.get("vitalsHistory") or {}
    if isinstance(vitals, dict):
        for vital_type, items in vitals.items():
            if vital_type not in VITAL_TYPES or not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                date = safe_day(item.get("date"))
                if date is None:
                    continue
                conn.execute(
                    "INSERT INTO vital_records(user_id, type, date, value, value2, text, created_at) "
                    "VALUES (?, ?, ?, NULL, NULL, ?, ?)",
                    (uid, vital_type, date, safe_text(item.get("text"), 100), db.now()),
                )
                imported += 1
    counts["vitals"] = imported

    # ---- 最新血压 / 血糖 / 活动水平 ----
    bp = body.get("bp")
    if isinstance(bp, dict):
        systolic = safe_float(bp.get("systolic"), 40, 300)
        diastolic = safe_float(bp.get("diastolic"), 20, 200)
        if systolic is not None and diastolic is not None and diastolic < systolic:
            db.state_set(conn, uid, "bp", {"systolic": systolic, "diastolic": diastolic,
                                           "date": db.now()[:16]})
    glucose = safe_float(body.get("glucose"), 1, 40)
    if glucose is not None:
        db.state_set(conn, uid, "glucose", {"value": glucose, "date": db.now()[:16]})
    activity = safe_float(body.get("dietActivity"), 0.9, 2.5)
    if activity is not None:
        db.state_set(conn, uid, "dietActivity", activity)

    # ---- 饮食记录 ----
    imported = 0
    for item in body.get("mealLog") or []:
        if not isinstance(item, dict):
            continue
        text = safe_text(item.get("text"), 100)
        if not text:
            continue
        date = safe_day(item.get("date"), db.today())
        conn.execute(
            "INSERT INTO meal_records(user_id, date, meal, text, kcal, protein, carb, fat, fiber, "
            "image, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (uid, (date or db.today())[:10], safe_text(item.get("meal"), 10, "加餐"), text,
             safe_float(item.get("kcal"), 0, 5000) or 0,
             safe_float(item.get("protein"), 0, 1000) or 0,
             safe_float(item.get("carb"), 0, 1000) or 0,
             safe_float(item.get("fat"), 0, 1000) or 0,
             safe_float(item.get("fiber"), 0, 500) or 0,
             safe_text(item.get("image"), 500) or None, db.now()),
        )
        imported += 1
    counts["meals"] = imported

    # ---- 运动目标与每日数据 ----
    sport = body.get("sport") or {}
    if isinstance(sport, dict):
        goal = sport.get("goal") or {}
        kcal = safe_int(goal.get("kcal"), 1, 10000)
        steps = safe_int(goal.get("steps"), 1, 200000)
        minutes = safe_int(goal.get("minutes"), 1, 1440)
        if kcal and steps and minutes:
            conn.execute(
                "INSERT INTO sport_goals(user_id, kcal, steps, minutes, updated_at) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET kcal = excluded.kcal, steps = excluded.steps, "
                "minutes = excluded.minutes, updated_at = excluded.updated_at",
                (uid, kcal, steps, minutes, db.now()),
            )

        imported = 0
        history = sport.get("history") or {}
        if isinstance(history, dict):
            for date, item in history.items():
                day = safe_day(date)
                if day is None or not isinstance(item, dict):
                    continue
                conn.execute(
                    "INSERT INTO sport_records(user_id, date, kcal, steps, minutes, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(user_id, date) DO UPDATE SET kcal = excluded.kcal, "
                    "steps = excluded.steps, minutes = excluded.minutes",
                    (uid, day[:10], int(safe_float(item.get("kcal"), 0, 10000) or 0),
                     int(safe_float(item.get("steps"), 0, 200000) or 0),
                     int(safe_float(item.get("minutes"), 0, 1440) or 0), db.now()),
                )
                imported += 1
        counts["sport"] = imported

    # ---- 心情 ----
    imported = 0
    mood_log = body.get("moodLog") or {}
    if isinstance(mood_log, dict):
        for date, item in mood_log.items():
            day = safe_day(date)
            if day is None or not isinstance(item, dict):
                continue
            mood = safe_text(item.get("mood"), 10)
            if mood not in MOODS:
                continue
            conn.execute(
                "INSERT INTO mood_records(user_id, date, mood, note, created_at) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(user_id, date) DO UPDATE SET mood = excluded.mood, note = excluded.note",
                (uid, day[:10], mood, safe_text(item.get("note"), 500), db.now()),
            )
            imported += 1
    counts["mood"] = imported

    # ---- 家人档案（旧 ID 加用户前缀，避免跨账号冲突）----
    member_map = {}
    imported = 0
    for index, item in enumerate(body.get("familyMembers") or []):
        if not isinstance(item, dict):
            continue
        old_id = safe_text(item.get("id"), 40, "m%d" % index)
        new_id_value = "m%d-%s" % (uid, old_id)
        relation = safe_text(item.get("relation"), 20, "家人")
        conn.execute(
            "INSERT INTO family_members(id, user_id, relation, name, age, conditions, medications, "
            "emergency_name, emergency_phone, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (new_id_value, uid, relation, safe_text(item.get("name"), 30),
             int(safe_float(item.get("age"), 0, 150) or 0),
             safe_text(item.get("conditions"), 200), safe_text(item.get("medications"), 200),
             safe_text(item.get("emergencyName"), 50), safe_text(item.get("emergencyPhone"), 30),
             db.now(), db.now()),
        )
        member_map[old_id] = new_id_value
        imported += 1
    counts["familyMembers"] = imported

    # ---- 家人健康记录 ----
    imported = 0
    for index, item in enumerate(body.get("familyRecords") or []):
        if not isinstance(item, dict):
            continue
        member_id = member_map.get(safe_text(item.get("memberId"), 40))
        if not member_id:
            continue
        date = safe_day(item.get("date"), db.today())
        record_id = "f%d-%d" % (uid, index)
        conn.execute(
            "INSERT INTO family_records(id, user_id, member_id, type, date, content, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (record_id, uid, member_id, safe_text(item.get("type"), 20, "体检"),
             (date or db.today())[:10], safe_text(item.get("content"), 200), db.now()),
        )
        imported += 1
    counts["familyRecords"] = imported

    # ---- 关怀提醒 ----
    imported = 0
    for index, item in enumerate(body.get("reminders") or []):
        if not isinstance(item, dict):
            continue
        title = safe_text(item.get("title"), 60)
        date = safe_day(item.get("date"))
        if not title or date is None:
            continue
        old_member = safe_text(item.get("memberId"), 40)
        reminder_id = "r%d-%d" % (uid, index)
        conn.execute(
            "INSERT INTO reminders(id, user_id, member_id, title, date, done, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (reminder_id, uid, member_map.get(old_member), title, date[:10],
             1 if to_bool(item.get("done")) else 0, db.now(), db.now()),
        )
        imported += 1
    counts["reminders"] = imported

    # ---- 常用提醒 ----
    imported = 0
    existing = {row["text"] for row in conn.execute(
        "SELECT text FROM quick_reminders WHERE user_id = ?", (uid,))}
    sort = conn.execute(
        "SELECT COALESCE(MAX(sort), -1) + 1 AS next FROM quick_reminders WHERE user_id = ?",
        (uid,),
    ).fetchone()["next"]
    for index, item in enumerate(body.get("quickReminders") or []):
        if not isinstance(item, dict):
            continue
        label = safe_text(item.get("label"), 30)
        text = safe_text(item.get("text"), 100) or label
        if not text or text in existing:
            continue
        conn.execute(
            "INSERT INTO quick_reminders(id, user_id, label, text, sort, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("q%d-%d" % (uid, index), uid, label or text, text, sort, db.now()),
        )
        existing.add(text)
        sort += 1
        imported += 1
    counts["quickReminders"] = imported

    return {"ok": True, "imported": counts}


@route("GET", "/api/sync/export")
def sync_export(ctx):
    """导出当前账号的全部业务数据，便于换机或备份。"""
    conn = ctx.conn
    uid = ctx.user_id

    weight_rows = conn.execute(
        "SELECT * FROM weight_records WHERE user_id = ? ORDER BY date", (uid,)
    ).fetchall()
    vital_rows = conn.execute(
        "SELECT type, date, text FROM vital_records WHERE user_id = ? ORDER BY date", (uid,)
    ).fetchall()
    vitals = {name: [] for name in VITAL_TYPES}
    for row in vital_rows:
        vitals[row["type"]].append({"date": row["date"], "text": row["text"] or ""})

    meal_rows = conn.execute(
        "SELECT * FROM meal_records WHERE user_id = ? ORDER BY date, id", (uid,)
    ).fetchall()
    mood_rows = conn.execute(
        "SELECT * FROM mood_records WHERE user_id = ? ORDER BY date", (uid,)
    ).fetchall()
    sport_rows = conn.execute(
        "SELECT * FROM sport_records WHERE user_id = ? ORDER BY date", (uid,)
    ).fetchall()
    sleep_rows = conn.execute(
        "SELECT * FROM sleep_records WHERE user_id = ? ORDER BY date", (uid,)
    ).fetchall()
    member_rows = conn.execute(
        "SELECT * FROM family_members WHERE user_id = ? ORDER BY created_at", (uid,)
    ).fetchall()
    record_rows = conn.execute(
        "SELECT * FROM family_records WHERE user_id = ? ORDER BY date", (uid,)
    ).fetchall()
    reminder_rows = conn.execute(
        "SELECT * FROM reminders WHERE user_id = ? ORDER BY date", (uid,)
    ).fetchall()
    quick_rows = conn.execute(
        "SELECT * FROM quick_reminders WHERE user_id = ? ORDER BY sort", (uid,)
    ).fetchall()
    report_rows = conn.execute(
        "SELECT * FROM report_records WHERE user_id = ? ORDER BY date", (uid,)
    ).fetchall()

    profile_row = read_profile(conn, uid)
    preference_row = conn.execute(
        "SELECT * FROM preferences WHERE user_id = ?", (uid,)
    ).fetchone()
    female_row = conn.execute(
        "SELECT * FROM female_profiles WHERE user_id = ?", (uid,)
    ).fetchone()
    female_rows = conn.execute(
        "SELECT * FROM female_status WHERE user_id = ? ORDER BY date", (uid,)
    ).fetchall()

    return {
        "exportedAt": db.now(),
        "user": auth.public_user(ctx.user),
        "profile": profile_json(profile_row),
        "preferences": preference_json(preference_row),
        "settings": {
            "dietActivity": db.state_get(conn, uid, "dietActivity", 1.375),
            "bp": db.state_get(conn, uid, "bp"),
            "glucose": db.state_get(conn, uid, "glucose"),
        },
        "weightHistory": [weight_json(row) for row in weight_rows],
        "vitalsHistory": vitals,
        "mealLog": [meal_json(row) for row in meal_rows],
        "moodLog": {row["date"]: {"mood": row["mood"], "note": row["note"] or ""}
                    for row in mood_rows},
        "sleepLog": [sleep_json(row) for row in sleep_rows],
        "sport": {
            "goal": sport_goal(conn, uid),
            "history": {row["date"]: {"kcal": row["kcal"], "steps": row["steps"],
                                      "minutes": row["minutes"]} for row in sport_rows},
        },
        "familyMembers": [member_json(row) for row in member_rows],
        "familyRecords": [family_record_json(row) for row in record_rows],
        "reminders": [reminder_json(row) for row in reminder_rows],
        "quickReminders": [quick_json(row) for row in quick_rows],
        "reports": [report_json(row) for row in report_rows],
        "female": {
            "profile": {
                "periodDays": female_row["period_days"] if female_row else 5,
                "cycleDays": female_row["cycle_days"] if female_row else 28,
                "lastPeriodStart": (female_row["last_period_start"] or "") if female_row else "",
            },
            "status": [female_status_json(row) for row in female_rows],
        },
    }
