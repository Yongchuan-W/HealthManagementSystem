# 健康管理系统 HealthManagementSystem

面向家庭的一站式健康记录与 AI 健康助理。饮食、运动、睡眠、体征、情绪、女性健康、家人档案与体检报告统一管理，**基于大模型 Agent 智能体读取用户真实健康档案、调用系统工具，输出可执行的个性化健康建议**。

在线演示：https://health.mymyhealth.xyz

演示视频：`健康管理系统-演示视频.mp4`（存放在项目压缩包根目录，1080p，约 5 分 46 秒，普通话讲解 + 中文字幕）

## 项目亮点

- **零第三方运行依赖**：后端仅用 Python 标准库，无需 `pip install`；前端无框架、无构建，单页内嵌 HTML/CSS/JS，一条命令即可运行
- **多模态 AI Agent**：AI 健康小管家具备档案记忆与工具调用能力，支持文本、语音、图片输入，可直接读写业务数据库，完成饮食/运动/体重/睡眠记录的自动回填，而非单纯对话问答
- **家庭多成员管理**：支持多份家人健康档案，体征、用药、复诊与关怀提醒统一维护
- **测试与安全加固闭环**：经黑盒体验走查与安全审计，完成 P0/P1/P2 缺陷修复，注册接口 IP 限流、Cookie 安全属性等防护到位，数据库查询全部参数化
- **轻量可靠存储**：SQLite + WAL 共 23 张表，用户数据严格隔离，本地自动备份

## 功能

- 健康数据总览：核心体征、综合评分（饮食 40% + 运动 40% + BMI 20%）、异常提醒、体检报告分析
- 饮食：四个餐次、食物库、热量与三大营养素、个性化营养目标、**AI 餐食图片多模态识别并自动估算营养**
- 运动：类型/时长/强度记录、近 7 天柱状图、点日期补记、运动计划
- 睡眠与情绪：时长记录与近 7 天趋势
- 女性健康：经期、排卵日、易孕期推算
- 家人健康：多成员档案、血压/用药/复诊、关怀提醒
- 科普资讯：RSS 聚合、站内封面、速读摘要
- AI 健康小管家（Agent）：支持对话、语音、图片输入；智能体读取用户健康档案并调用系统工具，**可直接写入饮食/运动/体重/睡眠记录，并给出个性化健康改善建议**
- 账号：注册、登录、找回密码、数据云同步、注销

## 技术架构

```text
浏览器（单页 HTML/CSS/原生 JS）
        │ HTTPS
Python 标准库 ThreadingHTTPServer
  web.py 服务入口 / 静态资源 / ETag
  backend/app.py 请求处理
  backend/routes.py 路由与业务（40+ 接口）
  backend/auth.py PBKDF2 + 会话 + Cookie
  backend/db.py SQLite（WAL，23 张表，参数化查询，用户数据隔离）
  backend/ai.py OpenAI 兼容模型客户端（服务端保管 API 密钥，前端不接触密钥）
  backend/asr.py / backend/mailer.py / backend/telemetry.py
        │
health.db（SQLite）  +  外部多模态模型
```

- **前端**：无框架、无构建，样式与脚本内联，单次请求即可交互
- **后端**：仅 Python 标准库，零第三方运行时依赖
- **数据**：SQLite + WAL，23 张表，按用户隔离，全部参数化查询；`backups/` 目录负责数据库自动本地备份
- **AI**：OpenAI 兼容协议，切换供应商只需改 `HM_AI_API_BASE` / `HM_AI_MODEL`；密钥保存在服务端环境变量、由后端中转请求；识图需选用支持多模态的模型

## 快速开始

```bash
python web.py
# 浏览器自动打开 http://127.0.0.1:8000/（端口被占用会自动顺延）
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
健康管理系统-演示视频.mp4
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

运行时不依赖任何第三方 Python 包（见 `requirements.txt`），保留该文件仅为声明与评审确认，`python web.py` 即可直接运行。开发辅助脚本仅使用标准库；文档转换使用本机 Office，均不构成运行依赖。

## 测试说明

项目完成多轮质量验证：

1. Python 源码语法静态校验、内嵌 JS 语法校验，均零报错
2. 黑盒体验走查与安全审计，完成 P0/P1/P2 缺陷的定位与闭环修复
3. 手工功能测试覆盖新用户流程、AI 识别、家人档案、账号安全、移动端适配等场景

## 团队信息

| 成员 | 分工 |
| --- | --- |
| 郜婧雯 | 产品设计、前端实现、体验走查 |
| 王永传 | 后端与数据库、AI 接入、部署运维 |
| 宋雨珊 | 测试、文档与演示 |

## 说明与边界

1. 本项目为健康管理工具，所有 AI 输出与健康建议**均不构成医疗诊断**。涉及用药与急症请及时就医。
2. AI 餐食图片识别依赖外部多模态模型，结果仅供参考，复杂餐食建议手动录入。
3. AI 功能依赖外部大模型 API，网络异常或密钥无效时相关功能不可用。
4. AI 功能需配置`HM_AI_API_KEY` 。**完整功能请直接访问在线演示 https://health.mymyhealth.xyz （已配置密钥）**，本地运行默认走规则建议降级。

