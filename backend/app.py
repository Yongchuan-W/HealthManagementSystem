"""HTTP 服务：把页面、上传文件与 /api/* 接口合并到一个处理器。

由 web.py 启动时注入页面 HTML（已替换 AI 图标 data URI），
因此 `python web.py` 仍然是唯一入口，无需安装任何依赖。
"""

from __future__ import annotations

import json
import mimetypes
import os
import sqlite3
import traceback
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, unquote, urlparse

from . import auth, db, routes
from .errors import ApiError

MAX_BODY_BYTES = 14 * 1024 * 1024
API_PREFIX = "/api"


class HealthAppHandler(BaseHTTPRequestHandler):
    """页面 + 静态上传资源 + JSON 接口。"""

    server_version = "HealthSystem/2.0"
    protocol_version = "HTTP/1.1"

    # 由 web.py 在启动前写入
    page_html = ""
    mobile_url = "http://127.0.0.1:8000/"

    # ---------- 各 HTTP 方法 ----------
    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def do_PUT(self):
        self._handle("PUT")

    def do_PATCH(self):
        self._handle("PATCH")

    def do_DELETE(self):
        self._handle("DELETE")

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.send_header("Allow", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
        self.send_header("Content-Length", "0")
        self.end_headers()

    # ---------- 分发 ----------
    def _handle(self, method):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        query = parse_qs(parsed.query, keep_blank_values=True)

        if path in ("/", "/index.html"):
            self._serve_page()
        elif path == "/favicon.ico":
            self._send_body(204, b"", "image/x-icon")
        elif path.startswith("/uploads/"):
            self._serve_upload(path)
        elif path == API_PREFIX or path.startswith(API_PREFIX + "/"):
            self._handle_api(method, path, query)
        else:
            self._send_json(404, {"ok": False, "error": "页面不存在", "code": "not_found"})

    def _serve_page(self):
        html = self.page_html.replace("__MOBILE_URL__", self.mobile_url)
        self._send_body(200, html.encode("utf-8"), "text/html; charset=utf-8",
                        extra=[("Cache-Control", "no-store")])

    def _serve_upload(self, path):
        name = os.path.basename(path[len("/uploads/"):])
        if not name or name.startswith("."):
            self._send_json(404, {"ok": False, "error": "文件不存在", "code": "not_found"})
            return

        file_path = os.path.join(db.UPLOAD_DIR, name)
        if not os.path.isfile(file_path):
            self._send_json(404, {"ok": False, "error": "文件不存在", "code": "not_found"})
            return

        mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
        with open(file_path, "rb") as handle:
            data = handle.read()
        self._send_body(200, data, mime, extra=[("Cache-Control", "public, max-age=86400")])

    def _handle_api(self, method, path, query):
        try:
            raw_body = self._read_body()
            body = self._parse_json(raw_body)
            token = auth.token_from_headers(self.headers)

            with db.session() as conn:
                user = auth.user_from_token(conn, token)
                status, payload = routes.dispatch(
                    conn, method, path,
                    user=user, token=token, body=body, query=query,
                    raw_body=raw_body, headers=self.headers,
                )

            cookie = None
            if isinstance(payload, dict) and "cookie" in payload:
                cookie = payload.pop("cookie")
            if isinstance(payload, dict) and "ok" not in payload:
                payload["ok"] = True

            extra = [("Cache-Control", "no-store")]
            if cookie:
                extra.append(("Set-Cookie", cookie))
            self._send_json(status, payload, extra=extra)

        except ApiError as error:
            self._send_json(
                error.status,
                {"ok": False, "error": error.message, "code": error.code},
            )
        except sqlite3.IntegrityError as error:
            print("[DB] 约束错误：", error)
            self._send_json(409, {"ok": False, "error": "数据冲突，请检查输入", "code": "conflict"})
        except (ValueError, UnicodeDecodeError) as error:
            self._send_json(400, {"ok": False, "error": "请求格式有误：%s" % error, "code": "bad_request"})
        except Exception as error:  # noqa: BLE001 - 兜底，避免服务被单个请求打断
            traceback.print_exc()
            self._send_json(500, {"ok": False, "error": "服务器内部错误：%s" % error,
                                  "code": "internal_error"})

    # ---------- 请求体 ----------
    def _read_body(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise ApiError(400, "请求头 Content-Length 无效")
        if length > MAX_BODY_BYTES:
            raise ApiError(413, "请求内容超过 14MB")
        if length <= 0:
            return b""
        return self.rfile.read(length)

    def _parse_json(self, raw_body):
        if not raw_body:
            return {}
        content_type = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if content_type and content_type != "application/json":
            return {}
        try:
            return json.loads(raw_body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise ApiError(400, "请求体不是合法的 JSON")

    # ---------- 响应 ----------
    def _send_json(self, status, payload, extra=None):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = [("Cache-Control", "no-store")]
        headers.extend(extra or [])
        self._send_body(status, body, "application/json; charset=utf-8", extra=headers)

    def _send_body(self, status, body, content_type, extra=None):
        self.send_response(status)
        self._send_cors_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        for key, value in (extra or []):
            self.send_header(key, value)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _send_cors_headers(self):
        origin = self.headers.get("Origin")
        if not origin:
            return
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Access-Control-Allow-Headers",
                         "Content-Type, Authorization, X-File-Name")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")

    def log_message(self, fmt, *args):
        print("[HTTP] " + fmt % args)


def prepare():
    """初始化数据库并创建演示账号，返回是否成功。"""
    db.init_db()
    with db.session() as conn:
        auth.ensure_demo_user(conn)
    return True
