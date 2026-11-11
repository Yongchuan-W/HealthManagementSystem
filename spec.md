# 健康管理系统 · 本轮迭代 Spec

## 0. 背景与目标

用户在阿里云服务器（39.96.73.121:8000，systemd `health`）上运行 `web.py` + `backend/`（纯标准库 + SQLite）。
本轮要解决 7 件事：

1. 退出重进后「运动打卡」数据丢失。
2. 科普资讯「刷新」只是重排旧内容，需要拉取真正的新资讯。
3. 每个功能模块支持语音输入（面向老人 / 低文化水平用户）。
4. 用户可询问智能体「这个网页怎么使用」。
5. 回答概念问题：MCP 是什么、是否用了 RAG、是否用了 AI Agent。
6. AI Agent 能真正执行动作：说「开始跑步，帮我记录」→ 开始计时；说「吃了螺蛳粉…帮我填入晚餐」→ 写入晚餐记录。
7. 开放注册账号 + 注销账号。

并同步：`index.html` 重新生成、git 提交、给出服务器部署命令。

## 1. 已核实的现状（不再重复排查）

- 运动数据链路：`saveTodaySport()` → `saveData('sport', sportState)` → 500ms 防抖 `flushSync()` → `POST /api/sync/import`；后端 `sport` 分支（routes.py:2157-2189）正确写 `sport_goals` / `sport_records`；`GET /api/sync/export`（routes.py:2480-2484）正确返回。
- 前端 `sportState` 是模块级 `const`（web.py:7302），`applyBundle()` 只更新 `dataCache['sport']`；虽有 `refreshAllViews()`（web.py:10887）会回填，但它依赖调用时机，且 `refreshAllViews` 中 `sport` 为 null 时静默跳过 → 存在旧对象覆盖服务器数据的窗口。**修复：改为 `let` + `reloadSportState()`，在 `applyBundle()` 末尾同步刷新。**
- 注册：`POST /api/auth/register` 在 `allowed_accounts()` 非空时直接 403（routes.py:200-202）；同时 `auth.login()`（auth.py:239-241）也拒绝非白名单账号。**两处都要放开，否则注册后无法登录。**
- 注销：所有业务表 `user_id` 均为 `ON DELETE CASCADE`，且连接已 `PRAGMA foreign_keys = ON`（db.py:368）→ 删除 `users` 行即可级联清理。
- 资讯：`newsRefresh` 仅打乱 `newsOrder`（web.py:10858-10863），没有网络请求。
- AI：`POST /api/ai/chat`（routes.py:1462-1519）只返回文本；`ai.estimate_food()` 已可用；`sportTypes`（web.py:7603）包含「跑步」等名称。
- HTTPS：`build_ssl_context()`（web.py:11524）已支持 `HM_TLS_CERT` / `HM_TLS_KEY`，但没有证书。
- 退出登录按钮在个人信息弹窗底部（web.py:5295）。

## 2. 改动清单（文件 / 函数 / 行为）

### 2.1 运动数据持久化（web.py）

- `const sportState` → `let sportState`，抽出 `SPORT_DEFAULT` 常量。
- 新增 `function reloadSportState()`：重新 `loadData('sport', null)`，有 `goal` 则整体替换，否则用默认值，再 `pruneSportHistory()`。
- `applyBundle()` 末尾调用 `reloadSportState()`。
- `refreshAllViews()` 中运动分支改为调用 `reloadSportState()`，避免两套逻辑。
- 保存路径不变（`saveData('sport', sportState)` + 防抖同步）。

验收：记录今日运动 → 退出 → 重新登录 → 今日/本周数据仍在；服务器 `sport_records` 有当天行。

### 2.2 开放注册（backend/routes.py、backend/auth.py、web.py）

- `auth_register`：删除 `allowed_accounts()` 的 403 拦截。
- `auth.login`：删除 `allowed` 白名单限制（白名单只负责「创建/同步这些账号」，不再限制登录）。
- 前端登录卡：
  - 标题下方增加切换链接：`还没有账号？立即注册` / `已有账号？去登录`（`#authModeSwitch`）。
  - 注册模式显示新增字段：昵称（`#regNickname`，可选，默认=账号）。
  - 提交时按模式调用 `/api/auth/register` 或 `/api/auth/login`；注册成功后走 `afterAuthenticated()` → 进入 onboarding。
  - 按钮文案切换：`登录` / `注册并登录`。
- 错误提示复用 `showAuthError('loginError', ...)`。

### 2.3 注销账号（backend/routes.py、backend/auth.py、web.py）

- `auth.py` 新增 `verify_password_or_raise(conn, user, password)`（复用 `verify_password`）。
- 新路由 `DELETE /api/account`（需登录，body `{password}`）：
  1. 校验密码，错误 → 400「密码不正确」。
  2. `DELETE FROM users WHERE id = ?`（级联删除全部数据与会话）。
  3. 返回 `{ok: true, cookie: auth.clear_cookie_header()}`。
- 前端个人信息弹窗底部增加 `注销账号` 按钮（`#deleteAccountBtn`，危险样式）：
  - 两次确认：`confirm` 文案明确「永久删除，无法恢复」→ `prompt` 输入密码。
  - 成功后 `clearLocalData()` + `location.reload()`；失败 toast 提示。

### 2.4 真实科普资讯（backend/routes.py、backend/ai.py 不涉及、web.py）

- 新增 `GET /api/news`（`auth_required=False`，只读）：
  - 查询 `q`（默认「健康」）、`limit`（默认 12，上限 24）。
  - 拉取 Bing 新闻 RSS：`https://cn.bing.com/news/search?q=<q>&format=RSS`，失败回退 `https://www.bing.com/news/search?...`；`urllib` + `User-Agent`，超时 8s。
  - 用 `xml.etree.ElementTree` 解析 `item` 的 `title / link / description / pubDate`，`description` 去掉 HTML 标签并截断 160 字。
  - 模块级 10 分钟内存缓存（key = q+limit）。
  - 返回 `{items: [...], source: "bing", fetchedAt}`；失败返回 `{items: [], error: "..."}`（HTTP 200，前端可回退）。
- 前端：
  - 新增 `liveNews` 状态与 `seenNews`（localStorage `hm_newsSeen`，只存 link，最多 200 条）。
  - `newsRefresh` 改为 `async refreshLiveNews(isManual)`：请求 `/api/news?limit=24`，过滤已读链接，取前 12 条渲染为 `.news-card.live`（标题 / 摘要 / 来源 / 时间），点击 `window.open(link)`；同时把 link 记入 `seenNews`。
  - 搜索框有内容时用关键词作为 `q` 再请求一次；无网络或失败时回退内置 12 篇并 toast「网络资讯不可用，已显示内置科普」。
  - 保持原有内置文章、热门标签、速读摘要逻辑不变（`filterNews()` 只负责内置数据）。

### 2.5 语音输入（web.py）

- 新增固定按钮 `#voiceFab`（左下角，「语音输入」文字 + 麦克风图标），与右下角 AI 悬浮球对称，不遮挡内容；`≤560px` 缩小为圆形图标。
- `initVoice()`：
  - `const SR = window.SpeechRecognition || window.webkitSpeechRecognition`。
  - 不支持 → toast「当前浏览器不支持语音输入，请用 Edge/Chrome，或直接打字」。
  - `!window.isSecureContext` → toast「语音输入需要 HTTPS 访问，请让管理员开启 HTTPS」。
  - 点击开始监听：`lang='zh-CN'`、`interimResults=true`、`continuous=false`；按钮进入 `.listening` 状态并显示「正在听…」。
  - 记录 `lastEditable`：全局 `focusin` 时若为 `input/textarea`（非 password / file）则记录。
  - `onresult`：拼接最终文本；若目标 `type=number`，用 `spokenToNumber()`（阿拉伯数字优先，其次中文数字 零/一/二/…/十/百/千）转换；写入 `target.value` 并 `dispatchEvent(new Event('input', {bubbles:true}))` + `change`。
  - `onerror` / `onend`：复位按钮，失败时 toast 原因。
- 覆盖模块：健康数据输入、饮食输入、运动目标/数据、睡眠、心情、家人、提醒、个人信息、科普搜索、AI 对话（先点输入框再点语音按钮即可）。

### 2.6 AI 使用帮助（backend/ai.py、web.py）

- `ai.py` 增加 `PAGE_GUIDE` 常量（各模块入口 + 语音/小管家/资讯/注销等说明，约 350 字），在 `_build_messages()` 的 system 末尾拼接。
- 前端「健康小管家」页增加快捷提问按钮行（`#assistantQuick`）：`这个网页怎么用`、`怎么用语音输入`、`怎么记录跑步`、`怎么记录饮食`；点击调用 `sendChat(文本)`。
- 静态演示版 `getReply()` 增加「怎么用 / 使用 / 教程」规则，返回内置使用说明。

### 2.7 AI Agent 动作（backend/ai.py、backend/routes.py、web.py）

- `ai.py` 新增 `detect_action(message)`（纯规则，零额外模型调用、零延迟）：
  - 运动：命中运动词（跑步/慢跑/健走/快走/骑行/游泳/瑜伽/跳绳/力量训练/健身操/篮球/羽毛球/足球/乒乓球/太极/八段锦/拉伸/登山/爬楼梯/舞蹈）+ 意图词（开始/记录/打卡/帮我记）→
    `{"type":"sport_start","sport":"跑步"}`。
  - 饮食：命中吃/喝/早餐/午餐/晚餐/加餐 + 记录类意图 → `{"type":"meal_add","meal":"晚餐|午餐|早餐|加餐","text":"原始描述"}`。
- `/api/ai/chat` 在生成回复后调用 `detect_action(message)`：
  - `meal_add` 时尝试 `ai.estimate_food(text)`，成功则附 `action.foods`（name/kcal/protein/carb/fat/fiber/portion）与 `action.total`；失败只返回 `action` 不含 `foods`。
  - 响应新增 `action` 字段（无动作时为 `null`）。
- 前端 `runAiAction(action)`（`sendChat` 成功回调中调用）：
  - `sport_start`：调用已有 `startSportSession(name)`，`switchPage('sport')`，toast「已开始记录跑步，结束后自动统计」。
  - `meal_add` 且带 `foods`：合并营养素 → `saveMealRecord(meal, text, totals)` → `renderMealLog()`，toast「已把 … 记入晚餐」；无 `foods` 时提示「已识别到饮食描述，请到饮食页确认」。
- 系统提示补充：执行动作后用一句话确认已记录，不要重复询问。

### 2.8 HTTPS（部署说明，不改代码）

- 服务器用 openssl 生成带 IP SAN 的自签证书（`/opt/health/certs/`），在 `ai_local.env` 配置 `HM_TLS_CERT` / `HM_TLS_KEY`，`HM_PORT=443` 重启。
- 说明：自签证书浏览器会提示「不安全」，需手动继续；国内 Chrome 的语音识别依赖 Google 服务，可能仍不可用，建议用 Edge 或手动输入；彻底解决需域名 + Let's Encrypt 或 Cloudflare Tunnel。

### 2.9 生成与提交

- 用 importlib 重新生成 `index.html`。
- `git add` 相关文件并 commit（不提交 `ai_local.env`）。
- 给出服务器命令：`cd /opt/health && git pull && sudo systemctl restart health`。

## 3. 接口汇总

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/auth/register` | 开放注册（移除白名单 403） |
| DELETE | `/api/account` | 注销账号（body: password，级联删除） |
| GET | `/api/news?q=&limit=` | 必应新闻 RSS 代理，10 分钟缓存 |
| POST | `/api/ai/chat` | 响应新增 `action` 字段 |

## 4. 验收标准

1. 记录运动 → 退出 → 重新登录：今日运动卡片、本周统计、`sport_records` 均保留。
2. 新账号可自行注册并登录；旧白名单账号仍可登录。
3. 个人信息弹窗可注销账号；注销后该账号无法登录、数据被清除。
4. 点「刷新」能出现与上次不同的真实新闻标题，点击跳转原文；断网时回退内置 12 篇并有提示。
5. 点左下角语音按钮，说出「失眠」能填入科普搜索框并触发搜索；不支持的浏览器/非 HTTPS 有明确提示。
6. 对小管家说「我现在要开始跑步，帮我记录一下」→ 自动进入运动页并开始计时。
7. 说「我今天吃了一份螺蛳粉，里面有酸笋、花生、粉、青菜、炸蛋，帮我填入今日饮食的晚餐部分」→ 晚餐记录出现该条目及热量。
8. 问「这个网页怎么用」→ 返回分模块使用说明。
9. 页面无 JS 报错；`python web.py` 可正常启动。

## 5. 非目标

- 不做真正的语音转写后端（不接入讯飞/阿里云 ASR）。
- 不做新闻全文抓取与站内渲染（只跳转原文）。
- 不改动现有数据表结构与同步协议。

## 6. 风险与回退

- 必应 RSS 在境内可能被限流/改版 → 已设计回退内置内容，不影响主流程。
- 自签 HTTPS 有浏览器警告且语音能力依赖浏览器 → 保留手动输入路径。
- 开放注册后服务器可能被恶意注册 → 密码长度校验、账号唯一、每用户独立数据；如需要可在后续加频率限制（本轮不做）。
