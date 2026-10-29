"""账号与会话。

密码使用 PBKDF2-HMAC-SHA256（20 万次迭代 + 随机盐）存储，
会话使用随机 token，30 天有效；token 同时支持 Cookie 与
`Authorization: Bearer <token>` 两种携带方式。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from urllib.parse import unquote

from . import db
from .errors import ApiError

PBKDF2_ITERATIONS = 200_000
SESSION_DAYS = 30
TOKEN_COOKIE = "hm_token"

DEFAULT_QUICK_REMINDERS = [
    ("测量血压", "提醒家人测量血压"),
    ("按时吃药", "提醒家人按时吃药"),
    ("陪伴散步", "陪家人散步 30 分钟"),
    ("复诊体检", "预约复诊 / 体检"),
    ("多喝水", "提醒家人多喝水"),
    ("注意保暖", "提醒家人注意保暖"),
]


# ---------- 密码 ----------

def _digest(password, salt):
    return base64.b64encode(
        hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    ).decode()


def hash_password(password):
    """返回 (哈希, 盐)，均为 base64 文本。"""
    salt = secrets.token_bytes(16)
    return _digest(password, salt), base64.b64encode(salt).decode()


def verify_password(password, password_hash, salt_b64):
    try:
        salt = base64.b64decode(salt_b64)
    except (TypeError, ValueError):
        return False
    return hmac.compare_digest(_digest(password, salt), password_hash)


# ---------- 入参校验 ----------

def clean_account(value):
    account = str(value or "").strip()
    if len(account) < 2 or len(account) > 32:
        raise ApiError(400, "账号长度需为 2-32 个字符")
    if any(ch.isspace() for ch in account):
        raise ApiError(400, "账号不能包含空格")
    return account


def clean_password(value):
    password = str(value or "")
    if len(password) < 6 or len(password) > 64:
        raise ApiError(400, "密码长度需为 6-64 个字符")
    return password


# ---------- 会话 ----------

def _fmt(moment):
    return moment.strftime("%Y-%m-%d %H:%M:%S")


def create_session(conn, user_id):
    conn.execute("DELETE FROM sessions WHERE expires_at < ?", (db.now(),))
    token = secrets.token_urlsafe(32)
    created = datetime.now()
    conn.execute(
        "INSERT INTO sessions(token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (token, user_id, _fmt(created), _fmt(created + timedelta(days=SESSION_DAYS))),
    )
    return token


def cookie_header(token):
    return "%s=%s; Path=/; Max-Age=%d; HttpOnly; SameSite=Lax" % (
        TOKEN_COOKIE, token, SESSION_DAYS * 86400)


def clear_cookie_header():
    return "%s=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax" % TOKEN_COOKIE


def token_from_headers(headers):
    auth = headers.get("Authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()

    cookie = headers.get("Cookie") or ""
    for part in cookie.split(";"):
        name, _, value = part.strip().partition("=")
        if name == TOKEN_COOKIE and value:
            return unquote(value)
    return None


def user_from_token(conn, token):
    if not token:
        return None

    row = conn.execute(
        "SELECT user_id, expires_at FROM sessions WHERE token = ?", (token,)
    ).fetchone()
    if row is None:
        return None

    if row["expires_at"] < db.now():
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        return None

    return conn.execute("SELECT * FROM users WHERE id = ?", (row["user_id"],)).fetchone()


def require_user(conn, token):
    user = user_from_token(conn, token)
    if user is None:
        raise ApiError(401, "登录状态已失效，请重新登录", "unauthorized")
    return user


def logout(conn, token):
    if token:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))


def public_user(user):
    return {
        "id": user["id"],
        "account": user["account"],
        "nickname": user["nickname"] or "",
        "createdAt": user["created_at"],
    }


# ---------- 注册 / 登录 ----------

def ensure_defaults(conn, user_id, nickname=""):
    """为新账号补齐档案、运动目标与常用提醒。"""
    conn.execute(
        "INSERT OR IGNORE INTO profiles(user_id, nickname, avatar, updated_at) VALUES (?, ?, 0, ?)",
        (user_id, nickname or "", db.now()),
    )
    conn.execute(
        "INSERT OR IGNORE INTO sport_goals(user_id, kcal, steps, minutes, updated_at) "
        "VALUES (?, 500, 8000, 60, ?)",
        (user_id, db.now()),
    )

    count = conn.execute(
        "SELECT COUNT(*) AS total FROM quick_reminders WHERE user_id = ?", (user_id,)
    ).fetchone()["total"]
    if count == 0:
        for index, (label, text) in enumerate(DEFAULT_QUICK_REMINDERS):
            conn.execute(
                "INSERT INTO quick_reminders(id, user_id, label, text, sort, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (db.new_id(), user_id, label, text, index, db.now()),
            )


def register(conn, account, password, nickname=""):
    account = clean_account(account)
    password = clean_password(password)

    exists = conn.execute(
        "SELECT id FROM users WHERE account = ?", (account,)
    ).fetchone()
    if exists:
        raise ApiError(409, "该账号已被注册")

    password_hash, salt = hash_password(password)
    cursor = conn.execute(
        "INSERT INTO users(account, password_hash, salt, nickname, created_at) VALUES (?, ?, ?, ?, ?)",
        (account, password_hash, salt, nickname or account, db.now()),
    )
    user_id = cursor.lastrowid
    ensure_defaults(conn, user_id, nickname or account)
    return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def login(conn, account, password):
    row = conn.execute(
        "SELECT * FROM users WHERE account = ?", (str(account or "").strip(),)
    ).fetchone()
    if row is None or not verify_password(str(password or ""), row["password_hash"], row["salt"]):
        raise ApiError(401, "账号或密码不正确", "invalid_credentials")
    return row


def change_password(conn, user, old_password, new_password, keep_token=None):
    if not verify_password(str(old_password or ""), user["password_hash"], user["salt"]):
        raise ApiError(400, "原密码不正确")
    new_password = clean_password(new_password)

    password_hash, salt = hash_password(new_password)
    conn.execute(
        "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?",
        (password_hash, salt, user["id"]),
    )
    if keep_token:
        conn.execute(
            "DELETE FROM sessions WHERE user_id = ? AND token != ?", (user["id"], keep_token)
        )


def ensure_demo_user(conn):
    """首次启动时创建演示账号 AAA / 123456。"""
    if conn.execute("SELECT id FROM users WHERE account = 'AAA'").fetchone():
        return
    register(conn, "AAA", "123456", "张三")
