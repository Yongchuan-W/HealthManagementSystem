# -*- coding: utf-8 -*-
"""
健康管理系统 · 启动入口
================================================
前端（HTML / CSS / JS / 图片）已拆分到 frontend/ 目录，
后端接口拆分到 backend/ 包，本文件只负责：
  1. 选择端口与监听地址（支持 HTTP / HTTPS）
  2. 初始化数据库与账号
  3. 把「手机访问地址」注入后端处理器
  4. 启动 HTTP 服务

运行方式（无需安装任何第三方库，仅使用 Python 标准库）：
  - VS Code 打开本文件，点击右上角 ▶ 运行；
  - 或在终端执行：python web.py
  - 启动后浏览器会自动打开 http://127.0.0.1:8000/
  - 手机与电脑连接同一 Wi-Fi 后，可通过终端显示的局域网地址登录

停止服务：在终端按 Ctrl + C。
"""

import os
import socket
import ssl
import threading
import webbrowser
from http.server import ThreadingHTTPServer

from backend import auth
from backend.app import HealthAppHandler, prepare


def find_free_port(start=8000, end=8100):
    """从 8000 开始查找一个空闲端口，避免端口被占用导致启动失败。"""
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue
    raise RuntimeError("8000-8100 端口均被占用，请手动修改端口范围")


def get_lan_ip():
    """获取本机在局域网中的 IP，供手机访问。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # 不会真正发送数据，仅用于让系统选择出口网卡
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def build_ssl_context():
    """ai_local.env 里配置了 HM_TLS_CERT / HM_TLS_KEY 时启用 HTTPS。"""
    if not auth.tls_enabled():
        return None
    cert = os.environ.get("HM_TLS_CERT", "").strip()
    key = os.environ.get("HM_TLS_KEY", "").strip()
    if not cert or not key:
        return None
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert, key)
    return context


def main():
    # 服务器部署时用 HM_PORT 固定端口；本机未配置时从 8000 起自动找空闲端口
    port = int(os.environ.get("HM_PORT", "0") or 0) or find_free_port()
    tls = build_ssl_context()
    scheme = "https" if tls else "http"
    local_url = "%s://127.0.0.1:%d/" % (scheme, port)

    lan_ip = get_lan_ip()
    mobile_url = ("%s://%s:%d/" % (scheme, lan_ip, port)
                  if lan_ip != "127.0.0.1" else local_url)

    # 对外访问地址：配置了域名（如 https://health.example.xyz）时优先展示它
    public_url = os.environ.get("HM_PUBLIC_URL", "").strip()
    if public_url:
        mobile_url = public_url if public_url.endswith("/") else public_url + "/"

    # 初始化数据库，并按白名单同步指定账号
    prepare()

    # 把手机访问地址注入后端处理器（前端页面里用到）
    HealthAppHandler.mobile_url = mobile_url

    # 本机使用时自动打开浏览器；服务器部署（HM_NO_BROWSER=1 或非 Windows）不弹窗
    if os.name == "nt" and os.environ.get("HM_NO_BROWSER", "") != "1":
        threading.Timer(0.8, lambda: webbrowser.open(local_url)).start()

    # 监听地址：默认 0.0.0.0，手机与电脑在同一 Wi-Fi 下即可访问；
    # 服务器部署可设 HM_BIND=127.0.0.1，只允许本机（Cloudflare 隧道）访问，
    # 公网 IP:端口 将不再对外开放
    bind_host = os.environ.get("HM_BIND", "").strip() or "0.0.0.0"
    server = ThreadingHTTPServer((bind_host, port), HealthAppHandler)
    if tls:
        server.socket = tls.wrap_socket(server.socket, server_side=True)
    print("=" * 58)
    print("健康管理系统已启动")
    print("电脑访问：", local_url)
    print("手机访问：", mobile_url, "（需连接同一 Wi-Fi）")
    if public_url:
        print("公网访问：", public_url)
    print("接口地址：", local_url + "api/health")
    print("数据文件：health.db（与本文件同目录）")
    if tls:
        print("已启用 HTTPS：首次访问若提示证书不受信任，确认是本机后再继续")
    else:
        print("提示：当前为 HTTP，同一 Wi-Fi 下的流量未加密；可在 ai_local.env 配置证书启用 HTTPS")
    print("提示：若 Windows 防火墙弹窗，请允许 Python 访问专用网络")
    print("按 Ctrl + C 停止服务")
    print("=" * 58)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
