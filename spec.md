# 健康管理系统 · 本轮迭代规格说明

## 背景

单文件前端 [web.py](web.py)（`PAGE_HTML` 内嵌 CSS/JS）+ `backend/`（纯标准库 + SQLite）已部署到阿里云。数据通过 `localStorage(hm_*)` + 500ms 防抖 `POST /api/sync/import` 持久化，登录后 `GET /api/sync/export` → `applyBundle()` 回填。

本轮把用户提出的 8 项需求拆成可验证的改动，全部集中在 `web.py` 前端（后端接口已支持所需字段，仅需回归验证），改完必须重新生成 `index.html`。

## 需求与实现方案

### 1. 睡眠时长改为「小时 + 分钟」

- 位置：[web.py](web.py) 睡眠表单 `#sleepForm`（约 4844 行）。
- HTML：删除单个 `#sleepHours`，改为 `#sleepHour`（0-23）与 `#sleepMinute`（0-59，step 5），中间用「小时 / 分钟」文字分隔，外层 `.sleep-time`。
- CSS：新增 `.sleep-time { display:flex; align-items:center; gap:6px; }`，内部 input 宽度改为 80px。
- JS：
  - `renderSleepToday()` 把 `entry.hours` 拆成 `h = floor(hours)`、`m = round((hours-h)*60)` 回填；展示文案改为「X 小时 Y 分钟 · 质量」。
  - 提交时 `hours = h + m/60`；校验 0 ≤ 总时长 ≤ 24、分钟 0-59；存储结构仍为 `{date, hours, quality, note}`，后端 `sleep_records` 不变。

### 2. 日常活动水平持久化修复

- 现状：`#dietActivity` 在 change 时写入 `hm_dietActivity`，`buildSyncPayload()` 会提交，`applyBundle()` 会回填；但页面加载 / 登录回填分散在 `refreshAllViews()`，存在刷新时机与空值判断问题。
- 改法：
  - 新增 `applyDietActivity()`：读取 `loadData('dietActivity', null)`，非空时设置 `select.value`；在 `applyBundle()` 末尾、`refreshAllViews()` 内调用。
  - `change` 监听改为同时写 `parseFloat` 并立即 `refreshDietViews()`（保留现有行为）。
  - `applyBundle()` 对 `settings.dietActivity` 为 `undefined` 时不再写入（现有 `if (values[key] === undefined) return;` 已保证）。
- 验证：本地起服务，注册/登录后 `POST /api/sync/import`（dietActivity=1.55）→ `GET /api/sync/export` 应返回 1.55；前端切账号后下拉框保持所选值。

### 3. 睡眠最近一周柱形图

- HTML：`#sleepToday` 后新增 `<div class="sleep-week" id="sleepWeek"></div>`。
- CSS：新增 `.sleep-bars`、`.sleep-bar`（沿用 `.mini-bars` 视觉，浅色系以适配睡眠卡片）。
- JS：新增 `renderSleepWeek()`：取最近 7 天（含今天）`sleepLog`，按小时画柱，柱顶显示「7.5h」，柱下标日期；无记录柱高 4px 且显示「—」。在保存成功后与 `refreshAllViews()` 调用。

### 4. 女性健康：经期预测

- HTML：女性档案左侧 `.f-item` 列表新增：易孕期 `#fertileWindow`、下次预计经期 `#nextPeriodDate`、距离下次经期 `#daysToPeriod`；`.female-grid` 下新增 `<div class="cycle-forecast" id="cycleForecast"></div>` 展示未来 3 次经期与当前周期阶段。
- JS：扩展 `renderCycle()`：
  - `nextStart`：从 `lastPeriodStart` 起按 `cycleDays` 递增，直到 ≥ 今天。
  - 排卵日 = `nextStart - 14`，易孕期 = 排卵日前 5 天至后 1 天。
  - 若今天落在 `lastPeriodStart ~ +periodDays-1`，显示「经期第 N 天」，否则显示「距下次经期 N 天」。
  - 预测列表：未来 3 次经期开始日（`formatMD`），并提示「预测基于你填写的周期长度，仅作参考」。
  - 所有数值仍由 `femaleProfile`（periodDays/cycleDays/lastPeriodStart）推导，无需新增后端字段。

### 5. 侧边栏「修改基本信息」

- HTML：侧边栏 `#nav` 下方新增按钮 `#editBasicBtn`（`.side-edit`，图标 `i-user`），文案「修改基本信息」。
- JS：
  - `let editingBasic = false;`
  - `prefillOnboarding()`：从 `profile` 与 `preferences` 回填 `#obName/#obGender/#obAge/#obHeight/#obWeight/#obSleep/#obExercise/#obGoal/#obTaste/#obDietType/#obMeals`，并用 `setChipValues()` 回填 `#obConditions/#obRestrictions`（保留自定义标签）。
  - 点击后：`editingBasic = true`，隐藏 `#appShell`，显示 `#onboardingView`，滚到顶部。
  - `#skipOnboarding`（稍后完善 / 返回）在 `editingBasic` 时直接 `enterApp()` 返回，不保存。
  - 表单提交：新增保存 `preferences.age`（来自 `#obAge`），提交后 `editingBasic = false`、`enterApp()` 并调用 `loadProfileView()` / `refreshDietViews()` / `applyGenderView()`。
- 复用现有问卷表单，不复制一套 HTML。

### 6. 饮食热量柱形图可点击 + 综合饮食建议

- 柱形图：`renderWeekCompare()` 中 `.mini-bar` 改为 `<button type="button" class="mini-bar" data-date="YYYY-MM-DD">`，CSS 增加按钮重置样式（`border:0;background:none;padding:0;cursor:pointer;font:inherit;color:inherit;`）与 hover 提示。
- 新弹窗：`#dayMealMask`（复用 `.mask`/`.modal`），`#dayMealTitle`、`#dayMealBody`、关闭按钮。`openDayMeals(date)`：
  - 过滤 `mealLog` 当天记录，按餐次列出「早餐 · 食物（约 N kcal）」，并显示合计热量与目标热量对比；
  - 无记录时显示「当天没有记录」及引导（切换记录日期补记）。
- 综合建议：饮食卡片 `#weekCompare` 下新增小标题「综合饮食建议」与 `#recentDietAdvice`。`renderRecentDietAdvice()` 基于最近 7 天（不足时用全部记录）计算：记录天数、平均热量/蛋白质、蛋白质达标天数、蔬果次数、早餐记录次数，按问题优先级输出 3-5 条建议；数据越多文案随之变化。`refreshDietViews()` 调用。

### 7. 心情 / 饮食 / 运动「补充前几日数据」

- 饮食：`今日饮食记录` 标题旁新增 `#mealDate`（`type=date`，`max=今天`）+ 提示「可切换日期补记」。新增 `mealDateValue()`（默认今天）；`saveMealRecord()` 与 `renderMealLog()` 使用该日期；`#mealLogTitle` 文案随日期变化（今天/补记 M 月 D 日）。
- 心情：心情卡片新增 `#moodDate`（`type=date`，`max=今天`）+ 提示。`moodDateValue()`；`renderMoodForDate(date)` 回填该日心情/备注（替换 `renderMoodToday`，保留今天的包装函数）；保存写入所选日期；日期变更时重绘。
- 运动：运动数据弹窗 `#sportDataMask` 顶部新增 `#sdDate`（`type=date`，`max=今天`）；打开时默认今天并回填当天数据；`saveSportForDate(date, data)` 替代 `saveTodaySport` 的固定今天逻辑（计时结束仍写今天）；`renderExercise`/`renderWeekPanel`/评分刷新保持不变；提示文案区分「今天 / M 月 D 日」。
- 三个日期输入统一在 `refreshAllViews()` 时重置为今天（避免跨账号残留）。

### 8. 手机语音与域名问题（仅答复，不改代码）

- 浏览器只在「HTTPS 或 localhost」下允许麦克风（`getUserMedia`）；当前手机访问 `http://39.96.73.121:8000` 属于非安全源，必然无法录音。
- 不买域名也可用：现有 cloudflared `trycloudflare` 隧道（每次重启地址会变）；或 Cloudflare 免费账号 + 免费 `*.workers.dev`/自有域名隧道。
- 买域名：阿里云 / 腾讯云注册（`.top/.xyz` 首年约 30 元，`.com` 约 60-80 元）；大陆服务器绑定域名需 ICP 备案；香港/海外服务器无需备案。买后可用云厂商免费 DV 证书或 Caddy/Nginx 自动 HTTPS。
- 建议：短期继续用隧道验证语音；长期稳定使用再买域名 + 备案 + HTTPS 反代。

## 涉及文件

- `web.py`：HTML、CSS、JS（全部改动）。
- `index.html`：改完后由 `PAGE_HTML` 重新生成（必须）。
- `backend/`：不改业务代码，仅接口回归验证。

## 验证步骤

1. `python -m py_compile web.py`。
2. 本地 `python web.py`，`curl` 完成注册 → `POST /api/sync/import`（含 dietActivity、前几日 mealLog/moodLog/sport、sleepLog）→ `GET /api/sync/export` 字段回读一致。
3. 浏览器验证：睡眠小时+分钟保存、周柱图；活动水平切换后重新登录仍保留；经期预测数值随周期设置变化；侧边栏修改基本信息回填与保存；饮食柱形图点击弹出当天记录/空态；综合建议随补记数据变化；心情/饮食/运动补记日期生效。
4. 重新生成 `index.html`，确认长度正常且包含新增 id。
5. 清理测试数据，`git commit`（分条、不含密钥）。

## 决策待确认

- 睡眠时长仍以「小时（浮点）」入库，只改录入与展示方式（不改后端表结构）。
- 「修改基本信息」复用现有 onboarding 表单，而非新建弹窗。
- 经期预测只做基于周期长度的估算，不引入医学判断。
