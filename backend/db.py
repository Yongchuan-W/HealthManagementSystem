"""SQLite 数据层：连接、建表与通用小工具。

数据文件：项目根目录下的 health.db（自动创建）。
模块与表的对应关系：

    账号与会话   users / sessions
    个人档案     profiles
    体重趋势     weight_records      （对应前端 weightHistory）
    体征记录     vital_records       （体脂 / BMI / 血压 / 血糖，对应 vitalsHistory）
    最新体征     user_state          （键 bp / glucose / dietActivity / vitalsVisibility）
    饮食记录     meal_records        （对应 mealLog）
    运动         sport_goals + sport_records（对应 sport.goal / sport.history）
    心情         mood_records        （对应 moodLog）
    睡眠         sleep_records
    关怀提醒     reminders           （对应 reminders）
    常用提醒     quick_reminders     （对应 quickReminders）
    家人         family_members + family_records
    上传文件     uploads             （文件本体存 uploads/ 目录）
    AI 对话      ai_messages         （预留给后续接入大模型）
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "health.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    account       TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    salt          TEXT    NOT NULL,
    nickname      TEXT,
    created_at    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token      TEXT    PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT    NOT NULL,
    expires_at TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS profiles (
    user_id      INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    nickname     TEXT,
    name         TEXT,
    avatar       INTEGER DEFAULT 0,
    avatar_image TEXT,
    gender       TEXT,
    height       REAL,
    weight       REAL,
    birthday     TEXT,
    phone        TEXT,
    updated_at   TEXT
);

CREATE TABLE IF NOT EXISTS weight_records (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date       TEXT    NOT NULL,
    weight     REAL    NOT NULL,
    created_at TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_weight_user_date ON weight_records(user_id, date);

CREATE TABLE IF NOT EXISTS vital_records (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type       TEXT    NOT NULL,          -- fat / bmi / bp / glucose
    date       TEXT    NOT NULL,          -- YYYY-MM-DD HH:MM
    value      REAL,
    value2     REAL,
    text       TEXT,
    created_at TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_vital_user_type ON vital_records(user_id, type, date);

CREATE TABLE IF NOT EXISTS meal_records (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date       TEXT    NOT NULL,
    meal       TEXT    NOT NULL,          -- 早餐 / 午餐 / 晚餐 / 加餐
    text       TEXT    NOT NULL,
    kcal       REAL    DEFAULT 0,
    protein    REAL    DEFAULT 0,
    carb       REAL    DEFAULT 0,
    fat        REAL    DEFAULT 0,
    fiber      REAL    DEFAULT 0,
    image      TEXT,
    created_at TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_meal_user_date ON meal_records(user_id, date);

CREATE TABLE IF NOT EXISTS sport_goals (
    user_id    INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    kcal       INTEGER NOT NULL DEFAULT 500,
    steps      INTEGER NOT NULL DEFAULT 8000,
    minutes    INTEGER NOT NULL DEFAULT 60,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS sport_records (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date       TEXT    NOT NULL,
    kcal       INTEGER DEFAULT 0,
    steps      INTEGER DEFAULT 0,
    minutes    INTEGER DEFAULT 0,
    created_at TEXT    NOT NULL,
    UNIQUE(user_id, date)
);

CREATE TABLE IF NOT EXISTS mood_records (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date       TEXT    NOT NULL,
    mood       TEXT    NOT NULL,
    note       TEXT,
    created_at TEXT    NOT NULL,
    UNIQUE(user_id, date)
);

CREATE TABLE IF NOT EXISTS sleep_records (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date       TEXT    NOT NULL,
    hours      REAL    DEFAULT 0,
    quality    TEXT,
    note       TEXT,
    created_at TEXT    NOT NULL,
    UNIQUE(user_id, date)
);

CREATE TABLE IF NOT EXISTS reminders (
    id         TEXT    PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    member_id  TEXT,
    title      TEXT    NOT NULL,
    date       TEXT    NOT NULL,
    done       INTEGER NOT NULL DEFAULT 0,
    created_at TEXT,
    updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_reminder_user_date ON reminders(user_id, date);

CREATE TABLE IF NOT EXISTS quick_reminders (
    id         TEXT    PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    label      TEXT    NOT NULL,
    text       TEXT    NOT NULL,
    sort       INTEGER DEFAULT 0,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS family_members (
    id              TEXT    PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    relation        TEXT    NOT NULL,
    name            TEXT,
    age             INTEGER,
    conditions      TEXT,
    medications     TEXT,
    emergency_name  TEXT,
    emergency_phone TEXT,
    created_at      TEXT,
    updated_at      TEXT
);

CREATE TABLE IF NOT EXISTS family_records (
    id         TEXT    PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    member_id  TEXT    NOT NULL,
    type       TEXT    NOT NULL,
    date       TEXT    NOT NULL,
    content    TEXT,
    created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_family_record_member ON family_records(user_id, member_id, date);

CREATE TABLE IF NOT EXISTS uploads (
    id            TEXT    PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename      TEXT    NOT NULL,
    original_name TEXT,
    mime          TEXT,
    size          INTEGER DEFAULT 0,
    created_at    TEXT
);

CREATE TABLE IF NOT EXISTS ai_messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role       TEXT    NOT NULL,          -- user / assistant
    content    TEXT    NOT NULL,
    created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_ai_user ON ai_messages(user_id, id);

CREATE TABLE IF NOT EXISTS user_state (
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key        TEXT    NOT NULL,
    value      TEXT    NOT NULL,          -- JSON 字符串
    updated_at TEXT,
    PRIMARY KEY(user_id, key)
);

-- 首次填写与饮食偏好（健康目标、口味、忌口等）
CREATE TABLE IF NOT EXISTS preferences (
    user_id            INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    sleep_quality      TEXT,
    exercise_frequency TEXT,
    goal               TEXT,
    conditions         TEXT,              -- JSON 数组
    taste              TEXT,
    diet_type          TEXT,
    restrictions       TEXT,              -- JSON 数组
    updated_at         TEXT
);

-- 女性健康档案：周期设置 + 每日状态标签
CREATE TABLE IF NOT EXISTS female_profiles (
    user_id           INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    period_days       INTEGER DEFAULT 5,
    cycle_days        INTEGER DEFAULT 28,
    last_period_start TEXT,
    updated_at        TEXT
);

CREATE TABLE IF NOT EXISTS female_status (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date       TEXT    NOT NULL,
    tags       TEXT,                      -- JSON 数组
    note       TEXT,
    created_at TEXT,
    UNIQUE(user_id, date)
);

-- 体检报告记录（图片识别后同步的指标）
CREATE TABLE IF NOT EXISTS report_records (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date       TEXT    NOT NULL,
    weight     REAL,
    fat        REAL,
    systolic   REAL,
    diastolic  REAL,
    glucose    REAL,
    image_url  TEXT,
    created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_report_user_date ON report_records(user_id, date);
"""


def init_db():
    """创建数据目录与所有表，可重复调用。"""
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA)
        _migrate(conn)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.commit()
    finally:
        conn.close()


def _migrate(conn):
    """对已存在的旧库补齐新增字段。"""
    meal_columns = {row[1] for row in conn.execute("PRAGMA table_info(meal_records)")}
    if meal_columns and "image" not in meal_columns:
        conn.execute("ALTER TABLE meal_records ADD COLUMN image TEXT")


@contextmanager
def session():
    """每个请求独立连接；正常结束提交，异常回滚。"""
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------- 通用小工具 ----------

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today():
    return datetime.now().strftime("%Y-%m-%d")


def new_id():
    """短随机 ID，与前端现有的字符串 ID（m1 / r1）兼容。"""
    return uuid.uuid4().hex[:12]


def row_to_dict(row):
    return dict(row) if row is not None else None


def rows_to_dicts(rows):
    return [dict(item) for item in rows]


def state_get(conn, user_id, key, default=None):
    import json
    row = conn.execute(
        "SELECT value FROM user_state WHERE user_id = ? AND key = ?", (user_id, key)
    ).fetchone()
    if row is None:
        return default
    try:
        return json.loads(row["value"])
    except (TypeError, ValueError):
        return default


def state_set(conn, user_id, key, value):
    import json
    conn.execute(
        "INSERT INTO user_state(user_id, key, value, updated_at) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
        (user_id, key, json.dumps(value, ensure_ascii=False), now()),
    )


def state_delete(conn, user_id, key):
    conn.execute("DELETE FROM user_state WHERE user_id = ? AND key = ?", (user_id, key))
