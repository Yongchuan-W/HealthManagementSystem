"""HTTP 服务：把页面、上传文件与 /api/* 接口合并到一个处理器。

由 web.py 启动时注入页面 HTML（已替换 AI 图标 data URI），
因此 `python web.py` 仍然是唯一入口，无需安装任何依赖。
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import sqlite3
import time
import traceback
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, unquote, urlparse

from . import ai, auth, db, routes, telemetry
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
        elif path == "/api/ai/report-plan/stream" and method == "POST":
            self._handle_report_stream()
        elif path.startswith("/uploads/"):
            self._serve_upload(path)
        elif path.startswith("/assets/"):
            self._serve_asset(path)
        elif path == API_PREFIX or path.startswith(API_PREFIX + "/"):
            self._handle_api(method, path, query)
        else:
            self._send_json(404, {"ok": False, "error": "页面不存在", "code": "not_found"})

    def _serve_page(self):
        html = self.page_html.replace("__MOBILE_URL__", self.mobile_url)
        body = html.encode("utf-8")
        # 整页 400KB+，用 ETag 让浏览器复用时只做一次校验，不必重复下载
        etag = '"%s"' % hashlib.md5(body).hexdigest()
        if (self.headers.get("If-None-Match") or "").strip() == etag:
            self.send_response(304)
            self.send_header("ETag", etag)
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self._send_body(200, body, "text/html; charset=utf-8",
                        extra=[("Cache-Control", "no-cache"), ("ETag", etag)])

    def _serve_asset(self, path):
        """科普资讯封面等静态图片：公开访问，浏览器缓存一周。"""
        name = os.path.basename(path[len("/assets/"):])
        if not name or name.startswith("."):
            self._send_json(404, {"ok": False, "error": "文件不存在", "code": "not_found"})
            return

        file_path = os.path.join(db.BASE_DIR, "assets", "news", name)
        if not os.path.isfile(file_path):
            self._send_json(404, {"ok": False, "error": "文件不存在", "code": "not_found"})
            return

        types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".svg": "image/svg+xml",
        }
        with open(file_path, "rb") as handle:
            body = handle.read()
        self._send_body(
            200, body, types.get(os.path.splitext(name)[1].lower(), "application/octet-stream"),
            extra=[("Cache-Control", "public, max-age=604800")],
        )

    def _serve_upload(self, path):
        name = os.path.basename(path[len("/uploads/"):])
        if not name or name.startswith("."):
            self._send_json(404, {"ok": False, "error": "文件不存在", "code": "not_found"})
            return

        # 图片同样要求登录，并且只允许上传者本人读取
        token = auth.token_from_headers(self.headers)
        with db.session() as conn:
            user = auth.user_from_token(conn, token)
            if user is None:
                self._send_json(401, {"ok": False, "error": "请先登录", "code": "unauthorized"})
                return
            row = conn.execute(
                "SELECT 1 FROM uploads WHERE filename = ? AND user_id = ?",
                (name, user["id"]),
            ).fetchone()
        if row is None:
            self._send_json(404, {"ok": False, "error": "文件不存在", "code": "not_found"})
            return

        file_path = os.path.join(db.UPLOAD_DIR, name)
        if not os.path.isfile(file_path):
            self._send_json(404, {"ok": False, "error": "文件不存在", "code": "not_found"})
            return

        mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
        with open(file_path, "rb") as handle:
            data = handle.read()
        self._send_body(200, data, mime, extra=[("Cache-Control", "private, max-age=86400")])

    def _handle_api(self, method, path, query):
        started = time.time()
        status = 500
        current_user = None
        try:
            raw_body = self._read_body()
            body = self._parse_json(raw_body)
            token = auth.token_from_headers(self.headers)

            with db.session() as conn:
                user = auth.user_from_token(conn, token)
                current_user = user
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
            status = error.status
            if status >= 500:
                telemetry.record_error("接口异常", path, error.message)
            self._send_json(
                status,
                {"ok": False, "error": error.message, "code": error.code},
            )
        except sqlite3.IntegrityError as error:
            status = 409
            print("[DB] 约束错误：", error)
            telemetry.record_error("数据库约束冲突", path, str(error))
            self._send_json(409, {"ok": False, "error": "数据冲突，请检查输入", "code": "conflict"})
        except (ValueError, UnicodeDecodeError) as error:
            status = 400
            self._send_json(400, {"ok": False, "error": "请求格式有误：%s" % error, "code": "bad_request"})
        except Exception:  # noqa: BLE001 - 兜底，避免服务被单个请求打断
            # 详细堆栈只写服务端日志，返回给前端的内容不暴露异常与路径
            traceback.print_exc()
            status = 500
            telemetry.record_error("未捕获异常", path, telemetry.exception_text())
            self._send_json(500, {"ok": False, "error": "服务器开小差了，请稍后再试",
                                  "code": "internal_error"})
        finally:
            telemetry.record_request(
                method, path, status, (time.time() - started) * 1000,
                current_user["id"] if current_user is not None else None,
            )

    # ---------- SSE：体检报告解读 ----------
    def _handle_report_stream(self):
        """流式接口单独处理：先发 SSE 头，再把 OCR/工具/生成进度边算边推。"""
        started = time.time()
        current_user = None
        stream_started = False
        status = 500
        emit = None

        def safe_emit(event, payload):
            if emit is None:
                return
            try:
                emit(event, payload)
            except (BrokenPipeError, ConnectionResetError):
                pass

        try:
            raw_body = self._read_body()
            body = self._parse_json(raw_body)
            token = auth.token_from_headers(self.headers)

            with db.session() as conn:
                user = auth.user_from_token(conn, token)
                current_user = user
                if user is None:
                    status = 401
                    self._send_json(401, {"ok": False, "error": "请先登录",
                                          "code": "unauthorized"})
                    return

                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("X-Accel-Buffering", "no")
                self.send_header("Connection", "close")
                self.end_headers()
                self.close_connection = True
                stream_started = True
                status = 200

                def emit(event, payload):
                    chunk = "event: %s\ndata: %s\n\n" % (
                        event, json.dumps(payload, ensure_ascii=False))
                    self.wfile.write(chunk.encode("utf-8"))
                    self.wfile.flush()

                try:
                    routes.stream_report_plan(conn, user, body, emit)
                    emit("done", {"ok": True})
                except ApiError as error:
                    safe_emit("error", {"ok": False, "error": error.message, "code": error.code})
                except ai.AiError as error:
                    safe_emit("error", {"ok": False, "error": str(error), "code": "ai_failed"})
                except Exception:  # noqa: BLE001 - 已发头，只能把错误写进流里
                    traceback.print_exc()
                    telemetry.record_error("解读流式异常", "/api/ai/report-plan/stream",
                                           telemetry.exception_text())
                    safe_emit("error", {"ok": False, "error": "AI 解读失败，请稍后再试",
                                        "code": "internal_error"})

        except ApiError as error:
            status = error.status
            if stream_started:
                safe_emit("error", {"ok": False, "error": error.message, "code": error.code})
            else:
                self._send_json(status, {"ok": False, "error": error.message,
                                         "code": error.code})
        except (ValueError, UnicodeDecodeError) as error:
            status = 400
            if stream_started:
                safe_emit("error", {"ok": False, "error": "请求格式有误", "code": "bad_request"})
            else:
                self._send_json(400, {"ok": False, "error": "请求格式有误：%s" % error,
                                      "code": "bad_request"})
        except Exception:  # noqa: BLE001
            traceback.print_exc()
            status = 500
            if not stream_started:
                self._send_json(500, {"ok": False, "error": "服务器开小差了，请稍后再试",
                                      "code": "internal_error"})
        finally:
            telemetry.record_request(
                "POST", "/api/ai/report-plan/stream", status,
                (time.time() - started) * 1000,
                current_user["id"] if current_user is not None else None,
            )

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
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        for key, value in (extra or []):
            self.send_header(key, value)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def log_message(self, fmt, *args):
        print("[HTTP] " + fmt % args)


def prepare():
    """初始化数据库，并按白名单创建指定账号（未配置时创建演示账号）。"""
    db.init_db()
    db.backup_database()
    with db.session() as conn:
        if auth.allowed_accounts():
            auth.ensure_allowed_users(conn)
    return True
