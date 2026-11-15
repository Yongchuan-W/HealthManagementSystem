"""邮件发送：用于「忘记密码」的验证码。

使用标准库 smtplib，支持 QQ 邮箱 / 163 / 企业邮箱等。

需要在 ai_local.env 中配置（示例为 QQ 邮箱）：
    HM_MAIL_HOST=smtp.qq.com
    HM_MAIL_PORT=465
    HM_MAIL_USER=你的QQ邮箱
    HM_MAIL_PASS=邮箱授权码（不是登录密码）
    HM_MAIL_FROM=可选，默认与 HM_MAIL_USER 相同

端口 465 走 SSL；587 走 STARTTLS。
"""

from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr


def config():
    """返回邮件配置，未配置完整时返回 None。"""
    host = os.environ.get("HM_MAIL_HOST", "").strip()
    user = os.environ.get("HM_MAIL_USER", "").strip()
    password = os.environ.get("HM_MAIL_PASS", "").strip()
    if not (host and user and password):
        return None
    try:
        port = int(os.environ.get("HM_MAIL_PORT", "") or 465)
    except ValueError:
        port = 465
    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "from": os.environ.get("HM_MAIL_FROM", "").strip() or user,
    }


def is_configured():
    return config() is not None


def send_code(to_email, code, minutes=10):
    """发送验证码邮件，失败时抛出异常。"""
    settings = config()
    if settings is None:
        raise RuntimeError("邮件服务未配置")

    message = EmailMessage()
    message["Subject"] = "健康管理系统 · 密码重置验证码"
    message["From"] = formataddr(("健康管理系统", settings["from"]))
    message["To"] = to_email
    message.set_content(
        "你的验证码是：%s　　10 分钟内有效\n\n"
        "如果不是你本人操作，请忽略这封邮件，你的密码不会被修改。\n\n"
        "—— 健康管理系统" % code
    )

    if settings["port"] == 465:
        with smtplib.SMTP_SSL(
            settings["host"], settings["port"], timeout=15,
            context=ssl.create_default_context(),
        ) as server:
            server.login(settings["user"], settings["password"])
            server.send_message(message)
    else:
        with smtplib.SMTP(settings["host"], settings["port"], timeout=15) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(settings["user"], settings["password"])
            server.send_message(message)
