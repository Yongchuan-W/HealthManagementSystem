# 健康管理系统 HealthManagementSystem

面向家庭的一站式健康记录与 AI 健康助理。饮食、运动、睡眠、体征、情绪、女性健康、家人档案与体检报告统一管理，并让大模型基于真实数据给出可执行建议。

在线演示：https://health.mymyhealth.xyz

## 功能

- 健康数据总览：核心体征、综合评分（饮食 40% + 运动 40% + BMI 20%）、异常提醒、体检报告分析
- 饮食：四个餐次、食物库、热量与三大营养素、个性化营养目标、AI 餐食识别
- 运动：类型/时长/强度记录、近 7 天柱状图、点日期补记、运动计划
- 睡眠与情绪：时长记录与近 7 天趋势
- 女性健康：经期、排卵日、易孕期推算
- 家人健康：多成员档案、血压/用药/复诊、关怀提醒
- 科普资讯：RSS 聚合、站内封面、速读摘要
- AI 健康小管家：对话、语音、图片输入，可直接写入饮食/运动/体重/睡眠记录
- 账号：注册、登录、找回密码、数据云同步、注销

## 技术架构

```text
浏览器（单页 HTML/CSS/原生 JS）
        │ HTTPS
Python 标准库 ThreadingHTTPServer
  app.py 请求处理 / 静态资源 / ETag
  routes.py 路由与业务（40+ 接口）
  auth.py PBKDF2 + 会话 + Cookie
  db.py SQLite（WAL，23 张表）
  ai.py OpenAI 兼容模型客户端
  asr.py / mailer.py / telemetry.py
        │
health.db（SQLite）  +  外部多模态模型
```

- **前端**：无框架、无构建，样式与脚本内联，单次请求即可交互
- **后端**：仅 Python 标准库，零第三方运行时依赖
- **数据**：SQLite + WAL，按用户隔离，全部参数化查询
- **AI**：OpenAI 兼容协议，切换供应商只需改 `HM_AI_API_BASE` / `HM_AI_MODEL`

## 快速开始

```bash
python web.py
# 浏览器自动打开 http://127.0.0.1:8000/
```

要求 Python 3.9+，无需 `pip install`。

手机与电脑连同一 Wi-Fi 时，用终端输出的局域网地址访问。

## 目录结构

```text
web.py              单页前端 + 启动入口
backend/            应用服务（路由、鉴权、数据库、AI、邮件、可观测）
assets/news/        科普资讯封面
backups/            SQLite 自动备份（本地生成，不提交）
ai_local.env        本地密钥配置（已在 .gitignore 中，不提交）
```

## 环境变量

复制 `.env.example` 为 `ai_local.env` 并按需填写。关键变量：

| 变量 | 说明 |
| --- | --- |
| `HM_AI_API_KEY` | 模型 API Key（必填才能使用 AI 功能） |
| `HM_AI_API_BASE` | 兼容接口地址，默认 `https://api.deepseek.com/v1` |
| `HM_AI_MODEL` | 模型名，需支持多模态才能识图 |
| `HM_PORT` / `HM_BIND` | 监听端口与地址 |
| `HM_PUBLIC_URL` | 对外地址，用于 Cookie Secure 判定 |
| `HM_MAIL_*` | 找回密码用的 SMTP 配置（可选） |
| `HM_ALLOWED_USERS` | 指定账号，格式 `账号:密码,账号:密码`（会标记为管理员） |

## 部署

```bash
# systemd 示例
[Unit]
Description=Health Management System
After=network.target

[Service]
WorkingDirectory=/opt/health
EnvironmentFile=/opt/health/ai_local.env
ExecStart=/usr/bin/python3 /opt/health/web.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now health
curl -s http://127.0.0.1:8000/api/health
```

HTTPS 建议由 Nginx 或 Cloudflare 隧道终止，应用只监听 `127.0.0.1`。

## 依赖清单

运行时不依赖任何第三方 Python 包（见 `requirements.txt`）。开发辅助脚本仅使用标准库；文档转换使用本机 Office，不构成运行依赖。

## 团队信息

| 成员 | 分工 |
| --- | --- |
| （待填写） | 产品设计、前端实现 |
| （待填写） | 后端与数据库、AI 接入 |
| （待填写） | 测试、文档、演示 |

## 说明

本项目为健康管理工具，所有建议不构成医疗诊断。涉及用药与急症请及时就医。
