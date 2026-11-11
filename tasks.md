# 本轮任务清单

> 依据 `spec.md` 执行；已完成项已勾选。

## 一、数据与账号

- [x] T1 运动持久化：`sportState` 改 `let` + `SPORT_DEFAULT` + `reloadSportState()`，在 `applyBundle()` / `refreshAllViews()` 中调用
- [x] T2 后端开放注册：`auth_register` 移除白名单 403；`auth.login` / `user_from_token` 移除非白名单拒绝
- [x] T3 前端注册模式：登录卡增加「注册 / 登录」切换、昵称输入、按钮文案与提交分支
- [x] T4 注销账号：`auth.verify_password_or_raise()` + `DELETE /api/account` + 个人档案弹窗「注销账号」按钮（二次确认 + 密码）

## 二、资讯与语音

- [x] T5 后端 `GET /api/news`：中国新闻网 / 人民网健康 RSS 解析 + 5 分钟缓存 + 失败可回退
- [x] T6 前端真实资讯：`refreshLiveNews()`、已读链接去重、搜索联动、失败回退内置 12 篇
- [x] T7 语音输入：`#voiceFab` 按钮 + CSS + `initVoice()`（Web Speech API、中文数字转换、非 HTTPS/不支持提示）

## 三、AI 能力

- [x] T8 使用帮助：`ai.PAGE_GUIDE` 注入 system prompt；小管家快捷提问按钮；静态版 `getReply()` 使用说明
- [x] T9 Agent 动作：`ai.detect_action()` + `/api/ai/chat` 返回 `action`（含饮食热量估算）+ 前端 `runAiAction()` 执行

## 四、交付

- [x] T10 生成 `index.html`，本地启动 `python web.py` 冒烟检查（注册/登录/运动/资讯/语音/动作/注销）
- [ ] T11 git 提交（排除 `ai_local.env`），输出 push 与服务器 `git pull && sudo systemctl restart health` 命令
- [ ] T12 回复中解释 MCP / RAG / AI Agent 三个概念及本项目现状
