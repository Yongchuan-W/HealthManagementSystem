# 本轮迭代任务清单

> 全部改动在 `web.py`，完成后重新生成 `index.html` 并提交。

## T1 睡眠小时+分钟
- [x] 修改 `#sleepForm` HTML：`#sleepHour` + `#sleepMinute`
- [x] 新增 `.sleep-time` CSS
- [x] 改 `renderSleepToday()` 拆分钟回填与文案
- [x] 改提交逻辑：校验并保存 `h + m/60`

## T2 活动水平持久化
- [x] 新增 `applyDietActivity()`
- [x] `applyBundle()` 末尾调用
- [x] `refreshAllViews()` 调用
- [x] 修复后端 `safe_float` 精度导致 1.55 被存成 1.6
- [x] 服务端 import/export round-trip 验证

## T3 睡眠周柱形图
- [x] 新增 `#sleepWeek` HTML 与 `.sleep-bars` CSS
- [x] 实现 `renderSleepWeek()`，保存后与 `refreshAllViews()` 调用

## T4 经期预测
- [x] 女性档案新增 3 个 `.f-item` 与 `#cycleForecast`
- [x] 扩展 `renderCycle()`：下次经期、易孕期、倒计时、未来 3 次预测、周期阶段

## T5 侧边栏修改基本信息
- [x] 新增 `#editBasicBtn` 与 `.side-edit` CSS
- [x] 实现 `prefillOnboarding()`、`setChipValues()`、`setSelectValue()`
- [x] 编辑态显示 onboarding、返回逻辑
- [x] 提交保存 `preferences.age` 并在编辑后刷新视图

## T6 饮食柱形图点击 + 综合建议
- [x] `.mini-bar` 改为可点击按钮并加样式
- [x] 新增 `#dayMealMask` 弹窗与 `openDayMeals(date)`
- [x] 新增「综合饮食建议」`#recentDietAdvice` 与 `renderRecentDietAdvice()`
- [x] `refreshDietViews()` 调用新建议

## T7 补记前几日数据
- [x] 饮食 `#mealDate` + `#mealLogTitle`，`saveMealRecord`/`renderMealLog` 改为按所选日期
- [x] 心情 `#moodDate`，`renderMoodForDate`/保存改为按所选日期
- [x] 运动 `#sdDate`，`saveSportForDate` 写入所选日期
- [x] `refreshAllViews()` 重置三个日期为今天

## T8 语音/域名问题答复
- [x] 文字说明 HTTPS 限制、隧道方案与域名购买/备案建议（不改代码）

## 验证与提交
- [x] `python -m py_compile web.py`
- [x] 本地接口 round-trip 验证（dietActivity、补记数据、sleepLog、female.profile）
- [x] 浏览器实测：登录、睡眠、饮食柱形图、活动水平、基本信息回填、经期预测
- [x] 重新生成 `index.html`
- [x] 分条 `git commit`
