# -*- coding: utf-8 -*-
"""
健康管理系统 · 单文件 Web 演示
================================================
将小组设计的功能界面草稿提供给AI，得到「健康管理系统」基础网页，包含：
  1. 健康数据（女性用户含女性健康档案）  2. 饮食  3. 运动  4. 家人健康  5. 睡眠  6. 科普资讯
  7. 个人信息档案弹窗  8. AI 健康小管家（悬浮聊天窗）
  9. 餐食图片识别  10. 体检报告图片识别  11. 侧边导航与运动类型选择

运行方式（无需安装任何第三方库，仅使用 Python 标准库）：
  - VS Code 打开本文件，点击右上角 ▶ 运行；
  - 或在终端执行：python web.py
  - 启动后浏览器会自动打开 http://127.0.0.1:8000/
  - 手机与电脑连接同一 Wi-Fi 后，可通过终端显示的局域网地址登录

停止服务：在终端按 Ctrl + C。
"""

import socket
import threading
import webbrowser
from http.server import ThreadingHTTPServer

from backend.app import HealthAppHandler, prepare

# ============================================================
# 页面 HTML：样式（CSS）与交互（JavaScript）全部内嵌，便于单文件运行
# ============================================================
PAGE_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>健康管理系统</title>
<style>
/* ==========================================================
   1. 全局基础样式
   ========================================================== */
* { margin: 0; padding: 0; box-sizing: border-box; }

[hidden] { display: none !important; }

:root {
  --teal: #8b4a22;
  --teal-dark: #6e3a18;
  --text: #433326;
  --muted: #8b7d70;
  --line: #e4ece4;
  --bg: #edf5ee;
  --shadow: 0 2px 14px rgba(74, 53, 37, 0.06);
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
               "Microsoft YaHei", "Helvetica Neue", Arial, sans-serif;
  background: var(--bg);
  color: var(--text);
  -webkit-font-smoothing: antialiased;
}

button, input, textarea, select { font-family: inherit; }
button { cursor: pointer; }
a { text-decoration: none; }

/* 通用线性图标（配合页面顶部的 SVG symbol 雪碧图使用） */
.icon {
  width: 18px;
  height: 18px;
  display: inline-block;
  vertical-align: middle;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
  flex: none;
}

.container {
  max-width: 1180px;
  margin: 0 auto;
  padding: 0 24px;
}

/* ==========================================================
   2. 侧边导航
   ========================================================== */
.sidebar {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  z-index: 50;
  width: 220px;
  padding: 22px 16px 18px;
  background: #fff;
  border-right: 1px solid var(--line);
  display: flex;
  flex-direction: column;
  gap: 26px;
}

.side-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 8px;
  font-size: 17px;
  font-weight: 700;
  white-space: nowrap;
}

.logo {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: linear-gradient(135deg, #4ed3b0, #35b9a1);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}

.logo .icon { width: 19px; height: 19px; stroke-width: 2.2; }

.side-nav {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}

.side-nav button {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 11px 12px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: #6b7688;
  font-size: 14px;
  text-align: left;
  transition: background 0.2s, color 0.2s;
}

.side-nav button .icon { opacity: 0.8; }

.side-nav button:hover { background: #f5f8f7; color: var(--text); }

.side-nav button.active {
  background: #eefaf6;
  color: #1f2d3d;
  font-weight: 600;
}

.side-nav button.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 9px;
  bottom: 9px;
  width: 3px;
  border-radius: 3px;
  background: var(--teal);
}

.side-user {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border-radius: 12px;
  cursor: pointer;
  transition: background 0.2s;
}

.side-user:hover { background: #f5f7fa; }

.avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: #e3e8ef;
  color: #7b8798;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}

.avatar .icon { width: 16px; height: 16px; }

.side-user-info {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.side-user-name {
  font-size: 13px;
  font-weight: 600;
  color: #39404f;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.side-user-sub {
  font-size: 11px;
  color: #8a94a6;
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.caret { width: 14px; height: 14px; color: #8a94a6; }

.main-area { margin-left: 220px; min-height: 100vh; }

/* ==========================================================
   3. 顶部横幅（浅绿卡片式，含插画与三条评分）
   ========================================================== */
.hero {
  margin-top: 20px;
  border-radius: 14px;
  padding: 16px 24px;
  position: relative;
  overflow: hidden;
  color: #24512f;
  display: flex;
  align-items: center;
  gap: 26px;
  background:
    radial-gradient(90% 130% at 94% 4%, #ffffff 0%, rgba(255, 255, 255, 0) 58%),
    linear-gradient(112deg, #f0f8e7 0%, #f7fbf2 38%, #eef7f1 68%, #e6f2f5 100%);
  border: 1px solid #e3eedd;
  box-shadow: 0 8px 22px rgba(84, 112, 74, 0.07);
}

/* 底部柔和的草地与水色弧线 */
.hero::before {
  content: '';
  position: absolute;
  left: -12%;
  right: -12%;
  bottom: -104px;
  height: 130px;
  background:
    radial-gradient(58% 100% at 28% 100%, #dfefd3, rgba(223, 239, 211, 0) 72%),
    radial-gradient(52% 100% at 84% 100%, #d4e9f3, rgba(212, 233, 243, 0) 72%);
  pointer-events: none;
}

.hero-head {
  position: relative;
  z-index: 2;
  flex: none;
}

.hero-title h1 {
  font-size: 22px;
  font-weight: 800;
  letter-spacing: 2px;
  color: #1c5a30;
  line-height: 1.25;
  white-space: nowrap;
}

.hero-title p {
  font-size: 12.5px;
  font-weight: 500;
  letter-spacing: 1px;
  color: #47704f;
  margin-top: 4px;
}

.hero-underline {
  width: 42px;
  height: 3px;
  border-radius: 3px;
  background: #6ea75b;
  margin-top: 7px;
}

/* 顶部插画与角落装饰在紧凑版中不再展示 */
.hero-illus, .hero-leaf, .hero-leaf-sm, .hero-bowl, .hero-glass { display: none; }
.hero-illus {
  position: relative;
  flex: none;
  width: 336px;
  height: 110px;
}

.hi-heart {
  position: absolute;
  left: 6px;
  top: 2px;
  width: 64px;
  height: 60px;
}

.hi-heart svg { width: 100%; height: 100%; }

.hi-slogan {
  position: absolute;
  left: 76px;
  top: 8px;
  font-size: 15px;
  line-height: 1.55;
  letter-spacing: 1px;
  color: #2f6b45;
  font-style: italic;
  transform: rotate(-7deg);
  white-space: nowrap;
}

.hi-runner {
  position: absolute;
  right: 4px;
  top: -4px;
  width: 100px;
  height: 100px;
  border-radius: 50%;
  background: radial-gradient(circle at 42% 40%, rgba(180, 214, 239, 0.6), rgba(180, 214, 239, 0.04) 72%);
  color: #5b9ec9;
  display: flex;
  align-items: center;
  justify-content: center;
}

.hi-runner svg {
  width: 60px;
  height: 60px;
  stroke-width: 1.6;
}

.hi-runner::before,
.hi-runner::after {
  content: '';
  position: absolute;
  left: 0;
  height: 4px;
  border-radius: 4px;
  background: #c7e0f0;
  transform: rotate(-18deg);
}

.hi-runner::before { width: 28px; top: 62px; }
.hi-runner::after { width: 17px; top: 74px; left: -4px; opacity: 0.8; }

.hero-leaf {
  position: absolute;
  left: -14px;
  top: -14px;
  width: 132px;
  color: #8cbf6a;
  opacity: 0.7;
  z-index: 1;
  pointer-events: none;
}

.hero-leaf-sm {
  position: absolute;
  left: 196px;
  top: 30px;
  width: 46px;
  color: #8cbf6a;
  opacity: 0.55;
  z-index: 1;
  pointer-events: none;
}

/* 三条评分：同一行排布，图标 + 标题 + 进度条 + 分数 */
.score-group {
  position: relative;
  z-index: 2;
  flex: 1;
  min-width: 0;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-top: 0;
}

.score {
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr);
  align-items: center;
  gap: 9px;
  padding: 8px 12px 9px 9px;
  border-radius: 10px;
  border: 1px solid transparent;
  margin-top: 0;
  max-width: none;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.score:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 14px rgba(80, 100, 70, 0.1);
}

.score .score-ico {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex: none;
}

.score .score-ico .icon { width: 17px; height: 17px; stroke-width: 2; }

.score .row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 6px;
  font-size: 12px;
  color: #5b4636;
  margin-bottom: 5px;
  opacity: 1;
  white-space: nowrap;
}

.score .score-num {
  font-size: 10.5px;
  color: #9a8a7c;
  white-space: nowrap;
}

.score .score-num b {
  font-size: 17px;
  font-weight: 800;
  margin-right: 1px;
  letter-spacing: 0.3px;
}

.bar {
  height: 6px;
  border-radius: 99px;
  background: rgba(74, 53, 37, 0.08);
  overflow: hidden;
}

.bar i {
  display: block;
  height: 100%;
  width: 0;
  border-radius: 99px;
  transition: width 0.8s ease;
}

.score-total { background: #fdf2f3; border-color: #f8e2e6; }
.score-total .score-ico { background: linear-gradient(135deg, #f9808f, #ec4f6b); }
.score-total .score-num b { color: #e8465f; }
.score-total .bar i { background: linear-gradient(90deg, #f79aa9, #ec4f6b); }

.score-diet { background: #f2f8ec; border-color: #e1edd6; }
.score-diet .score-ico { background: linear-gradient(135deg, #93c96f, #5d9c43); }
.score-diet .score-num b { color: #4f8a37; }
.score-diet .bar i { background: linear-gradient(90deg, #a9d886, #5d9c43); }

.score-sport { background: #fdf7e9; border-color: #f6ebc9; }
.score-sport .score-ico { background: linear-gradient(135deg, #f4cf62, #dea31f); }
.score-sport .score-num b { color: #c58f13; }
.score-sport .bar i { background: linear-gradient(90deg, #f8d97e, #dea31f); }

/* 角落的蔬果碗与一杯水 */
.hero-bowl {
  position: absolute;
  left: -10px;
  bottom: -16px;
  width: 96px;
  z-index: 1;
  pointer-events: none;
}

.hero-glass {
  position: absolute;
  right: 16px;
  bottom: -6px;
  width: 40px;
  z-index: 1;
  pointer-events: none;
}

/* ==========================================================
   4. 页面切换与通用卡片
   ========================================================== */
.content { margin: 24px 0 48px; }

.page { display: none; }
.page.active { display: block; animation: fadeUp 0.35s ease both; }

@keyframes fadeUp {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

.card {
  background: #fff;
  border-radius: 16px;
  box-shadow: var(--shadow);
  padding: 24px;
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 700;
}

.card-title .icon { width: 20px; height: 20px; }

.sub-title {
  font-size: 14px;
  font-weight: 500;
  color: #4a5568;
  margin: 24px 0 10px;
}

/* ==========================================================
   5. 健康数据页
   ========================================================== */
.health-card {
  display: flex;
  gap: 28px;
  align-items: flex-start;
  padding: 24px 28px;
}

.health-main { flex: 1; min-width: 0; }

.health-main .card-head { margin-bottom: 20px; }
.heart { color: #ef5b5b; }

.vitals {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}

.vital {
  background: #f8f9fc;
  border-radius: 12px;
  padding: 16px 18px;
  transition: background 0.2s;
}

.vital:hover { background: #f4f6fa; }

.vital .label {
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 10px;
}

.vital .value {
  font-size: 22px;
  font-weight: 700;
  color: #222f3e;
  display: flex;
  align-items: center;
}

.vital .unit {
  font-size: 12px;
  color: var(--muted);
  font-weight: 400;
  margin-left: 4px;
}

.badge {
  font-size: 12px;
  color: #27b389;
  background: #e8f8f2;
  border-radius: 6px;
  padding: 2px 8px;
  margin-left: 8px;
  font-weight: 500;
}

.badge.warn { color: #d99a3f; background: #fdf3e0; }

/* 右侧健康参考面板：正常值范围 + 异常提醒 + BMI 公式 */
.vital-side {
  width: 330px;
  flex: 0 0 330px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-top: 2px;
}

.range-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  font-size: 13px;
  font-weight: 700;
  color: #4a3525;
}

.range-head .report-link { margin: 0; align-self: auto; }

.report-link {
  align-self: flex-end;
  background: none;
  border: 0;
  font-size: 12px;
  color: #2fbf9b;
  padding: 0;
  margin-bottom: 6px;
}

.report-link:hover { text-decoration: underline; }

.range-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.range-row {
  display: grid;
  grid-template-columns: 58px 1fr auto;
  gap: 8px;
  align-items: center;
  padding: 7px 10px;
  border-radius: 8px;
  background: #faf8f3;
  font-size: 12px;
}

.rr-name { color: #6f6154; white-space: nowrap; }
.rr-ref { color: #8b7d70; font-size: 11.5px; }

.rr-state {
  font-size: 11px;
  padding: 1px 7px;
  border-radius: 99px;
  background: #e8f8f2;
  color: #278f70;
  white-space: nowrap;
}

.rr-state.warn { background: #fdf3e0; color: #c07d20; }
.rr-state.muted { background: #f0efec; color: #8b7d70; }

.abnormal-box {
  background: #fff8f2;
  border: 1px solid #f4e2d3;
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 12px;
  color: #866a58;
}

.abnormal-box b { display: block; font-size: 12px; color: #b4614a; margin-bottom: 6px; }
.abnormal-box ul { margin: 0; padding-left: 16px; line-height: 1.7; }

.abnormal-box.ok { background: #f2fbf7; border-color: #d8f3e7; color: #2b9a7d; }
.abnormal-box.ok b { color: #278f70; }

.bmi-formula {
  background: #f4f8f0;
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 11.5px;
  line-height: 1.7;
  color: #7c7367;
}

.bmi-formula b { color: #6e3a18; font-size: 12px; }
.bmi-formula .formula-line { color: #6e3a18; font-weight: 600; }

/* 头像上传 + 裁剪 */
.avatar-option.avatar-upload {
  background: #f4f1ec;
  border: 1px dashed #d5c9bb;
  color: #9c8b7b;
  font-size: 17px;
}

.avatar-option img,
.side-user .avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: inherit;
  display: block;
}

.side-user .avatar { overflow: hidden; }

.crop-modal { width: 348px; }

.crop-stage {
  position: relative;
  width: 240px;
  height: 240px;
  margin: 0 auto 14px;
  border-radius: 12px;
  overflow: hidden;
  background: #f1eee9;
  cursor: grab;
  touch-action: none;
  user-select: none;
}

.crop-stage.dragging { cursor: grabbing; }

.crop-stage img {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  pointer-events: none;
  user-select: none;
}

.crop-overlay {
  position: absolute;
  inset: 12px;
  pointer-events: none;
  border-radius: 50%;
  box-shadow: 0 0 0 2000px rgba(30, 22, 16, 0.38);
}

.crop-overlay::after {
  content: '';
  position: absolute;
  inset: 0;
  border: 2px dashed rgba(255, 255, 255, 0.9);
  border-radius: 50%;
}

.crop-zoom {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: #6b7688;
}

.crop-zoom input[type="range"] {
  flex: 1;
  accent-color: #8b4a22;
}

.crop-hint {
  font-size: 11.5px;
  color: #9c8b7b;
  text-align: center;
  margin-bottom: 4px;
}

/* AI 智能体标志：跑步插画 + 轻微律动，表现「正在跑」的智能体 */
.fab .ai-run {
  position: relative;
  display: block;
  width: 100%;
  height: 100%;
  animation: aiRun 0.95s ease-in-out infinite;
  transform-origin: 50% 80%;
}

.fab .ai-run img {
  display: block;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
  box-shadow: 0 0 0 2px #fff, 0 10px 22px rgba(76, 122, 82, 0.32);
}

@keyframes aiRun {
  0%, 100% { transform: translateY(0) rotate(-1.4deg); }
  50%      { transform: translateY(-3px) rotate(1.4deg); }
}

.fab .ai-tag {
  position: absolute;
  right: -7px;
  bottom: -6px;
  padding: 1px 4px;
  border-radius: 5px;
  background: #3f9c72;
  color: #fff;
  font-size: 9px;
  font-weight: 800;
  line-height: 1.25;
  letter-spacing: 0.2px;
  box-shadow: 0 2px 6px rgba(63, 156, 114, 0.4);
}

.chat-head .ico { background: #fff; }
.chat-head .ico img {
  display: block;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
}


/* ==========================================================
   6. 饮食页
   ========================================================== */
.diet-wrap { max-width: none; margin: 0; }

.fork { color: #d98b5f; }

.macros {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}

.macro {
  background: #fdf7f1;
  border-radius: 10px;
  padding: 14px 6px;
  text-align: center;
}

.macro .label { font-size: 12px; color: #a58e7e; }

.macro .value {
  font-size: 17px;
  font-weight: 700;
  color: #c8834f;
  margin-top: 9px;
}

.meal {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 12px;
}

.meal-tag {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  flex: none;
}

.meal-tag.morning { background: #eaf2ff; color: #5b8def; }
.meal-tag.noon    { background: #fdf4dd; color: #d9a340; }
.meal-tag.night   { background: #efeaff; color: #8a6cf0; }

.meal input {
  flex: 1;
  height: 42px;
  border: 0;
  border-radius: 10px;
  background: #f8f9fc;
  padding: 0 16px;
  font-size: 13px;
  color: #475467;
  outline: none;
  transition: box-shadow 0.2s, background 0.2s;
}

.meal input::placeholder { color: #aab2c0; }

.meal-btn {
  flex: none;
  height: 34px;
  padding: 0 14px;
  border: 1px solid #d9c3ae;
  border-radius: 9px;
  background: #fdf7f0;
  color: #8b4a22;
  font-size: 12.5px;
  font-weight: 600;
  transition: background 0.2s, border-color 0.2s;
}

.meal-btn:hover { background: #f7eee4; border-color: #c9a98d; }

.meal input:focus {
  background: #fff;
  box-shadow: 0 0 0 2px #d9f3ec;
}

.tip-card {
  margin-top: 20px;
  background: #f0fbf6;
  border: 1px solid #d8f3e7;
  border-radius: 12px;
  padding: 16px 18px;
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.tip-card .icon { color: #2fbf9b; margin-top: 2px; }

.tip-card b { font-size: 14px; color: #2b9a7d; }

.tip-card p {
  font-size: 12px;
  color: #7b8a86;
  line-height: 1.8;
  margin-top: 6px;
}

/* ==========================================================
   7. 运动页
   ========================================================== */
.exercise-wrap { max-width: none; margin: 0; }

.activity-icon { color: #6b7cf0; }

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: linear-gradient(135deg, #6b8cff, #5b6cf6);
  color: #fff;
  border: 0;
  border-radius: 10px;
  padding: 10px 18px;
  font-size: 13px;
  box-shadow: 0 6px 14px rgba(91, 108, 246, 0.25);
  transition: transform 0.15s, box-shadow 0.2s;
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 9px 18px rgba(91, 108, 246, 0.32);
}

.btn-primary .icon { width: 14px; height: 14px; }

.tabs {
  display: flex;
  gap: 28px;
  border-bottom: 1px solid var(--line);
  margin-bottom: 20px;
}

.tabs button {
  position: relative;
  background: none;
  border: 0;
  padding: 0 0 12px;
  font-size: 14px;
  color: #7c8698;
}

.tabs button.active { color: var(--text); font-weight: 600; }

.tabs button.active::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: -1px;
  height: 2px;
  background: var(--teal);
}

.ex-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}

.ex-stat {
  background: #f8f9fc;
  border-radius: 12px;
  padding: 20px 8px 18px;
  text-align: center;
}

.ex-stat .ico {
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 8px;
}

.ex-stat .ico .icon { width: 26px; height: 26px; }
.ico-flame { color: #f08a4b; }
.ico-step  { color: #3fc7a4; }
.ico-clock { color: #5b8def; }

.ex-stat .value { font-size: 18px; font-weight: 700; color: #222f3e; }

.ex-stat .label {
  font-size: 12px;
  color: var(--muted);
  margin-top: 6px;
}

.mood {
  margin-top: 22px;
  background: #fdf9e9;
  border: 1px solid #fbf3d2;
  border-radius: 12px;
  padding: 18px;
}

.mood-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #5c5340;
}

.mood-title .icon { color: #e8a93c; }

.mood textarea {
  width: 100%;
  height: 84px;
  border: 0;
  border-radius: 10px;
  background: #fff;
  padding: 12px 14px;
  font-size: 13px;
  color: #475467;
  resize: none;
  outline: none;
  margin-top: 12px;
  line-height: 1.7;
}

.mood textarea::placeholder { color: #b3ac97; }

/* ==========================================================
   8. 女性健康与家人健康页
   ========================================================== */
.female-wrap { max-width: 720px; margin: 0 auto; }

.female-card {
  background: #fdf1f6;
  border: 1px solid #fbe3ee;
  border-radius: 16px;
  padding: 24px;
}

.female-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
  gap: 12px;
}

.female-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 700;
  color: #39404f;
}

.female-title .icon { color: #e0679a; }

.btn-soft {
  background: #fff;
  border: 1px solid #f3d6e4;
  color: #e0679a;
  border-radius: 10px;
  padding: 9px 16px;
  font-size: 13px;
  transition: background 0.2s;
}

.btn-soft:hover { background: #fff6fa; }

.female-grid {
  display: grid;
  grid-template-columns: 1fr 1.1fr;
  gap: 20px;
}

.f-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-radius: 10px;
  padding: 14px 16px;
  margin-bottom: 12px;
  font-size: 13px;
  color: #6b7688;
}

.f-item:last-child { margin-bottom: 0; }

.f-item .left { display: flex; align-items: center; gap: 8px; }
.f-item .icon { color: #e0679a; width: 16px; height: 16px; }
.f-item b { font-size: 16px; color: #39404f; }

.status-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  position: relative;
}

.status-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #39404f;
}

.status-title .icon { color: #e0679a; width: 16px; height: 16px; }

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 12px 0;
}

.tag {
  background: #fdeaf2;
  color: #dd6d9c;
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 12px;
}

.tag.add {
  background: #fff;
  border: 1px dashed #eabfd3;
  color: #c992ac;
  cursor: pointer;
}

.tag.add:hover { background: #fff7fb; }

.tip-pink {
  background: #fdeef5;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 12px;
  color: #a06c82;
  line-height: 1.8;
}

/* 可自由选择的周期字段（下拉框伪装成普通文字） */
.f-item select {
  border: 0;
  background-color: transparent;
  padding: 0 16px 0 0;
  font-size: 16px;
  font-weight: 700;
  color: #39404f;
  text-align: right;
  outline: none;
  cursor: pointer;
  appearance: none;
  -webkit-appearance: none;
  background-image: linear-gradient(45deg, transparent 50%, #b7bfcc 50%),
                    linear-gradient(135deg, #b7bfcc 50%, transparent 50%);
  background-position: calc(100% - 7px) 55%, calc(100% - 3px) 55%;
  background-size: 4px 4px, 4px 4px;
  background-repeat: no-repeat;
}

/* 标签移除小叉号（扩大点击区域） */
.tag .x {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  margin-left: 4px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: inherit;
  font-size: 12px;
  line-height: 1;
  font-style: normal;
  cursor: pointer;
  opacity: 0.6;
}

.tag .x:hover {
  opacity: 1;
  background: rgba(221, 109, 156, 0.14);
}

/* 标签多选浮层 */
.tag-menu {
  position: absolute;
  top: 46px;
  right: 12px;
  z-index: 30;
  display: none;
  width: 252px;
  padding: 14px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 12px;
  box-shadow: 0 14px 34px rgba(30, 42, 70, 0.18);
}

.tag-menu.open { display: block; animation: pop 0.18s ease both; }

.tag-menu h4 {
  font-size: 12px;
  font-weight: 600;
  color: #6b7688;
  margin-bottom: 10px;
}

.tag-options { display: flex; flex-wrap: wrap; gap: 8px; }

.tag-option {
  border: 1px solid #eef0f5;
  background: #f8f9fc;
  color: #6b7688;
  border-radius: 6px;
  padding: 5px 10px;
  font-size: 12px;
  transition: all 0.15s;
}

.tag-option:hover { border-color: #d9dee8; }

.tag-option.selected {
  background: #fdeaf2;
  border-color: #f6d3e3;
  color: #d76596;
  font-weight: 600;
}

.tag-menu-foot {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.btn-mini {
  border: 0;
  border-radius: 6px;
  background: #4ecdc4;
  color: #fff;
  padding: 6px 14px;
  font-size: 12px;
}

/* 男性模式：家人健康关怀 */
.family-card {
  background: #f2f8ff;
  border: 1px solid #dfeaf8;
  border-radius: 16px;
  padding: 24px;
}

.family-title .icon { color: #5b8def; }

.family-card .btn-soft {
  border-color: #d5e5fb;
  color: #4f86e8;
}

.family-card .btn-soft:hover { background: #f6faff; }

.family-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}

.person-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
}

.person-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.person-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #eaf2ff;
  color: #5b8def;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  flex: none;
}

.person-name { font-size: 14px; font-weight: 700; color: #39404f; }

.person-age { font-size: 11px; color: var(--muted); margin-left: 6px; }

.family-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  font-size: 12px;
  color: #6b7688;
  padding: 8px 0;
  border-top: 1px dashed #eef1f6;
}

.family-line b {
  color: #39404f;
  font-weight: 600;
  max-width: 64%;
  text-align: right;
  line-height: 1.5;
}

/* 家人卡片可点击进入完整档案 */
.person-card {
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.person-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(74, 53, 37, 0.1);
}

/* 家人健康档案弹窗 */
.member-detail-head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 14px;
  border-bottom: 1px dashed #eef1f6;
  margin-bottom: 14px;
}

.member-detail-name { display: flex; flex-direction: column; gap: 3px; }
.member-detail-name b { font-size: 15px; color: #39404f; }
.member-detail-name span { font-size: 12px; color: #8a94a6; }

.detail-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 16px;
}

.detail-item {
  padding: 10px 12px;
  border-radius: 10px;
  background: #f8faf7;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.detail-item span { font-size: 11.5px; color: #8b7d70; }
.detail-item b { font-size: 13px; color: #39404f; line-height: 1.5; word-break: break-all; }

.detail-title {
  font-size: 13px;
  color: #433326;
  margin: 14px 0 8px;
}

@media (max-width: 620px) {
  .detail-grid { grid-template-columns: 1fr; }
}

.family-card .status-title .icon { color: #5b8def; }

.family-card .tag {
  background: #eaf2ff;
  color: #4f7fd0;
}

.family-card .tag.add {
  background: #fff;
  border-color: #c5daf7;
  color: #86a6ce;
}

.family-card .tag-option.selected {
  background: #eaf2ff;
  border-color: #d5e5fb;
  color: #4f7fd0;
}

.tip-blue {
  background: #eef5ff;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 12px;
  color: #6b84a3;
  line-height: 1.8;
}

.family-records {
  margin-top: 14px;
  background: #fff;
  border-radius: 10px;
  padding: 12px 14px;
}

.family-records h4 {
  font-size: 12px;
  font-weight: 600;
  color: #6b7688;
  margin-bottom: 6px;
}

.record-empty { font-size: 12px; color: #aab2c0; }

.record-item {
  display: flex;
  gap: 10px;
  font-size: 12px;
  color: #6b7688;
  padding: 5px 0;
  border-top: 1px dashed #f1f4f8;
}

.record-item .date { color: #9aa6b6; flex: none; }

/* 弹窗中的取消按钮与说明文字 */
.btn-cancel {
  background: #f1f3f7;
  color: #6b7688;
  border: 0;
  border-radius: 8px;
  padding: 9px 14px;
  font-size: 12px;
  margin-right: 10px;
}

.btn-cancel:hover { background: #e8ebf1; }

.form-hint {
  font-size: 12px;
  color: #9aa3b2;
  line-height: 1.7;
  margin: 2px 0 8px;
}

/* 女性健康档案嵌入「健康数据」页 */
.female-health { margin-top: 20px; }
.female-health .female-card { padding: 24px 28px; }

/* 家人健康页：关怀提醒 */
.family-wrap { max-width: none; margin: 0; }

.reminder-card {
  background: #fff;
  border-radius: 16px;
  box-shadow: var(--shadow);
  padding: 24px;
  margin-bottom: 20px;
}

.reminder-count {
  font-size: 12px;
  font-weight: 500;
  color: #d98a3f;
  background: #fdf3e0;
  border-radius: 999px;
  padding: 3px 9px;
  margin-left: 6px;
}

.reminder-list { display: flex; flex-direction: column; gap: 10px; }

.reminder-item {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #f8f9fc;
  border-radius: 10px;
  padding: 12px 14px;
}

.reminder-item.done { opacity: 0.5; }

.reminder-check {
  width: 22px;
  height: 22px;
  border: 1.5px solid #cbd3df;
  border-radius: 50%;
  background: #fff;
  color: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  flex: none;
  padding: 0;
}

.reminder-item.done .reminder-check {
  background: #4ecdc4;
  border-color: #4ecdc4;
  color: #fff;
}

.reminder-main { flex: 1; min-width: 0; }

.reminder-title { font-size: 13px; font-weight: 600; color: #39404f; }
.reminder-item.done .reminder-title { text-decoration: line-through; color: #9aa3b2; }

.reminder-meta { font-size: 11px; color: #8a94a6; margin-top: 4px; }

.reminder-badge {
  flex: none;
  font-size: 11px;
  color: #e0679a;
  background: #fdeaf2;
  border-radius: 6px;
  padding: 3px 8px;
}

.reminder-badge.overdue { color: #d9534f; background: #fdeceb; }
.reminder-badge.today { color: #d98a3f; background: #fdf3e0; }
.reminder-badge.done { color: #8a94a6; background: #f1f3f7; }

.reminder-empty {
  font-size: 12px;
  color: #aab2c0;
  padding: 4px 0;
}

.head-actions { display: flex; gap: 8px; flex-wrap: wrap; }

.btn-small { padding: 8px 12px; font-size: 12px; }

.family-record-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 4px 0 10px;
}

.family-record-head h3 {
  font-size: 14px;
  font-weight: 600;
  color: #4a5568;
}

.family-card .family-records { margin-top: 0; }

/* 图片上传与识别 */
.upload-box {
  background: #f8f9fc;
  border: 1px dashed #d8dee9;
  border-radius: 12px;
  padding: 16px;
  transition: border-color 0.2s, background 0.2s;
}

.upload-box:hover {
  border-color: #9fe3d5;
  background: #f7fbfa;
}

.upload-empty { text-align: center; color: #8a94a6; font-size: 12px; }

.upload-empty .icon {
  width: 30px;
  height: 30px;
  color: #aab7c8;
  margin-bottom: 8px;
}

.upload-empty p { line-height: 1.7; margin-bottom: 10px; }

.upload-preview {
  display: flex;
  gap: 14px;
  align-items: flex-start;
}

.upload-preview img {
  width: 120px;
  height: 92px;
  object-fit: cover;
  border-radius: 10px;
  background: #e9edf3;
  flex: none;
}

.upload-info { flex: 1; min-width: 0; }

.upload-file {
  font-size: 12px;
  font-weight: 600;
  color: #4a5568;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.upload-status { font-size: 12px; color: #8a94a6; margin-top: 6px; }

.upload-status.scanning { color: #2fbf9b; }

.upload-status.scanning::before {
  content: '';
  display: inline-block;
  width: 12px;
  height: 12px;
  margin-right: 6px;
  border: 2px solid #d9f3ec;
  border-top-color: #2fbf9b;
  border-radius: 50%;
  vertical-align: -2px;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.upload-result {
  margin-top: 8px;
  font-size: 12px;
  color: #4a5568;
  line-height: 1.9;
}

.chip {
  display: inline-block;
  background: #e8f8f2;
  color: #2b9a7d;
  border-radius: 6px;
  padding: 2px 8px;
  font-size: 11px;
  margin: 0 6px 6px 0;
}

.upload-actions { margin-top: 10px; display: flex; gap: 8px; flex-wrap: wrap; }

.btn-ghost-sm {
  background: #fff;
  border: 1px solid #d8dee9;
  color: #6b7688;
  border-radius: 7px;
  padding: 6px 12px;
  font-size: 12px;
}

.btn-ghost-sm:hover { border-color: #9fe3d5; color: #2fbf9b; }

/* 体检报告分析 */
.report-card { margin-top: 20px; }

.report-sub { font-size: 12px; color: #8a94a6; }

.report-result {
  margin-top: 16px;
  border-top: 1px solid #f0f2f7;
  padding-top: 16px;
}

.report-meta {
  font-size: 12px;
  font-weight: 600;
  color: #4a5568;
  margin-bottom: 10px;
}

.report-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 10px;
}

.report-item {
  background: #f8f9fc;
  border-radius: 10px;
  padding: 12px 14px;
}

.report-item .label { font-size: 11px; color: #8a94a6; }

.report-item .value {
  font-size: 17px;
  font-weight: 700;
  color: #222f3e;
  margin-top: 6px;
}

.report-item .value .unit {
  font-size: 11px;
  color: #8a94a6;
  font-weight: 400;
  margin-left: 3px;
}

.report-summary {
  margin-top: 12px;
  background: #f0fbf6;
  border: 1px solid #d8f3e7;
  border-radius: 10px;
  padding: 12px 14px;
  font-size: 12px;
  color: #5c7a72;
  line-height: 1.8;
}

.report-actions { display: flex; justify-content: flex-end; margin-top: 12px; }

/* 运动类型选择 */
.sport-modal { width: 560px; }

.sport-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.sport-option {
  display: flex;
  align-items: center;
  gap: 10px;
  text-align: left;
  background: #f8f9fc;
  border: 1px solid #eef0f5;
  border-radius: 10px;
  padding: 10px 12px;
  transition: border-color 0.15s, background 0.15s, box-shadow 0.15s;
}

.sport-option:hover { border-color: #cfd8e5; }

.sport-option.selected {
  background: #eefaf6;
  border-color: #9fe3d5;
  box-shadow: 0 0 0 2px #e6faf5;
}

.sport-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  flex: none;
}

.sport-avatar .icon { width: 17px; height: 17px; stroke-width: 1.9; }

.sport-name { font-size: 13px; font-weight: 600; color: #39404f; }
.sport-cal { font-size: 10px; color: #8a94a6; margin-top: 2px; }

.active-sport {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 14px;
  padding: 10px 12px;
  border-radius: 10px;
  background: #eefaf6;
  border: 1px solid #d8f3e7;
  font-size: 12px;
  color: #2b9a7d;
}

.active-sport b { color: #1f8f75; }

.active-sport .end {
  margin-left: auto;
  background: none;
  border: 0;
  color: #8a94a6;
  font-size: 12px;
}

.active-sport .end:hover { color: #d9534f; }

/* ==========================================================
   登录界面
   ========================================================== */
.auth-layer {
  position: fixed;
  inset: 0;
  z-index: 100;
  overflow-y: auto;
  background:
    radial-gradient(circle at 12% 18%, rgba(78, 211, 176, 0.18), transparent 42%),
    radial-gradient(circle at 88% 24%, rgba(91, 141, 239, 0.14), transparent 40%),
    #f6f8fb;
}

.login-wrap {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 22px;
  padding: 40px 20px;
}

.login-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 700;
  color: #2c3648;
}

.login-card {
  width: 380px;
  max-width: 100%;
  background: #fff;
  border-radius: 18px;
  padding: 30px;
  box-shadow: 0 20px 50px rgba(35, 72, 110, 0.12);
}

.login-card h1 { font-size: 24px; color: #1f2d3d; }

.login-sub {
  font-size: 13px;
  color: #8a94a6;
  margin: 8px 0 22px;
}

.login-field { margin-bottom: 15px; }

.login-field label {
  display: block;
  font-size: 12px;
  color: #6b7688;
  margin-bottom: 8px;
}

.login-field input {
  width: 100%;
  height: 44px;
  border: 1px solid #e9edf2;
  border-radius: 9px;
  background: #f8f9fc;
  padding: 0 14px;
  font-size: 14px;
  color: #39404f;
  outline: none;
  transition: border-color 0.2s, background 0.2s, box-shadow 0.2s;
}

.login-field input:focus {
  background: #fff;
  border-color: #7fdccd;
  box-shadow: 0 0 0 3px #e6faf5;
}

.login-error {
  font-size: 12px;
  color: #d9534f;
  margin: 2px 0 10px;
}

.login-btn {
  width: 100%;
  justify-content: center;
  padding: 12px;
  font-size: 14px;
}

.login-hint {
  margin-top: 16px;
  padding: 9px 10px;
  border-radius: 8px;
  background: #f7f9fc;
  color: #9aa3b2;
  font-size: 12px;
  text-align: center;
}

.login-hint b { color: #4a5568; letter-spacing: 1px; }

.mobile-hint {
  margin-top: 10px;
  font-size: 12px;
  line-height: 1.7;
  color: #8b7d70;
  text-align: center;
  word-break: break-all;
}

.mobile-hint a { color: #8b4a22; text-decoration: underline; }

/* 睡眠板块并入健康数据 */
.sleep-inline { margin-top: 20px; }
.sleep-inline .sleep-card { padding: 34px 32px 32px; }

/* ==========================================================
   登录后的基本信息填写
   ========================================================== */
.onboarding-wrap {
  max-width: 1000px;
  margin: 0 auto;
  padding: 42px 24px 56px;
}

.onboarding-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 26px;
}

.onboarding-head h1 { font-size: 24px; color: #1f2d3d; }

.onboarding-head p {
  font-size: 13px;
  color: #8a94a6;
  margin-top: 6px;
}

.onboarding-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 18px;
  align-items: start;
}

.onboarding-card {
  background: #fff;
  border-radius: 16px;
  padding: 22px;
  box-shadow: var(--shadow);
}

.onboarding-card h2 {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  color: #2c3648;
  margin-bottom: 18px;
}

.onboarding-card h2 .icon { color: #4ecdc4; }

.ob-field { margin-bottom: 14px; }

.ob-field label {
  display: block;
  font-size: 12px;
  color: #6b7688;
  margin-bottom: 7px;
}

.ob-field input,
.ob-field select {
  width: 100%;
  height: 38px;
  border: 1px solid #e9edf2;
  border-radius: 8px;
  background: #f8f9fc;
  padding: 0 12px;
  font-size: 13px;
  color: #39404f;
  outline: none;
  transition: border-color 0.2s, background 0.2s;
}

.ob-field input:focus,
.ob-field select:focus {
  background: #fff;
  border-color: #7fdccd;
}

.ob-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.pref-chips { display: flex; flex-wrap: wrap; gap: 8px; }

.pref-chip {
  border: 1px solid #eef0f5;
  background: #f8f9fc;
  color: #6b7688;
  border-radius: 6px;
  padding: 5px 10px;
  font-size: 12px;
  transition: all 0.15s;
}

.pref-chip:hover { border-color: #d9dee8; }

.pref-chip.selected {
  background: #eefaf6;
  border-color: #9fe3d5;
  color: #2b9a7d;
  font-weight: 600;
}

.onboarding-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 14px;
  margin-top: 24px;
}

.link-skip {
  background: none;
  border: 0;
  color: #8a94a6;
  font-size: 13px;
}

.link-skip:hover { color: #4a5568; }

.onboarding-actions .btn-primary { padding: 12px 24px; font-size: 14px; }

/* ==========================================================
   运动计划 · 目标与计划
   ========================================================== */
.beauty-card { margin-top: 20px; }

.beauty-sub { font-size: 12px; color: #8a94a6; }

.beauty-body {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 22px;
  align-items: start;
}

.beauty-form .field { margin-bottom: 12px; }

.beauty-form .btn-primary {
  width: 100%;
  justify-content: center;
  margin-top: 4px;
}

.beauty-result {
  background: #f8f9fc;
  border-radius: 12px;
  padding: 18px;
  min-height: 210px;
}

.beauty-empty {
  height: 174px;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  font-size: 12px;
  color: #aab2c0;
  line-height: 1.8;
  padding: 0 24px;
}

.goal-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.goal-stat {
  background: #fff;
  border-radius: 10px;
  padding: 12px;
}

.goal-stat .label { font-size: 11px; color: #8a94a6; }

.goal-stat .value {
  font-size: 16px;
  font-weight: 700;
  color: #222f3e;
  margin-top: 6px;
}

.goal-stat .value .unit {
  font-size: 11px;
  color: #8a94a6;
  font-weight: 400;
  margin-left: 3px;
}

.progress-wrap { margin-top: 14px; }

.progress-label {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #6b7688;
  margin-bottom: 7px;
}

.progress-label b { color: #2fbf9b; }

.progress-bar {
  height: 9px;
  border-radius: 999px;
  background: #e8edf4;
  overflow: hidden;
}

.progress-bar i {
  display: block;
  height: 100%;
  width: 0;
  border-radius: 999px;
  background: linear-gradient(90deg, #4ed3b0, #5b8def);
  transition: width 0.4s ease;
}

.plan-summary {
  font-size: 12px;
  color: #6b7688;
  line-height: 1.8;
  margin-top: 14px;
  background: #fff;
  border-radius: 8px;
  padding: 10px 12px;
}

.plan-week {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  margin-top: 12px;
}

.plan-day {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  background: #fff;
  border-radius: 8px;
  padding: 9px 12px;
  font-size: 12px;
  color: #4a5568;
}

.plan-day span:last-child { color: #8a94a6; text-align: right; }

.weight-log {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 14px;
  font-size: 12px;
  color: #6b7688;
}

.weight-log input {
  width: 92px;
  height: 34px;
  border: 1px solid #e9edf2;
  border-radius: 8px;
  background: #fff;
  padding: 0 10px;
  font-size: 12px;
  color: #39404f;
  outline: none;
}

.weight-log input:focus { border-color: #7fdccd; }

/* ==========================================================
   9. 睡眠页
   ========================================================== */
.sleep-wrap { max-width: 620px; margin: 0 auto; }

.sleep-card {
  background: linear-gradient(135deg, #3b2b7d, #4a3797);
  border-radius: 18px;
  padding: 46px 32px 42px;
  text-align: center;
  color: #fff;
  box-shadow: 0 18px 40px rgba(59, 43, 125, 0.28);
}

.sleep-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 20px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.08);
  color: #b7a8ff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.sleep-icon .icon { width: 32px; height: 32px; }

.sleep-card h2 { font-size: 24px; letter-spacing: 1px; }

.sleep-card p {
  font-size: 13px;
  color: #cfc8f2;
  margin-top: 12px;
  line-height: 1.8;
}

.btn-sleep {
  margin-top: 26px;
  background: #7f74e8;
  color: #fff;
  border: 0;
  border-radius: 999px;
  padding: 12px 28px;
  font-size: 13px;
  transition: background 0.2s, transform 0.15s;
}

.btn-sleep:hover {
  background: #8d83ef;
  transform: translateY(-1px);
}

/* ==========================================================
   10. 科普资讯页
   ========================================================== */
.news-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.news-card {
  background: #fff;
  border-radius: 14px;
  overflow: hidden;
  box-shadow: var(--shadow);
  transition: transform 0.2s, box-shadow 0.2s;
  cursor: pointer;
}

.news-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 26px rgba(30, 42, 70, 0.12);
}

.news-img {
  height: 150px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.news-img .icon { width: 44px; height: 44px; stroke-width: 1.4; opacity: 0.55; }
.news-img.green  { background: linear-gradient(135deg, #e8f8f2, #d6f2e8); color: #3fc7a4; }
.news-img.blue   { background: linear-gradient(135deg, #eaf2ff, #dbe8ff); color: #5b8def; }
.news-img.purple { background: linear-gradient(135deg, #efebff, #e2dcff); color: #7f74e8; }

.news-body { padding: 18px; }

.news-cat { font-size: 12px; font-weight: 600; }
.news-cat.green  { color: #27b389; }
.news-cat.blue   { color: #5b8def; }
.news-cat.purple { color: #7f74e8; }

.news-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
  margin-top: 8px;
  line-height: 1.5;
}

.news-desc {
  font-size: 12px;
  color: #9099a8;
  line-height: 1.7;
  margin-top: 8px;
}

/* ==========================================================
   11. 个人信息档案弹窗
   ========================================================== */
.mask {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: none;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(20, 28, 45, 0.35);
  backdrop-filter: blur(3px);
}

.mask.open { display: flex; }

.modal {
  width: 380px;
  max-width: 100%;
  max-height: calc(100vh - 40px);
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.25);
  animation: pop 0.25s ease both;
}

@keyframes pop {
  from { opacity: 0; transform: translateY(12px) scale(0.98); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}

.modal-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
  padding: 12px 16px;
  background: linear-gradient(135deg, #4ed3b0, #3bb8a3);
  color: #fff;
  font-size: 13px;
}

.modal-head .icon { width: 16px; height: 16px; }

.modal-close {
  margin-left: auto;
  background: none;
  border: 0;
  color: #fff;
  display: flex;
  padding: 2px;
}

.modal-close .icon { width: 16px; height: 16px; }

.modal-body { padding: 20px 20px 6px; overflow-y: auto; }

.field { margin-bottom: 14px; }

.field label {
  display: block;
  font-size: 12px;
  color: #6b7688;
  margin-bottom: 8px;
}

.field input,
.field select {
  width: 100%;
  height: 38px;
  border: 1px solid #e9edf2;
  border-radius: 8px;
  background: #f8f9fc;
  padding: 0 12px;
  font-size: 13px;
  color: #39404f;
  outline: none;
  transition: border-color 0.2s, background 0.2s, box-shadow 0.2s;
}

.field input:focus,
.field select:focus {
  background: #fff;
  border-color: #7fdccd;
  box-shadow: 0 0 0 2px #e6faf5;
}

.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

/* 头像选择器：预设头像 + 当前选中态 */
.avatar-picker {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 9px;
}

.avatar-option {
  position: relative;
  height: 48px;
  border: 2px solid transparent;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  line-height: 1;
  color: #fff;
  transition: transform 0.15s, border-color 0.15s, box-shadow 0.15s;
}

.avatar-option:hover { transform: translateY(-2px); }

.avatar-option.selected {
  border-color: #8b4a22;
  box-shadow: 0 0 0 2px rgba(139, 74, 34, 0.16);
}

.avatar-option.selected::after {
  content: '✓';
  position: absolute;
  right: -5px;
  bottom: -5px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #8b4a22;
  color: #fff;
  font-size: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.side-user .avatar { font-size: 19px; line-height: 1; }

.modal-foot {
  display: flex;
  justify-content: flex-end;
  flex: 0 0 auto;
  padding: 2px 20px 18px;
}

.btn-save {
  background: #4ecdc4;
  color: #fff;
  border: 0;
  border-radius: 8px;
  padding: 9px 14px;
  font-size: 12px;
  transition: background 0.2s;
}

.btn-save:hover { background: #3fc0b6; }

/* ==========================================================
   12. 悬浮客服按钮 + AI 聊天窗口
   ========================================================== */
.fab {
  position: fixed;
  right: 26px;
  bottom: 26px;
  z-index: 60;
  width: 58px;
  height: 58px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.2s;
}

.fab:hover { transform: scale(1.06); }
.fab .icon { width: 26px; height: 26px; }

.fab .dot {
  position: absolute;
  top: 0;
  right: 0;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #ff5a5f;
  border: 2px solid #fff;
  animation: pulse 1.8s infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50%      { transform: scale(1.35); opacity: 0.7; }
}

.chat {
  position: fixed;
  right: 24px;
  bottom: 94px;
  z-index: 60;
  width: 322px;
  height: 440px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 24px 60px rgba(30, 42, 70, 0.22);
  display: none;
  flex-direction: column;
  overflow: hidden;
  animation: pop 0.25s ease both;
}

.chat.open { display: flex; }

.chat-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  background: linear-gradient(135deg, #4ed3b0, #3bb8a3);
  color: #fff;
}

.chat-head .ico {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}

.chat-head .ico .icon { width: 17px; height: 17px; }
.chat-head .t { font-size: 14px; font-weight: 700; }
.chat-head .s { font-size: 11px; opacity: 0.85; margin-top: 2px; }

.chat-close {
  margin-left: auto;
  background: none;
  border: 0;
  color: #fff;
  display: flex;
  padding: 3px;
}

.chat-close .icon { width: 16px; height: 16px; }

.chat-body {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
  background: #f7f8fb;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.msg {
  max-width: 82%;
  padding: 10px 12px;
  border-radius: 12px;
  font-size: 12px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}

.msg.bot {
  align-self: flex-start;
  background: #fff;
  color: #4a5568;
  border-top-left-radius: 4px;
  box-shadow: 0 1px 4px rgba(30, 42, 70, 0.05);
}

.msg.user {
  align-self: flex-end;
  background: #4ecdc4;
  color: #fff;
  border-top-right-radius: 4px;
}

.msg.typing { color: #a3adbd; }

.chat-input {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-top: 1px solid var(--line);
  background: #fff;
}

.chat-input input {
  flex: 1;
  height: 36px;
  border: 1px solid #e6e9f0;
  border-radius: 999px;
  padding: 0 14px;
  font-size: 12px;
  color: #39404f;
  outline: none;
}

.chat-input input::placeholder { color: #aab2c0; }
.chat-input input:focus { border-color: #9fe3d5; }

.chat-send {
  width: 34px;
  height: 34px;
  border: 0;
  border-radius: 50%;
  background: #4ecdc4;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
  transition: background 0.2s;
}

.chat-send:hover { background: #3fc0b6; }
.chat-send .icon { width: 15px; height: 15px; }

/* ==========================================================
   13. 轻提示 Toast
   ========================================================== */
.toast {
  position: fixed;
  left: 50%;
  bottom: 40px;
  z-index: 99;
  transform: translate(-50%, 20px);
  background: rgba(35, 45, 60, 0.92);
  color: #fff;
  font-size: 13px;
  padding: 10px 18px;
  border-radius: 8px;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.3s, transform 0.3s;
  max-width: 80vw;
}

.toast.show {
  opacity: 1;
  transform: translate(-50%, 0);
}

/* ==========================================================
   主题配色：棕 / 薄荷 / 浅绿 / 浅蓝
   ========================================================== */
body { color: var(--text); }

/* 侧边栏 */
.sidebar { background: #e6f1e7; border-right-color: #d6e6d9; }
.side-brand { color: #6e3a18; }
.logo { background: linear-gradient(135deg, #8b4a22, #a9653a); }
.side-nav button { color: #6f6154; }
.side-nav button:hover { background: #dcebdc; color: #4a3525; }
.side-nav button.active { background: #d7e8b9; color: #6e3a18; }
.side-nav button.active::before { background: #8b4a22; }
.avatar { background: #cfe4f2; color: #4f7898; }
.side-user-name, .onboarding-card h2, .news-title { color: #4a3525; }

/* 图标 */
.heart { color: #8b4a22; }
.fork { color: #b06a3a; }
.activity-icon { color: #5f8fae; }

/* 核心体征 */
.vital { background: #f4f8f1; }
.vital:hover { background: #eef5e9; }
.vital .value { color: #4a3525; }
.badge { color: #6b8f3f; background: #e8f2d8; }
.badge.warn { color: #a9653a; background: #f8ece3; }
.report-link { color: #8b4a22; }

/* 按钮 */
.btn-primary {
  background: linear-gradient(135deg, #8b4a22, #a9653a);
  box-shadow: 0 6px 14px rgba(139, 74, 34, 0.25);
}
.btn-primary:hover { box-shadow: 0 9px 18px rgba(139, 74, 34, 0.32); }
.btn-soft { border-color: #e3d3c4; color: #8b4a22; }
.btn-soft:hover { background: #fdf7f2; }
.btn-mini { background: #8b4a22; }
.btn-ghost-sm:hover { border-color: #c8dcae; color: #6e3a18; }
.btn-cancel { background: #f2efe9; color: #7c7065; }
.btn-cancel:hover { background: #ebe6de; }
.btn-save { background: #8b4a22; }
.btn-save:hover { background: #a9653a; }

/* 饮食 */
.macro { background: #fbf3e9; }
.macro .label { color: #a08066; }
.macro .value { color: #8b4a22; }
.meal-tag.morning { background: #e3eff8; color: #4f7898; }
.meal-tag.noon { background: #edf5df; color: #6b8f3f; }
.meal-tag.night { background: #f6ede4; color: #8b4a22; }
.meal input { background: #f5f8f1; }
.meal input:focus { box-shadow: 0 0 0 2px #d7e8b9; }
.tip-card { background: #f1f8e9; border-color: #dfeacd; }
.tip-card .icon, .tip-card b { color: #6e3a18; }
.tip-card p { color: #7a6b4c; }

/* 运动 */
.tabs { border-bottom-color: #e4ece4; }
.tabs button { color: #8b7d70; }
.tabs button.active { color: #4a3525; }
.ex-stat { background: #f4f8f1; }
.ex-stat .value { color: #4a3525; }
.ico-flame { color: #b06a3a; }
.ico-step { color: #6b8f3f; }
.ico-clock { color: #5f8fae; }
.mood { background: #fbf6e8; border-color: #f1e7cd; }
.mood-title { color: #6f5a3a; }
.mood-title .icon { color: #a9653a; }
.mood textarea::placeholder { color: #b3a58c; }

/* 运动类型 */
.sport-option { background: #f5f8f1; border-color: #e4ece4; }
.sport-option:hover { border-color: #cfdcc7; }
.sport-option.selected {
  background: #e8f2d8;
  border-color: #c8dcae;
  box-shadow: 0 0 0 2px #edf5df;
}
.active-sport {
  background: #e8f2d8;
  border-color: #d5e6bd;
  color: #6e3a18;
}
.active-sport b { color: #8b4a22; }

.sport-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0 0 16px;
}

.sport-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #f1f7e8;
  color: #6e3a18;
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 12px;
}

.sport-pill .icon { width: 15px; height: 15px; color: #8b4a22; }

/* 科学变美 */
.beauty-result { background: #f4f8f1; }
.goal-stat .value { color: #4a3525; }
.progress-label b { color: #8b4a22; }
.progress-bar { background: #e4ece0; }
.progress-bar i { background: linear-gradient(90deg, #8b4a22, #9fc6e4); }
.plan-summary { color: #7a6b4c; }
.plan-day { color: #4a3525; }

/* 女性健康 */
.female-card { background: #f1f7e8; border-color: #dfeacd; }
.female-title .icon, .f-item .icon, .status-title .icon { color: #8b4a22; }
.female-title { color: #4a3525; }
.f-item b { color: #4a3525; }
.f-item select { color: #4a3525; }
.tag { background: #e4f0cf; color: #6e3a18; }
.tag.add { background: #fff; border-color: #c9dcae; color: #8b6b4a; }
.tag.add:hover { background: #f8fbef; }
.tip-pink { background: #f3f8ea; color: #7a6b4c; }
.tag-option.selected { background: #e4f0cf; border-color: #c9dcae; color: #6e3a18; }
.tag .x:hover { background: rgba(110, 58, 24, 0.12); }

/* 家人健康 */
.family-card { background: #eaf3fb; border-color: #d8e7f4; }
.family-title .icon { color: #5f8fae; }
.family-card .btn-soft { border-color: #cfe0ef; color: #4f7898; }
.family-card .btn-soft:hover { background: #f6faff; }
.family-card .tag { background: #dcecf8; color: #4f7898; }
.family-card .tag.add { background: #fff; border-color: #c5daf7; color: #86a6ce; }
.family-card .tag-option.selected { background: #dcecf8; border-color: #c5daf7; color: #4f7898; }
.tip-blue { background: #eef6fd; color: #5f7f96; }
.reminder-count { background: #f6ede4; color: #8b4a22; }
.reminder-badge.today { background: #f6ede4; color: #8b4a22; }
.reminder-check { border-color: #cfd8c5; }
.reminder-item.done .reminder-check {
  background: #8b4a22;
  border-color: #8b4a22;
  color: #fff;
}

/* 睡眠 */
.sleep-card {
  background: linear-gradient(135deg, #8b4a22, #6e3a18);
  box-shadow: 0 18px 40px rgba(110, 58, 24, 0.28);
}
.sleep-icon { background: rgba(255, 255, 255, 0.1); color: #d7e8b9; }
.sleep-card p { color: #eadfce; }
.btn-sleep { background: #d7e8b9; color: #6e3a18; }
.btn-sleep:hover { background: #e2f0c9; }

/* 科普 */
.news-img.purple { background: linear-gradient(135deg, #f7ece2, #f1e1d4); color: #8b4a22; }
.news-cat.purple { color: #8b4a22; }

/* 上传与识别 */
.upload-box { background: #f5f8f1; border-color: #dbe6d8; }
.upload-box:hover { border-color: #c8dcae; background: #f8fbf3; }
.upload-status.scanning { color: #8b4a22; }
.upload-status.scanning::before {
  border-color: #f0e4d7;
  border-top-color: #8b4a22;
}
.chip { background: #e4f0cf; color: #6e3a18; }
.report-summary { background: #f1f8e9; border-color: #dfeacd; color: #6e5a3a; }
.report-item { background: #f4f8f1; }
.report-item .value { color: #4a3525; }

/* 弹窗与表单 */
.modal-head { background: linear-gradient(135deg, #8b4a22, #a9653a); }
.field input:focus, .field select:focus {
  border-color: #c8a585;
  box-shadow: 0 0 0 2px #f6ede4;
}
.modal { box-shadow: 0 24px 60px rgba(74, 53, 37, 0.25); }
.tag-menu { border-color: #e4ece4; box-shadow: 0 14px 34px rgba(74, 53, 37, 0.16); }
.tag-menu h4 { color: #8b7d70; }

/* 登录与资料填写 */
.auth-layer {
  background:
    radial-gradient(circle at 12% 18%, rgba(201, 227, 167, 0.45), transparent 42%),
    radial-gradient(circle at 88% 24%, rgba(147, 189, 224, 0.35), transparent 40%),
    #eef6ef;
}
.login-brand { color: #6e3a18; }
.login-card { box-shadow: 0 20px 50px rgba(74, 53, 37, 0.12); }
.login-card h1 { color: #4a3525; }
.login-field input:focus {
  border-color: #c8a585;
  box-shadow: 0 0 0 3px #f3e8dd;
}
.login-hint { background: #eef6ef; color: #8b7d70; }
.login-hint b { color: #8b4a22; }
.login-error { color: #b3482f; }
.pref-chip { background: #f5f8f1; border-color: #e4ece4; color: #6f6154; }
.pref-chip.selected { background: #e4f0cf; border-color: #c8dcae; color: #6e3a18; }
.ob-field input:focus, .ob-field select:focus { border-color: #c8a585; }

/* 聊天 */
.chat-head { background: linear-gradient(135deg, #5d9c43, #3f9c72); }
.msg.user { background: #8b4a22; }
.chat-send { background: #8b4a22; }
.chat-send:hover { background: #a9653a; }
.chat-input input:focus { border-color: #c8a585; }
.chat-body { background: #f5f8f1; }
.msg.bot { color: #5c4d40; }

/* 轻提示 */
.toast { background: rgba(74, 53, 37, 0.94); }

/* ==========================================================
   14. 响应式适配（窄屏）
   ========================================================== */
@media (max-width: 900px) {
  .sidebar {
    position: static;
    width: auto;
    height: auto;
    padding: 10px 14px;
    border-right: 0;
    border-bottom: 1px solid var(--line);
    flex-direction: row;
    align-items: center;
    gap: 12px;
    overflow-x: auto;
  }
  .side-brand { padding: 0; }
  .side-brand span { display: none; }
  .side-nav {
    flex-direction: row;
    gap: 4px;
    flex: 1;
    overflow-x: auto;
  }
  .side-nav button { width: auto; padding: 8px 10px; white-space: nowrap; }
  .side-nav button.active::before { display: none; }
  .side-user { padding: 4px; margin-left: auto; }
  .side-user-info { display: none; }
  .main-area { margin-left: 0; }

  .health-card { flex-direction: column; }
  .vital-side { width: 100%; flex: none; }
  .report-link { align-self: flex-end; }
  .hero { gap: 14px; padding: 14px 16px; }
  .score-group { gap: 8px; }
  .vitals { grid-template-columns: repeat(2, 1fr); }
  .report-grid { grid-template-columns: repeat(2, 1fr); }
  .sport-modal { width: 100%; }
  .sport-grid { grid-template-columns: repeat(2, 1fr); }

  .ex-stats { grid-template-columns: repeat(2, 1fr); }
  .female-grid { grid-template-columns: 1fr; }
  .family-grid { grid-template-columns: 1fr; }
  .news-grid { grid-template-columns: 1fr; }
  .onboarding-grid { grid-template-columns: 1fr; }
  .beauty-body { grid-template-columns: 1fr; }
  .chat { right: 12px; left: 12px; width: auto; }
}

/* 窄屏：标题在上，三个评分仍保持一行 */
@media (max-width: 700px) {
  .hero { flex-direction: column; align-items: stretch; gap: 10px; padding: 14px 16px; }
  .score-group { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}

@media (max-width: 560px) {
  .container { padding: 0 16px; }
  .hero { padding: 16px 16px 18px; flex-direction: column; align-items: stretch; gap: 10px; }
  .hero-title h1 { font-size: 21px; letter-spacing: 2px; }
  .hero-title p { font-size: 12px; }
  .hero-underline { width: 38px; height: 3px; margin-top: 6px; }
  .score-group { gap: 8px; }
  .score { grid-template-columns: 26px minmax(0, 1fr); padding: 7px 8px; gap: 6px; }
  .score .score-ico { width: 26px; height: 26px; }
  .score .score-ico .icon { width: 14px; height: 14px; }
  .score .row { font-size: 11px; margin-bottom: 4px; }
  .score .score-num { font-size: 9px; }
  .score .score-num b { font-size: 15px; }
  .macros { grid-template-columns: repeat(2, 1fr); }
  .female-card { padding: 18px; }
  .family-card { padding: 18px; }
  .tag-menu { width: 230px; right: 6px; }
  .sleep-card { padding: 36px 20px; }
  .login-card { padding: 24px; }
  .onboarding-wrap { padding: 28px 16px 40px; }
  .onboarding-head { flex-direction: column; align-items: flex-start; }
  .goal-stats { grid-template-columns: 1fr; }
  .plan-week { grid-template-columns: 1fr; }
}
/* ==========================================================
   12. 新增功能样式：体征编辑 / 体重曲线 / 每日计划勾选 /
       饮食营养 / 每日心情 / 运动目标 / 科普详情 / 提醒删除
   ========================================================== */

/* 体征编辑 */
.vital-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.vital-edit {
  border: none;
  background: transparent;
  color: #a98a72;
  font-size: 11px;
  padding: 0;
  cursor: pointer;
}

.vital-edit:hover { color: #8b4a22; }

.vital-edit-box {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.vital-edit-box input {
  width: 62px;
  height: 32px;
  border: 1px solid #e2d6c8;
  border-radius: 8px;
  padding: 0 8px;
  font-size: 13px;
  color: #4a3525;
  background: #fff;
}

.vital-edit-box button {
  border: none;
  border-radius: 8px;
  background: #8b4a22;
  color: #fff;
  font-size: 12px;
  padding: 7px 12px;
  cursor: pointer;
}

.vital-edit-box button.ghost { background: #f1ece5; color: #8b6b52; }

/* 体重趋势图 */
.weight-chart {
  margin-top: 14px;
  background: #fbf7f1;
  border-radius: 12px;
  padding: 10px 8px 6px;
}

.weight-chart svg { width: 100%; height: auto; display: block; }
.weight-chart svg text { font-size: 9px; fill: #a08d7d; }

.weight-chart-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #8b7d70;
  padding: 0 6px 4px;
}

.weight-chart-head b { color: #8b4a22; }

.weight-chart-empty {
  font-size: 12px;
  color: #a08d7d;
  text-align: center;
  padding: 18px 6px;
  line-height: 1.8;
}

/* 每日计划勾选 */
.plan-day {
  display: grid;
  grid-template-columns: 22px 40px 1fr;
  align-items: center;
  justify-content: initial;
}

.plan-check {
  width: 20px;
  height: 20px;
  border: 1.5px solid #d3c4b2;
  border-radius: 6px;
  background: #fff;
  color: transparent;
  font-size: 11px;
  line-height: 1;
  padding: 0;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.plan-day.done .plan-check {
  background: #8b4a22;
  border-color: #8b4a22;
  color: #fff;
}

.plan-day.done span:last-child {
  text-decoration: line-through;
  color: #b3a595;
}

/* 科学变美：饮食种类推荐 */
.beauty-diet {
  margin-top: 14px;
  background: #f4f9ea;
  border: 1px solid #e2ecd0;
  border-radius: 12px;
  padding: 12px 14px;
}

.beauty-diet b { font-size: 13px; color: #5d7a35; }

.beauty-diet ul {
  margin: 8px 0 0;
  padding-left: 18px;
  color: #6f7b57;
  font-size: 12px;
  line-height: 1.9;
}

/* 饮食：每日营养摄入 */
.nutri-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
}

.nutri-head {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #7a6b5c;
  margin-bottom: 5px;
}

.nutri-head b { color: #8b4a22; }

.nutri-bar {
  height: 8px;
  border-radius: 999px;
  background: #f0eae2;
  overflow: hidden;
}

.nutri-bar i {
  display: block;
  height: 100%;
  width: 0;
  border-radius: 999px;
  background: linear-gradient(90deg, #8b4a22, #c08a5a);
  transition: width 0.35s ease;
}

.nutri-bar.over i { background: linear-gradient(90deg, #b06a3a, #d9a340); }

/* 饮食：今日记录标签 */
.meal-log {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.meal-log-item {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #f8f2e9;
  color: #7a6350;
  font-size: 12px;
  padding: 5px 10px;
  border-radius: 999px;
  line-height: 1.6;
}

.meal-log-item button {
  border: none;
  background: transparent;
  color: #b99b85;
  font-size: 13px;
  line-height: 1;
  padding: 0;
  cursor: pointer;
}

.meal-log-item button:hover { color: #b0402f; }

.meal-log-empty {
  font-size: 12px;
  color: #a08d7d;
  padding: 4px 0;
}

/* 饮食：两周对比 */
.week-compare table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.week-compare th,
.week-compare td {
  padding: 8px 4px;
  text-align: center;
  border-bottom: 1px solid #f1eae0;
  color: #7a6b5c;
}

.week-compare th { color: #a08d7d; font-weight: 600; }
.week-compare td.up { color: #b06a3a; }
.week-compare td.down { color: #6b8f3f; }

.mini-bars {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  height: 86px;
  margin-top: 14px;
}

.mini-bar {
  flex: 1;
  text-align: center;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  height: 100%;
  gap: 4px;
}

.mini-bar i {
  display: block;
  border-radius: 5px 5px 0 0;
  background: linear-gradient(180deg, #c08a5a, #8b4a22);
  min-height: 4px;
}

.mini-bar span { font-size: 10px; color: #a08d7d; }

.mini-bar em { font-style: normal; font-size: 10px; color: #8b4a22; }

/* 运动：目标与数据填写 */
.sport-inputs {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-top: 12px;
}

.sport-inputs .field label { font-size: 12px; color: #8b7d70; }

.sport-inputs input {
  width: 100%;
  height: 38px;
  border: 1px solid #e6dbcd;
  border-radius: 10px;
  background: #fbf8f4;
  padding: 0 10px;
  font-size: 13px;
  color: #4a3525;
}

.sport-actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

/* 每日心情 */
.mood-picker {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.mood-opt {
  border: 1px solid #efe4cd;
  background: #fff;
  border-radius: 999px;
  padding: 7px 14px;
  font-size: 12px;
  color: #7a6b5c;
  cursor: pointer;
}

.mood-opt.selected {
  background: #8b4a22;
  border-color: #8b4a22;
  color: #fff;
}

.mood-tip {
  margin-top: 10px;
  font-size: 12px;
  color: #7a6b5c;
  line-height: 1.85;
  background: #fffdf7;
  border-radius: 10px;
  padding: 10px 12px;
}

/* 科普资讯详情 */
.news-detail { max-width: 720px; }

.news-article h4 {
  font-size: 14px;
  color: #4a3525;
  margin: 16px 0 6px;
}

.news-article p {
  font-size: 13px;
  color: #6b5c4c;
  line-height: 1.9;
  margin: 6px 0;
}

.news-article ul {
  margin: 6px 0 6px 18px;
  color: #6b5c4c;
  font-size: 13px;
  line-height: 1.9;
}

.news-article .note {
  font-size: 12px;
  color: #a08d7d;
  border-top: 1px dashed #e8ded0;
  padding-top: 10px;
  margin-top: 14px;
}

.news-body .read-more {
  display: inline-block;
  margin-top: 10px;
  font-size: 12px;
  color: #8b4a22;
  font-weight: 600;
}

/* 关怀提醒删除 */
.reminder-del {
  flex: none;
  border: none;
  background: transparent;
  color: #c0a895;
  font-size: 12px;
  padding: 2px 4px;
  cursor: pointer;
  margin-left: 4px;
}

.reminder-del:hover { color: #b0402f; }

/* 顶部三项评分：综合 / 饮食 / 运动，随数据自动更新 */
.score-group .score {
  flex: 1;
  margin-top: 0;
  max-width: none;
}

.score-group .score .row b { font-weight: 700; }
.score-group .bar i { width: 0; }

/* 科普资讯搜索 */
.news-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.news-search {
  flex: 1;
  min-width: 200px;
  display: flex;
  align-items: center;
  gap: 8px;
  height: 42px;
  padding: 0 14px;
  background: #fff;
  border: 1px solid #e6dbcd;
  border-radius: 12px;
}

.news-search .icon {
  width: 16px;
  height: 16px;
  color: #a08d7d;
  flex: none;
}

.news-search input {
  flex: 1;
  border: 0;
  outline: none;
  background: transparent;
  font-size: 13px;
  color: #4a3525;
}

.news-count { font-size: 12px; color: #8b7d70; }

.news-empty {
  font-size: 13px;
  color: #a08d7d;
  text-align: center;
  padding: 40px 0;
  background: #fff;
  border-radius: 14px;
}

/* 可点击的运动数据卡片 */
.ex-stat {
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s;
}

.ex-stat:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 18px rgba(74, 53, 37, 0.1);
}

.ex-stat .hint {
  font-size: 10px;
  color: #b3a595;
  margin-top: 4px;
}

/* 运动分类可直接点击开始 */
.sport-pill { cursor: pointer; }
.sport-pill:hover { background: #f3ece3; }

.active-sport .timer {
  font-variant-numeric: tabular-nums;
  color: #8b4a22;
  font-weight: 700;
  margin-left: 8px;
}

/* 本周统计：日历图标 */
.week-panel { display: none; }
.week-panel.active { display: block; }

.week-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 8px;
}

.week-day {
  background: #fff;
  border: 1px solid #efe6da;
  border-radius: 12px;
  padding: 10px 5px;
  text-align: center;
  cursor: pointer;
}

.week-day .date { font-size: 11px; color: #a08d7d; }

.week-day .icon {
  width: 22px;
  height: 22px;
  margin: 6px auto 4px;
  color: #8b4a22;
  display: block;
}

.week-day .emoji { font-size: 16px; display: block; margin: 4px 0; }
.week-day .kcal { font-size: 10px; color: #8b7d70; }

.week-day.selected {
  border-color: #8b4a22;
  background: #fbf3ea;
}

.week-day.empty { opacity: 0.55; }

.week-detail {
  margin-top: 12px;
  background: #fbf7f1;
  border-radius: 12px;
  padding: 12px 14px;
  font-size: 12px;
  color: #7a6b5c;
  line-height: 1.9;
}

/* 每日心情：一周表情记录 */
.mood-week {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.mood-week .day {
  flex: 1;
  text-align: center;
  background: #fff;
  border: 1px solid #efe4cd;
  border-radius: 10px;
  padding: 8px 4px;
  cursor: pointer;
}

.mood-week .day .emoji { font-size: 16px; display: block; }
.mood-week .day .date { font-size: 10px; color: #a08d7d; }

.mood-week .day.selected {
  border-color: #8b4a22;
  background: #fbf3ea;
}

/* 营养计算依据说明 */
.nutri-note {
  margin-top: 10px;
  font-size: 11px;
  color: #a08d7d;
  line-height: 1.8;
}

/* 自定义标签输入 */
.pref-custom-row { margin-top: 8px; }

.pref-custom-input {
  width: 100%;
  height: 38px;
  border: 1px dashed #cfc0ae;
  border-radius: 10px;
  padding: 0 12px;
  font-size: 12px;
  color: #4a3525;
  background: #fbf8f4;
  outline: none;
}

.pref-custom-input:focus { border-color: #8b4a22; border-style: solid; }

/* 核心数据修改弹窗 */
.vital-history-title {
  font-size: 13px;
  color: #4a3525;
  margin: 16px 0 8px;
}

.vital-history { font-size: 12px; color: #7a6b5c; }

.vital-history-row {
  display: flex;
  justify-content: space-between;
  padding: 7px 2px;
  border-bottom: 1px dashed #f0e9df;
}

.vital-history-row span:first-child { color: #a08d7d; }
.vital-history-empty { color: #a08d7d; font-size: 12px; padding: 6px 0; }

/* 生理期弹窗美化 */
.period-modal .modal-head {
  background: linear-gradient(135deg, #8b4a22, #b06a3a);
}

.period-tip {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  background: #fdf1f6;
  color: #8a5b6b;
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 12px;
  line-height: 1.7;
  margin-bottom: 14px;
}

.period-tip .icon { width: 16px; height: 16px; color: #c9789a; flex: none; margin-top: 2px; }

.period-dates { display: flex; align-items: flex-end; gap: 8px; }

.period-date-field {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.period-date-field label { font-size: 12px; color: #8b7d70; }

.period-date-field input {
  width: 100%;
  height: 46px;
  border: 1px solid #e6dbcd;
  border-radius: 12px;
  padding: 0 12px;
  font-size: 14px;
  color: #4a3525;
  background: #fbf8f4;
}

.period-arrow { padding-bottom: 12px; color: #c0a895; }
.period-arrow .icon { width: 18px; height: 18px; }

.period-preview { display: flex; gap: 10px; margin-top: 14px; }

.period-preview .pp-item {
  flex: 1;
  background: #fdf5ef;
  border: 1px solid #f3e3d6;
  border-radius: 12px;
  padding: 10px 12px;
}

.period-preview span { display: block; font-size: 11px; color: #a08d7d; }
.period-preview b { display: block; margin-top: 4px; font-size: 15px; color: #8b4a22; }

/* 食物分量弹窗 */
.food-modal { max-width: 560px; }

.food-summary {
  font-size: 13px;
  color: #4a3525;
  line-height: 1.8;
  margin-bottom: 12px;
}

.food-portions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.food-portion-row {
  display: flex;
  justify-content: space-between;
  background: #fbf7f1;
  border-radius: 10px;
  padding: 9px 12px;
  font-size: 12px;
  color: #7a6b5c;
}

.food-portion-row b { color: #8b4a22; }

.food-total {
  margin-top: 10px;
  background: #f4f9ea;
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 12px;
  color: #5d7a35;
  line-height: 1.8;
}

/* 运动板块选择 */
.sport-boards {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.sport-board {
  background: #fbf7f1;
  border: 1px solid #efe4d7;
  border-radius: 14px;
  padding: 16px 14px;
  text-align: left;
  cursor: pointer;
}

.sport-board:hover { border-color: #c9a98d; background: #f8f1e8; }
.sport-board b { display: block; font-size: 14px; color: #4a3525; }
.sport-board span { display: block; font-size: 11px; color: #a08d7d; margin-top: 4px; }

.sport-board-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  font-size: 12px;
  color: #8b7d70;
}

/* 评分可点击查看分析 */
.score { cursor: pointer; }
.score:hover .row span:first-child { text-decoration: underline; }

/* 常用提醒 */
.quick-reminders {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  font-size: 12px;
  color: #a08d7d;
}

/* 提醒弹窗：多日期选择 */
.date-quick { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px; }

.date-add { display: flex; align-items: center; gap: 8px; }

.date-add input {
  flex: 1;
  height: 38px;
  padding: 0 12px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: #f8faf7;
  color: #475467;
  font-size: 13px;
}

.date-selected {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.date-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border-radius: 999px;
  background: #f2f8ec;
  border: 1px solid #dbe9cd;
  color: #4f7a37;
  font-size: 12px;
}

.date-tag button {
  border: 0;
  background: transparent;
  color: #8aa377;
  font-size: 13px;
  line-height: 1;
  padding: 0;
}

.date-tag button:hover { color: #b0402f; }

.date-empty { font-size: 12px; color: #aab2c0; }

.quick-chip {
  border: 1px solid #e6dbcd;
  background: #fbf8f4;
  color: #8b6b52;
  border-radius: 999px;
  padding: 5px 12px;
  font-size: 12px;
  cursor: pointer;
}

.quick-chip:hover { border-color: #c9a98d; background: #f7eee4; }

/* 家人卡片上的「最近记录」可点击 */
.family-line.clickable { cursor: pointer; }
.family-line.clickable:hover b { color: #8b4a22; text-decoration: underline; }

/* 家人记录弹窗 */
.member-record {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 9px 2px;
  border-bottom: 1px dashed #f0e9df;
  font-size: 12px;
  color: #7a6b5c;
}

.member-record .date { color: #a08d7d; flex: none; }
.member-record-empty { font-size: 12px; color: #a08d7d; padding: 8px 0; }

/* 评分分析弹窗 */
.score-modal { max-width: 560px; }

.score-hero { display: flex; align-items: baseline; gap: 6px; margin-bottom: 14px; }
.score-hero b { font-size: 34px; color: #8b4a22; line-height: 1; }
.score-hero span { font-size: 13px; color: #a08d7d; }

.score-hero em {
  font-style: normal;
  margin-left: auto;
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 999px;
  background: #f4f9ea;
  color: #5d7a35;
}

.score-body p { font-size: 13px; color: #6b5c4c; line-height: 1.9; margin: 6px 0; }
.score-body h4 { font-size: 13px; color: #4a3525; margin: 14px 0 6px; }
.score-body ul { margin: 6px 0 6px 18px; font-size: 13px; color: #6b5c4c; line-height: 1.9; }

@media (max-width: 700px) {
  .sport-inputs { grid-template-columns: 1fr; }
  .plan-day { grid-template-columns: 22px 36px 1fr; }
  .week-grid { grid-template-columns: repeat(4, 1fr); }
  .mood-week { flex-wrap: wrap; }
  .mood-week .day { flex: 1 1 28%; }
  .sport-boards { grid-template-columns: 1fr; }
  .period-dates { flex-direction: column; align-items: stretch; }
  .period-arrow { display: none; }
}
</style>
</head>
<body>

<!-- ========================================================
     SVG 图标库：集中定义，页面中通过 <use href="#id"> 引用
     ======================================================== -->
<svg xmlns="http://www.w3.org/2000/svg" style="display:none" aria-hidden="true">
  <symbol id="i-pulse" viewBox="0 0 24 24"><path d="M3 12h4l2.5-6 4 12L16 12h5"/></symbol>
  <symbol id="i-heart" viewBox="0 0 24 24"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 1 0-7.8 7.8L12 21l8.9-8.7a5.5 5.5 0 0 0-.1-7.7z"/></symbol>
  <symbol id="i-fork" viewBox="0 0 24 24"><path d="M7 3v8a2 2 0 0 0 4 0V3M9 11v10"/><path d="M17 3c-1.6 1.4-2.5 3.6-2.5 6.5 0 2.2 1 3.5 2.5 3.5V3z"/><path d="M17 13v8"/></symbol>
  <symbol id="i-dumbbell" viewBox="0 0 24 24"><path d="M6.5 6.5v11M3.5 9v6M17.5 6.5v11M20.5 9v6M6.5 12h11"/></symbol>
  <symbol id="i-activity" viewBox="0 0 24 24"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></symbol>
  <symbol id="i-female" viewBox="0 0 24 24"><circle cx="12" cy="8.5" r="4.5"/><path d="M12 13v8M9 18h6"/></symbol>
  <symbol id="i-moon" viewBox="0 0 24 24"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></symbol>
  <symbol id="i-user" viewBox="0 0 24 24"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-6.5 8-6.5s8 2.5 8 6.5"/></symbol>
  <symbol id="i-chevron" viewBox="0 0 24 24"><polyline points="6 9 12 15 18 9"/></symbol>
  <symbol id="i-close" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></symbol>
  <symbol id="i-calendar" viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="16" rx="2"/><line x1="16" y1="3" x2="16" y2="7"/><line x1="8" y1="3" x2="8" y2="7"/><line x1="3" y1="11" x2="21" y2="11"/></symbol>
  <symbol id="i-refresh" viewBox="0 0 24 24"><polyline points="23 4 23 10 17 10"/><path d="M20.5 15a9 9 0 1 1-2.1-9.4L23 10"/></symbol>
  <symbol id="i-droplet" viewBox="0 0 24 24"><path d="M12 2.7 6.5 9.2a7 7 0 1 0 11 0L12 2.7z"/></symbol>
  <symbol id="i-flame" viewBox="0 0 24 24"><path d="M12 2c3 4 6 6.5 6 10a6 6 0 0 1-12 0c0-2 1-3.5 2.5-5C9.5 8 10 6 12 2z"/></symbol>
  <symbol id="i-footprints" viewBox="0 0 24 24"><path d="M8.5 3.5c1.6 0 2.6 1.4 2.6 3.1 0 1.3-.5 2.1-.4 3 .1 1-.4 1.8-1.4 1.8H8c-1 0-1.6-.8-1.5-1.8.1-.9-.4-1.7-.4-3C6.1 4.9 7 3.5 8.5 3.5z"/><path d="M15.5 11c1.6 0 2.6 1.4 2.6 3.1 0 1.3-.5 2.1-.4 3 .1 1-.4 1.8-1.4 1.8H15c-1 0-1.6-.8-1.5-1.8.1-.9-.4-1.7-.4-3 0-1.7.9-3.1 2.4-3.1z"/></symbol>
  <symbol id="i-clock" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15 14"/></symbol>
  <symbol id="i-target" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/></symbol>
  <symbol id="i-play" viewBox="0 0 24 24"><polygon points="8 5 19 12 8 19 8 5"/></symbol>
  <symbol id="i-send" viewBox="0 0 24 24"><path d="M22 2 11 13"/><path d="M22 2l-7 20-4-9-9-4 20-7z"/></symbol>
  <symbol id="i-plus" viewBox="0 0 24 24"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></symbol>
  <symbol id="i-spark" viewBox="0 0 24 24"><path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9L12 3z"/><path d="M19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8L19 16z"/></symbol>
  <symbol id="i-image" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></symbol>
  <symbol id="i-smile" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/></symbol>
  <symbol id="i-chat" viewBox="0 0 24 24"><path d="M21 11.5a8.4 8.4 0 0 1-9 8.4 9 9 0 0 1-3.9-.9L3 21l1.9-5a8.4 8.4 0 0 1-.9-3.9 8.4 8.4 0 0 1 8.4-8.4 8.4 8.4 0 0 1 8.6 8.3z"/><line x1="8" y1="12" x2="8.01" y2="12"/><line x1="12" y1="12" x2="12.01" y2="12"/><line x1="16" y1="12" x2="16.01" y2="12"/></symbol>
  <symbol id="i-book" viewBox="0 0 24 24"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></symbol>
  <symbol id="i-search" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.6-3.6"/></symbol>
  <symbol id="i-bell" viewBox="0 0 24 24"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/></symbol>
  <symbol id="i-ball" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 7.2l3 2.2-1.1 3.4h-3.8L9 9.4l3-2.2z"/><path d="M12 3.2v4M4.3 9.6l4.7 1.6M19.7 9.6L15 11.2M7.2 20.1l2-4.3M16.8 20.1l-2-4.3"/></symbol>
  <symbol id="i-bike" viewBox="0 0 24 24"><circle cx="5.5" cy="17.5" r="3.5"/><circle cx="18.5" cy="17.5" r="3.5"/><path d="M5.5 17.5h5l3-7h-3M14.5 17.5l-2-7M12 7h3M15 6l3.5 11.5"/></symbol>
  <symbol id="i-run" viewBox="0 0 24 24"><circle cx="15" cy="4.5" r="2"/><path d="M13 8l-3 5 4 2 1 6M10 13l-4 3M14 15l4 2M9 21l2-6"/></symbol>
  <symbol id="i-swim" viewBox="0 0 24 24"><circle cx="7" cy="8" r="2"/><path d="M9 10l5 2 3-2M3 17c2-1.5 4-1.5 6 0s4 1.5 6 0 4-1.5 6 0"/><path d="M3 21c2-1.5 4-1.5 6 0s4 1.5 6 0 4-1.5 6 0"/></symbol>
  <symbol id="i-yoga" viewBox="0 0 24 24"><circle cx="12" cy="4.5" r="2"/><path d="M12 7v5M12 12l-5 3M12 12l5 3M7 21l5-6M17 21l-5-6"/></symbol>
  <symbol id="i-mountain" viewBox="0 0 24 24"><path d="M3 20l6-11 4 6 3-4 5 9H3z"/><circle cx="18" cy="5" r="2"/></symbol>
  <symbol id="i-leaf" viewBox="0 0 24 24"><path d="M20 4c-8 0-14 5-14 11 0 2 1 4 3 5 6 0 11-6 11-16z"/><path d="M4 21c2-5 6-9 11-12"/></symbol>
</svg>

<!-- ========================================================
     登录界面
     ======================================================== -->
<div class="auth-layer" id="loginView">
  <div class="login-wrap">
    <div class="login-brand">
      <div class="logo"><svg class="icon"><use href="#i-pulse"/></svg></div>
      <span>健康管理系统</span>
    </div>

    <div class="login-card">
      <h1>欢迎回来</h1>
      <p class="login-sub">登录后开始科学管理你的健康</p>

      <form id="loginForm" novalidate>
        <div class="login-field">
          <label for="loginAccount">账号</label>
          <input id="loginAccount" type="text" autocomplete="username" placeholder="请输入账号" value="AAA">
        </div>
        <div class="login-field">
          <label for="loginPassword">密码</label>
          <input id="loginPassword" type="password" autocomplete="current-password" placeholder="请输入密码" value="123456">
        </div>
        <div class="login-error" id="loginError" hidden></div>
        <button class="btn-primary login-btn" type="submit">登录</button>
      </form>

      <div class="login-hint">演示账号：<b>AAA</b>　密码：<b>123456</b></div>
      <div class="mobile-hint">手机与电脑连接同一 Wi-Fi 后访问：<br><a href="__MOBILE_URL__">__MOBILE_URL__</a></div>
    </div>
  </div>
</div>

<!-- ========================================================
     登录后的基本信息填写
     ======================================================== -->
<div class="auth-layer" id="onboardingView" hidden>
  <div class="onboarding-wrap">
    <div class="onboarding-head">
      <div>
        <h1>完善你的健康信息</h1>
        <p>填写后，我们会为你生成更贴合的健康建议与运动计划。</p>
      </div>
    </div>

    <form id="onboardingForm">
      <div class="onboarding-grid">

        <!-- 基本信息 -->
        <section class="onboarding-card">
          <h2><svg class="icon"><use href="#i-user"/></svg>基本信息</h2>
          <div class="ob-field">
            <label for="obName">昵称</label>
            <input id="obName" type="text" value="张三">
          </div>
          <div class="ob-row">
            <div class="ob-field">
              <label for="obGender">性别</label>
              <select id="obGender">
                <option value="女" selected>女</option>
                <option value="男">男</option>
              </select>
            </div>
            <div class="ob-field">
              <label for="obAge">年龄</label>
              <input id="obAge" type="number" value="28" min="1" max="120">
            </div>
          </div>
          <div class="ob-row">
            <div class="ob-field">
              <label for="obHeight">身高（cm）</label>
              <input id="obHeight" type="number" value="165">
            </div>
            <div class="ob-field">
              <label for="obWeight">体重（kg）</label>
              <input id="obWeight" type="number" step="0.1" value="60.0">
            </div>
          </div>
        </section>

        <!-- 健康情况 -->
        <section class="onboarding-card">
          <h2><svg class="icon"><use href="#i-heart"/></svg>健康情况</h2>
          <div class="ob-field">
            <label for="obSleep">睡眠质量</label>
            <select id="obSleep">
              <option>良好</option>
              <option selected>一般</option>
              <option>较差</option>
            </select>
          </div>
          <div class="ob-field">
            <label for="obExercise">运动频率</label>
            <select id="obExercise">
              <option>很少运动</option>
              <option selected>每周 1-2 次</option>
              <option>每周 3-4 次</option>
              <option>几乎每天</option>
            </select>
          </div>
          <div class="ob-field">
            <label for="obGoal">健康目标</label>
            <select id="obGoal">
              <option selected>减脂塑形</option>
              <option>增肌紧致</option>
              <option>保持健康</option>
              <option>改善睡眠</option>
              <option>改善体态</option>
            </select>
          </div>
          <div class="ob-field">
            <label>健康情况（可多选）</label>
            <div class="pref-chips" id="obConditions">
              <button type="button" class="pref-chip selected" data-value="无">无</button>
              <button type="button" class="pref-chip" data-value="高血压">高血压</button>
              <button type="button" class="pref-chip" data-value="高血脂">高血脂</button>
              <button type="button" class="pref-chip" data-value="糖尿病">糖尿病</button>
              <button type="button" class="pref-chip" data-value="脂肪肝">脂肪肝</button>
              <button type="button" class="pref-chip" data-value="胃病">胃病</button>
              <button type="button" class="pref-chip" data-value="贫血">贫血</button>
              <button type="button" class="pref-chip" data-value="甲状腺问题">甲状腺问题</button>
              <button type="button" class="pref-chip" data-value="过敏体质">过敏体质</button>
              <button type="button" class="pref-chip" data-value="颈椎不适">颈椎不适</button>
              <button type="button" class="pref-chip" data-value="关节不适">关节不适</button>
              <button type="button" class="pref-chip" data-value="睡眠不佳">睡眠不佳</button>
              <button type="button" class="pref-chip" data-value="月经不调">月经不调</button>
              <button type="button" class="pref-chip" data-value="焦虑情绪">焦虑情绪</button>
            </div>
            <div class="pref-custom-row">
              <input class="pref-custom-input" data-group="obConditions" placeholder="其他健康情况，输入后按回车添加">
            </div>
          </div>
        </section>

        <!-- 饮食偏好 -->
        <section class="onboarding-card">
          <h2><svg class="icon"><use href="#i-fork"/></svg>饮食偏好</h2>
          <div class="ob-row">
            <div class="ob-field">
              <label for="obTaste">口味</label>
              <select id="obTaste">
                <option selected>清淡</option>
                <option>适中</option>
                <option>重口</option>
              </select>
            </div>
            <div class="ob-field">
              <label for="obDietType">饮食类型</label>
              <select id="obDietType">
                <option selected>均衡饮食</option>
                <option>素食</option>
                <option>低糖</option>
                <option>高蛋白</option>
              </select>
            </div>
          </div>
          <div class="ob-field">
            <label for="obMeals">每日餐数</label>
            <select id="obMeals">
              <option>2 餐</option>
              <option selected>3 餐</option>
              <option>3 餐 + 加餐</option>
            </select>
          </div>
          <div class="ob-field">
            <label>忌口 / 过敏（可多选）</label>
            <div class="pref-chips" id="obRestrictions">
              <button type="button" class="pref-chip selected" data-value="无">无</button>
              <button type="button" class="pref-chip" data-value="辛辣">辛辣</button>
              <button type="button" class="pref-chip" data-value="海鲜">海鲜</button>
              <button type="button" class="pref-chip" data-value="花生">花生</button>
              <button type="button" class="pref-chip" data-value="坚果">坚果</button>
              <button type="button" class="pref-chip" data-value="乳制品">乳制品</button>
              <button type="button" class="pref-chip" data-value="鸡蛋">鸡蛋</button>
              <button type="button" class="pref-chip" data-value="牛肉">牛肉</button>
              <button type="button" class="pref-chip" data-value="大豆">大豆</button>
              <button type="button" class="pref-chip" data-value="麸质">麸质</button>
              <button type="button" class="pref-chip" data-value="酒精">酒精</button>
              <button type="button" class="pref-chip" data-value="咖啡因">咖啡因</button>
              <button type="button" class="pref-chip" data-value="高糖">高糖</button>
            </div>
            <div class="pref-custom-row">
              <input class="pref-custom-input" data-group="obRestrictions" placeholder="其他忌口，输入后按回车添加">
            </div>
          </div>
        </section>
      </div>

      <div class="onboarding-actions">
        <button type="button" class="link-skip" id="skipOnboarding">稍后完善</button>
        <button type="submit" class="btn-primary">保存并进入系统</button>
      </div>
    </form>
  </div>
</div>

<!-- ========================================================
     主应用（登录并完善信息后显示）
     ======================================================== -->
<div id="appShell" hidden>

<!-- ========================================================
     侧边导航
     ======================================================== -->
<aside class="sidebar">
  <div class="side-brand">
    <div class="logo"><svg class="icon"><use href="#i-pulse"/></svg></div>
    <span>健康管理系统</span>
  </div>

  <nav class="side-nav" id="nav">
    <button class="active" data-page="data"><svg class="icon"><use href="#i-pulse"/></svg>健康数据</button>
    <button data-page="diet"><svg class="icon"><use href="#i-fork"/></svg>饮食</button>
    <button data-page="sport"><svg class="icon"><use href="#i-dumbbell"/></svg>运动</button>
    <button data-page="family"><svg class="icon"><use href="#i-heart"/></svg>家人健康</button>
    <button data-page="news"><svg class="icon"><use href="#i-book"/></svg>科普资讯</button>
  </nav>

  <div class="side-user" id="userBtn" title="个人信息">
    <div class="avatar" id="sideAvatar"><svg class="icon"><use href="#i-user"/></svg></div>
    <div class="side-user-info">
      <span class="side-user-name" id="sideUserName">张三</span>
      <span class="side-user-sub" id="sideUserSub">女 · 165cm</span>
    </div>
    <svg class="icon caret"><use href="#i-chevron"/></svg>
  </div>
</aside>

<div class="main-area">
<main class="container">

  <!-- 所有页面共用的顶部横幅（紧凑版：标题 + 三评分同一行） -->
  <section class="hero">
    <div class="hero-head">
      <div class="hero-title">
        <h1>科学管理健康</h1>
        <p>遇见更好的自己</p>
        <div class="hero-underline"></div>
      </div>
    </div>

    <div class="score-group">
      <div class="score score-total" data-score="total" title="点击查看分析">
        <span class="score-ico"><svg class="icon"><use href="#i-heart"/></svg></span>
        <div class="score-main">
          <div class="row"><span>综合健康评分</span><span class="score-num"><b id="scoreTotal">0</b>/100</span></div>
          <div class="bar"><i id="scoreTotalBar"></i></div>
        </div>
      </div>

      <div class="score score-diet" data-score="diet" title="点击查看分析">
        <span class="score-ico"><svg class="icon"><use href="#i-leaf"/></svg></span>
        <div class="score-main">
          <div class="row"><span>饮食健康评分</span><span class="score-num"><b id="scoreDiet">0</b>/100</span></div>
          <div class="bar"><i id="scoreDietBar"></i></div>
        </div>
      </div>

      <div class="score score-sport" data-score="sport" title="点击查看分析">
        <span class="score-ico"><svg class="icon"><use href="#i-run"/></svg></span>
        <div class="score-main">
          <div class="row"><span>运动完成评分</span><span class="score-num"><b id="scoreSport">0</b>/100</span></div>
          <div class="bar"><i id="scoreSportBar"></i></div>
        </div>
      </div>
    </div>
  </section>

  <div class="content">

    <!-- ====================================================
         页面一：健康数据
         ==================================================== -->
    <section class="page active" id="page-data">
      <div class="card health-card">
        <div class="health-main">
          <div class="card-head">
            <div class="card-title">
              <svg class="icon heart"><use href="#i-heart"/></svg>核心体征
            </div>
          </div>

          <div class="vitals">
            <div class="vital">
              <div class="vital-head">
                <div class="label">体重</div>
                <button class="vital-edit" type="button" data-vital="weight">修改</button>
              </div>
              <div class="value"><span id="weightValue">60.0</span><span class="unit">kg</span></div>
            </div>
            <div class="vital">
              <div class="vital-head">
                <div class="label">体脂率</div>
                <button class="vital-edit" type="button" data-vital="fat">修改</button>
              </div>
              <div class="value"><span id="fatValue">24.0</span><span class="unit">%</span></div>
            </div>
            <div class="vital">
              <div class="vital-head">
                <div class="label">BMI</div>
                <button class="vital-edit" type="button" data-vital="bmi">修改</button>
              </div>
              <div class="value">
                <span id="bmiValue">22.0</span>
                <span class="badge" id="bmiBadge">正常</span>
              </div>
            </div>
            <div class="vital">
              <div class="vital-head">
                <div class="label">血压</div>
                <button class="vital-edit" type="button" data-vital="bp">修改</button>
              </div>
              <div class="value"><span id="bpValue">110/70</span><span class="unit">mmHg</span></div>
            </div>
            <div class="vital">
              <div class="vital-head">
                <div class="label">血糖（空腹）</div>
                <button class="vital-edit" type="button" data-vital="glucose">修改</button>
              </div>
              <div class="value"><span id="glucoseValue">5.2</span><span class="unit">mmol/L</span></div>
            </div>
          </div>
        </div>

        <!-- 右侧：正常值范围、异常提醒与 BMI 公式 -->
        <div class="vital-side">
          <div class="range-head">
            <span>正常值范围</span>
            <button class="report-link" id="quickReportUpload">上传体检报告 ›</button>
          </div>

          <div class="range-list">
            <div class="range-row">
              <span class="rr-name">体重</span>
              <span class="rr-ref" id="refWeight">—</span>
              <span class="rr-state muted" id="stateWeight">—</span>
            </div>
            <div class="range-row">
              <span class="rr-name">BMI</span>
              <span class="rr-ref">18.5–23.9</span>
              <span class="rr-state muted" id="stateBmi">—</span>
            </div>
            <div class="range-row">
              <span class="rr-name">体脂率</span>
              <span class="rr-ref" id="refFat">女 20%–30%</span>
              <span class="rr-state muted" id="stateFat">—</span>
            </div>
            <div class="range-row">
              <span class="rr-name">血压</span>
              <span class="rr-ref">＜120/80 mmHg</span>
              <span class="rr-state muted" id="stateBp">—</span>
            </div>
            <div class="range-row">
              <span class="rr-name">空腹血糖</span>
              <span class="rr-ref">3.9–6.1 mmol/L</span>
              <span class="rr-state muted" id="stateGlucose">—</span>
            </div>
          </div>

          <div class="abnormal-box ok" id="abnormalBox">
            <b>异常提醒</b>
            <ul id="abnormalList"><li>各项体征均在参考范围内，继续保持。</li></ul>
          </div>

          <div class="bmi-formula">
            <b>BMI 计算公式</b><br>
            <span class="formula-line">BMI = 体重（kg）÷ 身高（m）²</span><br>
            <span id="bmiFormulaValue">60.0 ÷ 1.65² ≈ 22.0</span><br>
            <span>参考标准：中国成人 BMI 18.5–23.9 为正常（WS/T 428-2013）；血压、血糖参考《中国高血压防治指南》《中国 2 型糖尿病防治指南》。异常结果请以医院检查为准。</span>
          </div>
        </div>
      </div>

      <!-- 体检报告分析：上传图片并识别关键指标 -->
      <div class="card report-card" id="reportCard">
        <div class="card-head">
          <div class="card-title">
            <svg class="icon"><use href="#i-book"/></svg>体检报告分析
          </div>
          <span class="report-sub">上传报告图片，自动识别关键指标</span>
        </div>

        <div class="upload-box" id="reportUploadBox">
          <input type="file" id="reportImageInput" accept="image/*" hidden>

          <div class="upload-empty" id="reportUploadEmpty">
            <svg class="icon"><use href="#i-image"/></svg>
            <p>上传体检报告照片，识别体重、体脂、BMI、血压、血糖等指标</p>
            <button class="btn-soft" type="button" id="reportChooseBtn">选择图片</button>
          </div>

          <div class="upload-preview" id="reportPreview" hidden>
            <img id="reportPreviewImg" alt="体检报告照片">
            <div class="upload-info">
              <div class="upload-file" id="reportFileName"></div>
              <div class="upload-status" id="reportStatus"></div>
              <div class="upload-actions">
                <button class="btn-ghost-sm" type="button" id="reportReselect">重新上传</button>
              </div>
            </div>
          </div>
        </div>

        <div class="report-result" id="reportResult" hidden>
          <div class="report-meta">识别结果 · 报告日期 <span id="reportDateText">2026年10月20日</span></div>
          <div class="report-grid">
            <div class="report-item">
              <div class="label">体重</div>
              <div class="value">64.8<span class="unit">kg</span></div>
            </div>
            <div class="report-item">
              <div class="label">体脂率</div>
              <div class="value">24.0<span class="unit">%</span></div>
            </div>
            <div class="report-item">
              <div class="label">BMI</div>
              <div class="value">23.8</div>
            </div>
            <div class="report-item">
              <div class="label">血压</div>
              <div class="value">112/72<span class="unit">mmHg</span></div>
            </div>
            <div class="report-item">
              <div class="label">血糖</div>
              <div class="value">5.0<span class="unit">mmol/L</span></div>
            </div>
          </div>
          <div class="report-summary">综合分析：各项指标总体处于正常范围。建议保持每周 3 次有氧运动，晚餐适当补充优质蛋白，并在 3 个月后复查。</div>
          <div class="report-actions">
            <button class="btn-primary" id="applyReport">同步到核心体征</button>
          </div>
        </div>
      </div>

      <!-- 睡眠板块（并入健康数据） -->
      <div class="sleep-inline" id="sleepSection">
        <div class="sleep-card">
          <div class="sleep-icon"><svg class="icon"><use href="#i-moon"/></svg></div>
          <h2>优质睡眠，恢复活力</h2>
          <p>连接你的智能手表或手动记录，分析睡眠周期与质量。</p>
          <button class="btn-sleep" data-toast="已开始记录睡眠，请保持设备佩戴">开始记录睡眠</button>
        </div>
      </div>

      <!-- 女性用户专属：女性健康档案（男性用户会自动隐藏） -->
      <div class="female-health" id="femaleHealthSection">
        <div class="female-card">
          <div class="female-head">
            <div class="female-title">
              <svg class="icon"><use href="#i-droplet"/></svg>女性健康档案
            </div>
            <button class="btn-soft" id="openPeriod">记录生理期</button>
          </div>

          <div class="female-grid">
            <!-- 左侧：周期数据（长度可自由选择） -->
            <div>
              <div class="f-item">
                <span class="left"><svg class="icon"><use href="#i-calendar"/></svg>经期长度</span>
                <select id="periodDays" aria-label="经期长度"></select>
              </div>
              <div class="f-item">
                <span class="left"><svg class="icon"><use href="#i-refresh"/></svg>周期长度</span>
                <select id="cycleDaysMain" aria-label="周期长度"></select>
              </div>
              <div class="f-item">
                <span class="left"><svg class="icon"><use href="#i-droplet"/></svg>排卵日预测</span>
                <b id="ovulationDate">10月25日</b>
              </div>
              <div class="f-item">
                <span class="left"><svg class="icon"><use href="#i-calendar"/></svg>最近一次经期</span>
                <b id="lastPeriodRange">10月11日 - 10月15日</b>
              </div>
            </div>

            <!-- 右侧：今日状态（从预设选项中多选） -->
            <div class="status-card">
              <div class="status-title">
                <svg class="icon"><use href="#i-calendar"/></svg>今日状态记录
              </div>
              <div class="tags" id="femaleTags">
                <button class="tag add" id="femaleAddTag" type="button">+ 添加标签</button>
              </div>
              <div class="tag-menu" id="femaleTagMenu">
                <h4>选择今日状态（可多选）</h4>
                <div class="tag-options" id="femaleTagOptions"></div>
                <div class="tag-menu-foot">
                  <button class="btn-mini" type="button" data-close-tag>确定</button>
                </div>
              </div>
              <div class="tip-pink" id="statusTip">科学建议：记录今日状态后，这里会给出对应的护理建议。</div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ====================================================
         页面二：饮食
         ==================================================== -->
    <section class="page" id="page-diet">
      <div class="diet-wrap">
        <div class="card">
          <div class="card-head">
            <div class="card-title">
              <svg class="icon fork"><use href="#i-fork"/></svg>饮食与营养计算
            </div>
          </div>

          <!-- 每日营养目标：数值由 JavaScript 根据个人资料自动计算 -->
          <div class="macros">
            <div class="macro"><div class="label">蛋白质</div><div class="value" id="macroProtein">0g</div></div>
            <div class="macro"><div class="label">碳水</div><div class="value" id="macroCarb">0g</div></div>
            <div class="macro"><div class="label">纤维素</div><div class="value" id="macroFiber">0g</div></div>
            <div class="macro"><div class="label">脂肪</div><div class="value" id="macroFat">0g</div></div>
            <div class="macro"><div class="label">总热量</div><div class="value" id="macroKcal">0k</div></div>
          </div>

          <!-- 活动水平由用户选择，避免系统凭空猜测运动量 -->
          <div class="field" style="margin-top:16px;max-width:340px">
            <label for="dietActivity">日常活动水平（决定热量目标）</label>
            <select id="dietActivity">
              <option value="1.2">久坐为主 · 几乎不运动</option>
              <option value="1.375" selected>轻度活动 · 每周 1-3 次</option>
              <option value="1.55">中度活动 · 每周 3-5 次</option>
              <option value="1.725">高强度 · 每周 6-7 次</option>
            </select>
          </div>

          <h3 class="sub-title">今日饮食记录</h3>

          <!-- 回车或点击「记录」即可记录一条饮食 -->
          <div class="meal">
            <span class="meal-tag morning">早</span>
            <input data-meal="早餐" placeholder="例如：一杯牛奶，两片全麦面包...">
            <button class="meal-btn" type="button" data-meal-btn="早餐">记录</button>
          </div>
          <div class="meal">
            <span class="meal-tag noon">中</span>
            <input data-meal="午餐" placeholder="记录午餐...">
            <button class="meal-btn" type="button" data-meal-btn="午餐">记录</button>
          </div>
          <div class="meal">
            <span class="meal-tag night">晚</span>
            <input data-meal="晚餐" placeholder="记录晚餐...">
            <button class="meal-btn" type="button" data-meal-btn="晚餐">记录</button>
          </div>

          <!-- 今日已记录的食物，可单条删除 -->
          <div class="meal-log" id="mealLog"></div>

          <h3 class="sub-title">今日营养摄入</h3>
          <div class="nutri-list" id="nutriList"></div>
          <div class="nutri-note" id="nutriNote"></div>

          <h3 class="sub-title">近两周饮食分析</h3>
          <div class="week-compare" id="weekCompare"></div>

          <h3 class="sub-title">餐食图片识别</h3>

          <!-- 上传餐食照片，识别食物与热量 -->
          <div class="upload-box" id="dietUploadBox">
            <input type="file" id="dietImageInput" accept="image/*" hidden>

            <div class="upload-empty" id="dietUploadEmpty">
              <svg class="icon"><use href="#i-image"/></svg>
              <p>上传餐食照片，自动识别食物种类与大致热量</p>
              <button class="btn-soft" type="button" id="dietChooseBtn">选择图片</button>
            </div>

            <div class="upload-preview" id="dietPreview" hidden>
              <img id="dietPreviewImg" alt="餐食照片">
              <div class="upload-info">
                <div class="upload-file" id="dietFileName"></div>
                <div class="upload-status" id="dietStatus"></div>
                <div class="upload-result" id="dietResult" hidden></div>
                <div class="upload-actions">
                  <button class="btn-ghost-sm" type="button" id="dietReselect">重新上传</button>
                  <button class="btn-ghost-sm" type="button" id="dietFillMeal" hidden>填入午餐记录</button>
                </div>
              </div>
            </div>
          </div>

          <div class="tip-card">
            <svg class="icon"><use href="#i-spark"/></svg>
            <div>
              <b>推荐补充</b>
              <p id="dietTipText">今日蛋白质摄入略低，晚餐可增加一份鸡胸肉、鸡蛋或豆制品，帮助肌肉修复与饱腹感提升。</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ====================================================
         页面三：运动
         ==================================================== -->
    <section class="page" id="page-sport">
      <div class="exercise-wrap">
        <div class="card">
          <div class="card-head">
            <div class="card-title">
              <svg class="icon activity-icon"><use href="#i-activity"/></svg>运动与心理状态
            </div>
            <button class="btn-primary" id="startSport">
              <svg class="icon"><use href="#i-play"/></svg>开始运动
            </button>
          </div>

          <!-- 当前正在进行的运动 -->
          <div class="active-sport" id="activeSport" hidden>
            <svg class="icon"><use href="#i-activity"/></svg>
            <span>当前运动：<b id="activeSportName"></b></span>
            <span class="timer" id="sportTimer">00:00</span>
            <button class="end" type="button" id="stopSport">结束</button>
          </div>

          <!-- 运动元素：点击任意分类可直接开始该运动 -->
          <div class="sport-strip">
            <span class="sport-pill" data-sport="球类运动"><svg class="icon"><use href="#i-ball"/></svg>球类</span>
            <span class="sport-pill" data-sport="户外骑行"><svg class="icon"><use href="#i-bike"/></svg>骑行</span>
            <span class="sport-pill" data-sport="跑步"><svg class="icon"><use href="#i-run"/></svg>跑步</span>
            <span class="sport-pill" data-sport="游泳"><svg class="icon"><use href="#i-swim"/></svg>游泳</span>
            <span class="sport-pill" data-sport="登山"><svg class="icon"><use href="#i-mountain"/></svg>登山</span>
            <span class="sport-pill" data-sport="瑜伽"><svg class="icon"><use href="#i-yoga"/></svg>瑜伽</span>
          </div>

          <!-- 今日 / 本周 数据切换 -->
          <div class="tabs" id="sportTabs">
            <button class="active" data-tab="today">今日运动</button>
            <button data-tab="week">本周统计</button>
          </div>

          <div class="ex-stats" id="todayStats">
            <div class="ex-stat" data-field="kcal" title="点击修改已消耗热量">
              <div class="ico ico-flame"><svg class="icon"><use href="#i-flame"/></svg></div>
              <div class="value"><span id="exKcal">320</span> <span class="unit">kcal</span></div>
              <div class="label">已消耗</div>
              <div class="hint">点击填写</div>
            </div>
            <div class="ex-stat" data-field="steps" title="点击修改今日步数">
              <div class="ico ico-step"><svg class="icon"><use href="#i-footprints"/></svg></div>
              <div class="value"><span id="exSteps">6,540</span> <span class="unit">步</span></div>
              <div class="label">今日步数</div>
              <div class="hint">点击填写</div>
            </div>
            <div class="ex-stat" data-field="minutes" title="点击修改活动时长">
              <div class="ico ico-clock"><svg class="icon"><use href="#i-clock"/></svg></div>
              <div class="value"><span id="exMinutes">45</span> <span class="unit">分钟</span></div>
              <div class="label">活动时长</div>
              <div class="hint">点击填写</div>
            </div>
            <div class="ex-stat">
              <div class="ico">
                <svg width="44" height="44" viewBox="0 0 44 44" aria-hidden="true">
                  <circle cx="22" cy="22" r="18" fill="none" stroke="#e8eaf2" stroke-width="4"/>
                  <circle id="exGaugeArc" cx="22" cy="22" r="18" fill="none" stroke="#7f74e8"
                          stroke-width="4" stroke-linecap="round" stroke-dasharray="113.1"
                          stroke-dashoffset="39.6" transform="rotate(-90 22 22)"/>
                  <text id="exPercent" x="22" y="25.5" text-anchor="middle"
                        font-size="9.5" font-weight="700" fill="#4a5568">65%</text>
                </svg>
              </div>
              <div class="label">目标完成率</div>
            </div>
          </div>

          <!-- 本周统计：日期 + 图标，点击查看当天详情 -->
          <div class="week-panel" id="weekPanel"></div>

          <!-- 目标设置 -->
          <h3 class="sub-title">目标设置</h3>
          <div class="sport-inputs">
            <div class="field">
              <label for="goalKcal">每日热量目标（kcal）</label>
              <input id="goalKcal" type="number" min="50" max="3000" step="10" value="500">
            </div>
            <div class="field">
              <label for="goalSteps">每日步数目标</label>
              <input id="goalSteps" type="number" min="1000" max="50000" step="100" value="8000">
            </div>
            <div class="field">
              <label for="goalMinutes">每日运动时长（分钟）</label>
              <input id="goalMinutes" type="number" min="5" max="300" step="5" value="60">
            </div>
          </div>
          <div class="sport-actions">
            <button class="btn-soft" type="button" id="saveSportGoal">保存目标</button>
          </div>

          <!-- 每日心情 -->
          <div class="mood">
            <div class="mood-title">
              <svg class="icon"><use href="#i-smile"/></svg>每日心情
            </div>
            <div class="mood-picker" id="moodPicker">
              <button class="mood-opt" type="button" data-mood="开心">😄 开心</button>
              <button class="mood-opt" type="button" data-mood="平静">🙂 平静</button>
              <button class="mood-opt" type="button" data-mood="疲惫">😴 疲惫</button>
              <button class="mood-opt" type="button" data-mood="焦虑">😰 焦虑</button>
              <button class="mood-opt" type="button" data-mood="低落">😔 低落</button>
            </div>
            <textarea id="moodNote" placeholder="今天心情怎么样？发生了什么？记录一下吧..."></textarea>
            <div class="sport-actions">
              <button class="btn-soft" type="button" id="saveMood">保存今日心情</button>
            </div>
            <div class="mood-tip" id="moodTip">选择今天的心情后，这里会给出对应的小贴士。</div>
            <div class="mood-week" id="moodWeek"></div>
          </div>
        </div>

        <!-- 运动计划：目标与训练安排 -->
        <div class="card beauty-card">
          <div class="card-head">
            <div class="card-title">
              <svg class="icon"><use href="#i-spark"/></svg>运动计划
            </div>
            <span class="beauty-sub">目标 · 训练安排</span>
          </div>

          <div class="beauty-body">
            <!-- 目标设置 -->
            <div class="beauty-form">
              <div class="field">
                <label for="beautyType">计划类型</label>
                <select id="beautyType">
                  <option>健身减脂</option>
                  <option>增肌塑形</option>
                  <option>体态改善</option>
                  <option>提升体能</option>
                  <option>缓解压力</option>
                  <option>改善睡眠</option>
                  <option>经期舒缓</option>
                </select>
              </div>
              <div class="field-row">
                <div class="field">
                  <label for="beautyTarget">目标体重（kg）</label>
                  <input id="beautyTarget" type="number" step="0.1" value="58">
                </div>
                <div class="field">
                  <label for="beautyWeeks">目标周期（周）</label>
                  <input id="beautyWeeks" type="number" value="12" min="2" max="52">
                </div>
              </div>
              <div class="field">
                <label for="beautyTimes">每周运动次数</label>
                <select id="beautyTimes">
                  <option value="2">2 次</option>
                  <option value="3">3 次</option>
                  <option value="4" selected>4 次</option>
                  <option value="5">5 次</option>
                  <option value="6">6 次</option>
                  <option value="7">7 次</option>
                </select>
              </div>
              <button class="btn-primary" id="generatePlan" type="button">生成运动计划</button>
            </div>

            <!-- 计划结果 -->
            <div class="beauty-result">
              <div class="beauty-empty" id="beautyEmpty">
                设置目标体重与周期后，<br>这里会生成属于你的运动计划。
              </div>

              <div id="beautyResultBody" hidden>
                <div class="goal-stats">
                  <div class="goal-stat">
                    <div class="label">当前 → 目标</div>
                    <div class="value"><span id="beautyCurrent">65.2</span> → <span id="beautyTargetText">58.0</span><span class="unit">kg</span></div>
                  </div>
                  <div class="goal-stat">
                    <div class="label">每周变化</div>
                    <div class="value"><span id="beautyWeekly">0.6</span><span class="unit">kg/周</span></div>
                  </div>
                  <div class="goal-stat">
                    <div class="label">每日热量</div>
                    <div class="value"><span id="beautyDeficit">550</span><span class="unit">kcal/天</span></div>
                  </div>
                </div>

                <div class="progress-wrap">
                  <div class="progress-label"><span>目标进度</span><b id="beautyProgressText">0%</b></div>
                  <div class="progress-bar"><i id="beautyProgress"></i></div>
                </div>

                <!-- 体重变化曲线：每次记录体重后自动重绘 -->
                <div class="weight-chart" id="weightChart"></div>

                <div class="plan-summary" id="beautySummary"></div>
                <div class="plan-week" id="beautyWeek"></div>

                <!-- 按计划类型推荐的饮食种类 -->
                <div class="beauty-diet" id="beautyDietTip" hidden></div>

                <div class="weight-log">
                  <label for="beautyWeightNow">记录当前体重</label>
                  <input id="beautyWeightNow" type="number" step="0.1" placeholder="65.2">
                  <button class="btn-ghost-sm" type="button" id="logBeautyWeight">记录</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ====================================================
         页面四：家人健康
         ==================================================== -->
    <section class="page" id="page-family">
      <div class="family-wrap">

        <!-- 关怀提醒：提醒用户主动关照家人 -->
        <div class="reminder-card">
          <div class="female-head">
            <div class="female-title family-title">
              <svg class="icon"><use href="#i-bell"/></svg>关怀提醒
              <span class="reminder-count" id="reminderCount">0 条待办</span>
            </div>
            <button class="btn-soft" id="openReminder">添加提醒</button>
          </div>

          <!-- 常用提醒：点击后自动带入标题，直接选日期保存；支持自定义并长期保留 -->
          <div class="quick-reminders" id="quickReminderBox">
            <span>常用提醒</span>
          </div>

          <div class="reminder-list" id="reminderList"></div>
        </div>

        <!-- 家人档案：支持添加家人与健康记录 -->
        <div class="family-card">
          <div class="female-head">
            <div class="female-title family-title">
              <svg class="icon"><use href="#i-heart"/></svg>家人健康档案
            </div>
            <div class="head-actions">
              <button class="btn-soft btn-small" id="openFamilyRecord">添加记录</button>
              <button class="btn-soft btn-small" id="openMember">添加家人</button>
            </div>
          </div>

          <!-- 家人卡片由 JavaScript 根据数据动态生成，点击「最近记录」查看该家人全部记录 -->
          <div class="family-grid" id="familyGrid"></div>
        </div>

      </div>
    </section>

    <!-- ====================================================
         页面五：科普资讯
         ==================================================== -->
    <section class="page" id="page-news">
      <!-- 资讯搜索：按标题、摘要和正文关键词过滤 -->
      <div class="news-toolbar">
        <label class="news-search">
          <svg class="icon"><use href="#i-search"/></svg>
          <input id="newsSearch" type="search" placeholder="搜索科普内容，例如：睡眠、血压、拉伸、蛋白质">
        </label>
        <span class="news-count" id="newsCount"></span>
      </div>
      <div class="news-empty" id="newsEmpty" hidden>没有找到相关内容，换个关键词试试。</div>

      <div class="news-grid">
        <article class="news-card" data-article="diet">
          <div class="news-img green"><svg class="icon"><use href="#i-fork"/></svg></div>
          <div class="news-body">
            <div class="news-cat green">饮食营养</div>
            <div class="news-title">如何科学搭配三餐饮食？</div>
            <p class="news-desc">合理的饮食搭配不仅能提供充足的能量，还能帮助预防慢性疾病，让身体保持良好状态。</p>
            <span class="read-more">点击查看全文 ›</span>
          </div>
        </article>

        <article class="news-card" data-article="stretch">
          <div class="news-img blue"><svg class="icon"><use href="#i-dumbbell"/></svg></div>
          <div class="news-body">
            <div class="news-cat blue">运动指南</div>
            <div class="news-title">久坐族的5分钟拉伸指南</div>
            <p class="news-desc">长时间面对电脑工作，肩颈酸痛？这几个动作帮你缓解疲劳，恢复身体活力。</p>
            <span class="read-more">点击查看全文 ›</span>
          </div>
        </article>

        <article class="news-card" data-article="sleep">
          <div class="news-img purple"><svg class="icon"><use href="#i-moon"/></svg></div>
          <div class="news-body">
            <div class="news-cat purple">睡眠健康</div>
            <div class="news-title">为什么你总是睡不够？</div>
            <p class="news-desc">了解深度睡眠的重要性，以及如何通过改善卧室环境提升睡眠质量，找回好状态。</p>
            <span class="read-more">点击查看全文 ›</span>
          </div>
        </article>

        <article class="news-card" data-article="bp">
          <div class="news-img green"><svg class="icon"><use href="#i-heart"/></svg></div>
          <div class="news-body">
            <div class="news-cat green">慢病管理</div>
            <div class="news-title">血压血糖，家庭自测怎么做才准？</div>
            <p class="news-desc">测压姿势、测量时间、记录方式都会影响结果，掌握几个细节让数据更可信。</p>
            <span class="read-more">点击查看全文 ›</span>
          </div>
        </article>
      </div>
    </section>

  </div>
</main>
</div>
</div>

<!-- ========================================================
     个人信息档案弹窗
     ======================================================== -->
<div class="mask" id="profileMask">
  <div class="modal">
    <div class="modal-head">
      <svg class="icon"><use href="#i-user"/></svg>个人信息档案
      <button class="modal-close" id="profileClose" aria-label="关闭">
        <svg class="icon"><use href="#i-close"/></svg>
      </button>
    </div>

    <div class="modal-body">
      <div class="field">
        <label>头像</label>
        <div class="avatar-picker" id="avatarPicker"></div>
        <input type="file" id="avatarUploadInput" accept="image/*" hidden>
      </div>
      <div class="field">
        <label for="pNickname">昵称</label>
        <input id="pNickname" type="text" value="张三" placeholder="给自己取个昵称">
      </div>
      <div class="field">
        <label for="pName">姓名（选填）</label>
        <input id="pName" type="text" placeholder="可不填，仅用于档案归档">
      </div>
      <div class="field">
        <label for="pGender">性别</label>
        <select id="pGender">
          <option value="女" selected>女</option>
          <option value="男">男</option>
        </select>
      </div>
      <div class="field-row">
        <div class="field">
          <label for="pHeight">身高（cm）</label>
          <input id="pHeight" type="number" value="165">
        </div>
        <div class="field">
          <label for="pWeight">体重（kg）</label>
          <input id="pWeight" type="number" step="0.1" value="60.0">
        </div>
      </div>
    </div>

    <div class="modal-foot">
      <button class="btn-save" id="saveProfile">保存修改</button>
    </div>
  </div>
</div>

<!-- ========================================================
     头像裁剪弹窗：拖拽移动 + 滑块缩放
     ======================================================== -->
<div class="mask" id="cropMask">
  <div class="modal crop-modal">
    <div class="modal-head">
      <svg class="icon"><use href="#i-image"/></svg>裁剪头像
      <button class="modal-close" id="cropClose" aria-label="关闭">
        <svg class="icon"><use href="#i-close"/></svg>
      </button>
    </div>

    <div class="modal-body">
      <div class="crop-stage" id="cropStage">
        <img id="cropImage" alt="待裁剪头像">
        <div class="crop-overlay"></div>
      </div>
      <div class="crop-hint">拖动图片调整位置，滑动缩放，圆形区域为最终头像</div>
      <div class="crop-zoom">
        <span>缩放</span>
        <input type="range" id="cropZoom" min="100" max="300" value="100">
      </div>
    </div>

    <div class="modal-foot">
      <button class="btn-cancel" id="cropCancel">取消</button>
      <button class="btn-save" id="cropSave">使用这张头像</button>
    </div>
  </div>
</div>

<!-- ========================================================
     生理期记录弹窗：可选择开始/结束日期与周期长度
     ======================================================== -->
<div class="mask" id="periodMask">
  <div class="modal period-modal">
    <div class="modal-head">
      <svg class="icon"><use href="#i-calendar"/></svg>记录生理期
      <button class="modal-close" id="periodClose" aria-label="关闭">
        <svg class="icon"><use href="#i-close"/></svg>
      </button>
    </div>

    <div class="modal-body">
      <div class="period-tip">
        <svg class="icon"><use href="#i-droplet"/></svg>
        <span>记录本次经期的开始与结束日期，系统会自动计算经期长度与下次排卵日。</span>
      </div>

      <div class="period-dates">
        <div class="period-date-field">
          <label for="periodStart">开始日期</label>
          <input id="periodStart" type="date" value="2026-10-11">
        </div>
        <div class="period-arrow">
          <svg class="icon"><use href="#i-refresh"/></svg>
        </div>
        <div class="period-date-field">
          <label for="periodEnd">结束日期</label>
          <input id="periodEnd" type="date" value="2026-10-15">
        </div>
      </div>

      <div class="field">
        <label for="cycleDaysInput">周期长度</label>
        <select id="cycleDaysInput"></select>
      </div>

      <div class="period-preview">
        <div class="pp-item">
          <span>经期长度</span>
          <b id="periodPreviewDays">5 天</b>
        </div>
        <div class="pp-item">
          <span>排卵日预测</span>
          <b id="periodPreviewOvulation">10月25日</b>
        </div>
      </div>
    </div>

    <div class="modal-foot">
      <button class="btn-cancel" id="periodCancel">取消</button>
      <button class="btn-save" id="periodSave">保存记录</button>
    </div>
  </div>
</div>

<!-- ========================================================
     家人记录弹窗（男性视图）
     ======================================================== -->
<div class="mask" id="familyMask">
  <div class="modal">
    <div class="modal-head">
      <svg class="icon"><use href="#i-heart"/></svg>添加家人记录
      <button class="modal-close" id="familyClose" aria-label="关闭">
        <svg class="icon"><use href="#i-close"/></svg>
      </button>
    </div>

    <div class="modal-body">
      <div class="field-row">
        <div class="field">
          <label for="familyPerson">关怀对象</label>
          <select id="familyPerson">
            <option value="母亲">母亲</option>
            <option value="爱人">爱人</option>
          </select>
        </div>
        <div class="field">
          <label for="familyType">记录类型</label>
          <select id="familyType">
            <option value="体检">体检</option>
            <option value="用药">用药</option>
            <option value="生理期">生理期</option>
            <option value="其他">其他</option>
          </select>
        </div>
      </div>
      <div class="field">
        <label for="familyDate">日期</label>
        <input id="familyDate" type="date">
      </div>
      <div class="field">
        <label for="familyContent">记录内容</label>
        <input id="familyContent" type="text" placeholder="例如：血压 135/85，每日服用降压药">
      </div>
    </div>

    <div class="modal-foot">
      <button class="btn-cancel" id="familyCancel">取消</button>
      <button class="btn-save" id="familySave">保存记录</button>
    </div>
  </div>
</div>

<!-- ========================================================
     添加家人信息弹窗
     ======================================================== -->
<div class="mask" id="memberMask">
  <div class="modal">
    <div class="modal-head">
      <svg class="icon"><use href="#i-user"/></svg>添加家人信息
      <button class="modal-close" id="memberClose" aria-label="关闭">
        <svg class="icon"><use href="#i-close"/></svg>
      </button>
    </div>

    <div class="modal-body">
      <div class="field-row">
        <div class="field">
          <label for="memberRelation">称呼 / 关系</label>
          <input id="memberRelation" type="text" placeholder="如：母亲、父亲、爱人">
        </div>
        <div class="field">
          <label for="memberAge">年龄</label>
          <input id="memberAge" type="number" placeholder="如：58">
        </div>
      </div>
      <div class="field">
        <label for="memberName">姓名（选填）</label>
        <input id="memberName" type="text" placeholder="如：李秀兰">
      </div>
      <div class="field">
        <label for="memberConditions">基础病史</label>
        <input id="memberConditions" type="text" placeholder="如：高血压、糖尿病（没有可填“无”）">
      </div>
      <div class="field">
        <label for="memberMedications">常用药物</label>
        <input id="memberMedications" type="text" placeholder="如：降压药 每日 1 片">
      </div>
      <div class="field-row">
        <div class="field">
          <label for="memberEmergencyName">紧急联系人</label>
          <input id="memberEmergencyName" type="text" placeholder="如：王小明（儿子）">
        </div>
        <div class="field">
          <label for="memberEmergencyPhone">联系电话</label>
          <input id="memberEmergencyPhone" type="tel" placeholder="如：13800000000">
        </div>
      </div>
    </div>

    <div class="modal-foot">
      <button class="btn-cancel" id="memberCancel">取消</button>
      <button class="btn-save" id="memberSave">保存</button>
    </div>
  </div>
</div>

<!-- ========================================================
     添加关怀提醒弹窗
     ======================================================== -->
<div class="mask" id="reminderMask">
  <div class="modal">
    <div class="modal-head">
      <svg class="icon"><use href="#i-bell"/></svg>添加关怀提醒
      <button class="modal-close" id="reminderClose" aria-label="关闭">
        <svg class="icon"><use href="#i-close"/></svg>
      </button>
    </div>

    <div class="modal-body">
      <div class="field">
        <label for="reminderMember">提醒家人</label>
        <select id="reminderMember"></select>
      </div>
      <div class="field">
        <label for="reminderTitle">提醒内容</label>
        <input id="reminderTitle" type="text" placeholder="如：提醒母亲测量血压">
      </div>
      <div class="field">
        <label>提醒日期（可一次多选）</label>
        <div class="date-quick">
          <button class="quick-chip date-chip" type="button" data-day="0">今天</button>
          <button class="quick-chip date-chip" type="button" data-day="1">明天</button>
          <button class="quick-chip date-chip" type="button" data-day="3">3 天后</button>
          <button class="quick-chip date-chip" type="button" data-day="7">一周后</button>
          <button class="quick-chip date-chip" type="button" data-day="14">两周后</button>
        </div>
        <div class="date-add">
          <input id="reminderDate" type="date">
          <button class="btn-soft" type="button" id="reminderDateAdd">添加日期</button>
        </div>
        <div class="date-selected" id="reminderDateList"></div>
      </div>
    </div>

    <div class="modal-foot">
      <button class="btn-cancel" id="reminderCancel">取消</button>
      <button class="btn-save" id="reminderSave">保存</button>
    </div>
  </div>
</div>

<!-- ========================================================
     家人健康记录弹窗：点击家人卡片的「最近记录」查看
     ======================================================== -->
<div class="mask" id="memberRecordsMask">
  <div class="modal">
    <div class="modal-head">
      <svg class="icon"><use href="#i-heart"/></svg><span id="memberRecordsTitle">家人健康记录</span>
      <button class="modal-close" id="memberRecordsClose" aria-label="关闭">
        <svg class="icon"><use href="#i-close"/></svg>
      </button>
    </div>
    <div class="modal-body">
      <div id="memberDetailBody"></div>
    </div>
  </div>
</div>

<!-- ========================================================
     健康评分分析弹窗：点击顶部任一评分打开
     ======================================================== -->
<div class="mask" id="scoreMask">
  <div class="modal score-modal">
    <div class="modal-head">
      <svg class="icon"><use href="#i-spark"/></svg><span id="scoreModalTitle">健康评分分析</span>
      <button class="modal-close" id="scoreClose" aria-label="关闭">
        <svg class="icon"><use href="#i-close"/></svg>
      </button>
    </div>

    <div class="modal-body">
      <div class="score-hero">
        <b id="scoreModalValue">0</b><span>/100</span>
        <em id="scoreModalLevel">—</em>
      </div>
      <div class="score-body" id="scoreModalBody"></div>
      <p class="form-hint">分析基于你填写的饮食、运动、体重与心情数据自动生成，数据越完整结论越准确。</p>
    </div>
  </div>
</div>

<!-- ========================================================
     核心数据修改弹窗：输入新值并查看近一个月记录
     ======================================================== -->
<div class="mask" id="vitalMask">
  <div class="modal">
    <div class="modal-head">
      <svg class="icon"><use href="#i-heart"/></svg><span id="vitalTitle">修改核心数据</span>
      <button class="modal-close" id="vitalClose" aria-label="关闭">
        <svg class="icon"><use href="#i-close"/></svg>
      </button>
    </div>

    <div class="modal-body">
      <div id="vitalFields"></div>

      <h4 class="vital-history-title">近一个月记录</h4>
      <div class="vital-history" id="vitalHistory"></div>
    </div>

    <div class="modal-foot">
      <button class="btn-cancel" id="vitalCancel">取消</button>
      <button class="btn-save" id="vitalSave">保存</button>
    </div>
  </div>
</div>

<!-- ========================================================
     食物分量参考弹窗：输入食物后弹出，按份数换算营养
     ======================================================== -->
<div class="mask" id="foodMask">
  <div class="modal food-modal">
    <div class="modal-head">
      <svg class="icon"><use href="#i-fork"/></svg>食物分量参考
      <button class="modal-close" id="foodClose" aria-label="关闭">
        <svg class="icon"><use href="#i-close"/></svg>
      </button>
    </div>

    <div class="modal-body">
      <div class="food-summary" id="foodSummary"></div>

      <div class="food-portions" id="foodPortions"></div>

      <div class="field">
        <label for="foodCount">食用份数</label>
        <input id="foodCount" type="number" min="0.25" max="10" step="0.25" value="1">
      </div>
      <p class="form-hint">支持 0.25～10 份，例如半碗填 0.5，两杯填 2。</p>

      <div class="food-total" id="foodTotal"></div>
    </div>

    <div class="modal-foot">
      <button class="btn-cancel" id="foodCancel">取消</button>
      <button class="btn-save" id="foodSave">记录</button>
    </div>
  </div>
</div>

<!-- ========================================================
     运动类型选择弹窗
     ======================================================== -->
<div class="mask" id="sportMask">
  <div class="modal sport-modal">
    <div class="modal-head">
      <svg class="icon"><use href="#i-dumbbell"/></svg>选择运动类型
      <button class="modal-close" id="sportClose" aria-label="关闭">
        <svg class="icon"><use href="#i-close"/></svg>
      </button>
    </div>

    <div class="modal-body">
      <div class="sport-boards" id="sportBoards"></div>
      <div class="sport-board-head" id="sportBoardHead" hidden>
        <button class="btn-ghost-sm" type="button" id="sportBack">‹ 返回板块</button>
        <span id="sportBoardName"></span>
      </div>
      <div class="sport-grid" id="sportGrid" hidden></div>
    </div>

    <div class="modal-foot">
      <button class="btn-cancel" id="sportCancel">取消</button>
      <button class="btn-save" id="sportConfirm">开始运动</button>
    </div>
  </div>
</div>

<!-- ========================================================
     运动数据填写弹窗：点击运动数据卡片后打开
     ======================================================== -->
<div class="mask" id="sportDataMask">
  <div class="modal">
    <div class="modal-head">
      <svg class="icon"><use href="#i-activity"/></svg>填写今日运动数据
      <button class="modal-close" id="sdClose" aria-label="关闭">
        <svg class="icon"><use href="#i-close"/></svg>
      </button>
    </div>

    <div class="modal-body">
      <div class="field">
        <label for="sdKcal">已消耗热量（kcal）</label>
        <input id="sdKcal" type="number" min="0" max="5000" step="10">
      </div>
      <div class="field">
        <label for="sdSteps">今日步数</label>
        <input id="sdSteps" type="number" min="0" max="80000" step="100">
      </div>
      <div class="field">
        <label for="sdMinutes">活动时长（分钟）</label>
        <input id="sdMinutes" type="number" min="0" max="600" step="5">
      </div>
    </div>

    <div class="modal-foot">
      <button class="btn-cancel" id="sdCancel">取消</button>
      <button class="btn-save" id="sdSave">保存</button>
    </div>
  </div>
</div>

<!-- ========================================================
     科普资讯详情弹窗：点击资讯卡片后展示正文
     ======================================================== -->
<div class="mask" id="newsMask">
  <div class="modal news-detail">
    <div class="modal-head">
      <svg class="icon"><use href="#i-book"/></svg><span id="newsTitle">科普详情</span>
      <button class="modal-close" id="newsClose" aria-label="关闭">
        <svg class="icon"><use href="#i-close"/></svg>
      </button>
    </div>
    <div class="modal-body">
      <div class="news-article" id="newsBody"></div>
    </div>
  </div>
</div>

<!-- ========================================================
     悬浮客服按钮与 AI 聊天窗口
     ======================================================== -->
<button class="fab" id="fab" aria-label="打开 AI 健康小管家">
  <span class="ai-run">
    <img src="__AI_LOGO__" alt="AI 健康小管家">
    <span class="ai-tag">AI</span>
  </span>
  <span class="dot" id="fabDot"></span>
</button>

<div class="chat" id="chat">
  <div class="chat-head">
    <div class="ico"><img src="__AI_LOGO__" alt="AI 健康小管家"></div>
    <div>
      <div class="t">健康小管家 (AI)</div>
      <div class="s">随时随地问答健康问题</div>
    </div>
    <button class="chat-close" id="chatClose" aria-label="关闭聊天">
      <svg class="icon"><use href="#i-close"/></svg>
    </button>
  </div>

  <div class="chat-body" id="chatBody">
    <div class="msg bot">你好！我是你的专属 AI 健康助理。请问今天有什么我可以帮你的？关于饮食计算、运动建议或是生理期护理，都可以问我。</div>
  </div>

  <div class="chat-input">
    <input id="chatInput" type="text" placeholder="输入你想咨询的健康问题...">
    <button class="chat-send" id="chatSend" aria-label="发送">
      <svg class="icon"><use href="#i-send"/></svg>
    </button>
  </div>
</div>

<!-- 轻提示 -->
<div class="toast" id="toast"></div>

<script>
/* ==========================================================
   零、登录与首次健康信息填写
   ========================================================== */
const loginView = document.getElementById('loginView');
const onboardingView = document.getElementById('onboardingView');
const appShell = document.getElementById('appShell');

// 演示账号
const DEMO_ACCOUNT = 'AAA';
const DEMO_PASSWORD = '123456';

document.getElementById('loginForm').addEventListener('submit', function (event) {
  event.preventDefault();

  const account = document.getElementById('loginAccount').value.trim();
  const password = document.getElementById('loginPassword').value;
  const error = document.getElementById('loginError');

  if (account === DEMO_ACCOUNT && password === DEMO_PASSWORD) {
    error.hidden = true;
    loginView.hidden = true;
    onboardingView.hidden = false;
    window.scrollTo(0, 0);
    document.getElementById('obName').focus();
  } else {
    error.hidden = false;
    error.textContent = '账号或密码不正确，请使用演示账号 AAA / 123456';
  }
});

// 页面打开时聚焦账号输入框
window.addEventListener('load', function () {
  document.getElementById('loginAccount').focus();
});

// 标签式多选（健康状况、忌口）
document.querySelectorAll('.pref-chips').forEach(function (group) {
  group.addEventListener('click', function (event) {
    const chip = event.target.closest('.pref-chip');
    if (!chip) return;

    const noneChip = group.querySelector('.pref-chip[data-value="无"]');

    if (chip.dataset.value === '无') {
      group.querySelectorAll('.pref-chip').forEach(function (item) {
        item.classList.remove('selected');
      });
      chip.classList.add('selected');
      return;
    }

    if (noneChip) noneChip.classList.remove('selected');
    chip.classList.toggle('selected');

    // 一个都没选时，自动回到「无」
    if (!group.querySelector('.pref-chip.selected') && noneChip) {
      noneChip.classList.add('selected');
    }
  });
});

function getChipValues(groupId) {
  return Array.from(document.querySelectorAll('#' + groupId + ' .pref-chip.selected'))
    .map(function (chip) { return chip.dataset.value; })
    .filter(function (value) { return value !== '无'; });
}

// 手动录入自定义健康情况 / 忌口
document.querySelectorAll('.pref-custom-input').forEach(function (input) {
  input.addEventListener('keydown', function (event) {
    if (event.key !== 'Enter') return;
    event.preventDefault();

    const value = input.value.trim();
    if (!value) return;

    const group = document.getElementById(input.dataset.group);
    const exists = Array.from(group.querySelectorAll('.pref-chip')).some(function (chip) {
      return chip.dataset.value === value;
    });
    if (exists) {
      showToast('这个选项已经存在');
      input.value = '';
      return;
    }

    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'pref-chip selected';
    chip.dataset.value = value;
    chip.textContent = value;
    group.appendChild(chip);

    const noneChip = group.querySelector('.pref-chip[data-value="无"]');
    if (noneChip) noneChip.classList.remove('selected');

    input.value = '';
    showToast('已添加：' + value);
  });
});

function enterApp() {
  loginView.hidden = true;
  onboardingView.hidden = true;
  appShell.hidden = false;
  window.scrollTo(0, 0);
}

// 跳过填写，直接进入系统
document.getElementById('skipOnboarding').addEventListener('click', function () {
  enterApp();
});

// 保存基本信息、健康情况与饮食偏好
document.getElementById('onboardingForm').addEventListener('submit', function (event) {
  event.preventDefault();

  const name = document.getElementById('obName').value.trim() || '张三';
  const gender = document.getElementById('obGender').value;
  const height = parseFloat(document.getElementById('obHeight').value);
  const weight = parseFloat(document.getElementById('obWeight').value);
  const goal = document.getElementById('obGoal').value;
  const taste = document.getElementById('obTaste').value;
  const dietType = document.getElementById('obDietType').value;
  const restrictions = getChipValues('obRestrictions');

  // 同步到侧边栏
  document.getElementById('sideUserName').textContent = name;
  document.getElementById('sideUserSub').textContent =
    gender + ' · ' + (height > 0 ? height + 'cm' : '未填写身高');

  // 同步到个人信息弹窗（昵称用于展示，姓名选填）
  document.getElementById('pNickname').value = name;
  document.getElementById('pName').value = '';
  document.getElementById('pGender').value = gender;
  if (height > 0) document.getElementById('pHeight').value = height;
  if (weight > 0) document.getElementById('pWeight').value = weight.toFixed(1);

  // 保存档案，再次打开系统时沿用昵称、头像与基础信息
  saveData('profile', {
    nickname: name,
    name: '',
    avatar: currentAvatar,
    avatarImage: customAvatarImage,
    gender: gender,
    height: height > 0 ? height : 0,
    weight: weight > 0 ? weight : 0
  });

  // 同步到核心体征并重算 BMI
  if (weight > 0) {
    document.getElementById('weightValue').textContent = weight.toFixed(1);
  }
  if (height > 0 && weight > 0) {
    setBmiDisplay(weight / Math.pow(height / 100, 2));
  }

  // 性别联动女性健康档案
  currentGender = gender;
  applyGenderView();

  // 健康目标联动「科学变美」计划类型
  const beautyType = document.getElementById('beautyType');
  if (goal === '增肌紧致') {
    beautyType.value = '增肌塑形';
  } else if (goal === '改善体态') {
    beautyType.value = '体态改善';
  } else {
    beautyType.value = '健身减脂';
  }

  // 饮食偏好联动饮食建议
  document.getElementById('dietTipText').textContent =
    '根据你的' + taste + '口味与' + dietType + '偏好' +
    (restrictions.length ? '（忌口：' + restrictions.join('、') + '）' : '') +
    '，建议三餐规律、优先选择天然食材，并保证每日蛋白质摄入。';

  enterApp();
  renderVitalRanges();
  showToast('健康档案已保存');
});

/* ==========================================================
   一、顶部导航：切换六个页面
   ========================================================== */
const navButtons = Array.from(document.querySelectorAll('#nav button'));
const pages = Array.from(document.querySelectorAll('.page'));

function switchPage(name) {
  // 高亮当前导航
  navButtons.forEach(function (btn) {
    btn.classList.toggle('active', btn.dataset.page === name);
  });
  // 显示对应页面（其余隐藏）
  pages.forEach(function (page) {
    page.classList.toggle('active', page.id === 'page-' + name);
  });
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

navButtons.forEach(function (btn) {
  btn.addEventListener('click', function () {
    switchPage(btn.dataset.page);
  });
});

/* ==========================================================
   二、轻提示 Toast
   ========================================================== */
let toastTimer = null;

function showToast(message) {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(function () {
    toast.classList.remove('show');
  }, 2200);
}

// 所有带 data-toast 的按钮，点击后弹出对应提示
document.querySelectorAll('[data-toast]').forEach(function (el) {
  el.addEventListener('click', function () {
    showToast(el.dataset.toast);
  });
});

/* ==========================================================
   三、个人信息档案弹窗
   ========================================================== */
const profileMask = document.getElementById('profileMask');

/* ---------- 头像预设：用户可自由选择 ---------- */
const avatarPresets = [
  { emoji: '🌿', bg: 'linear-gradient(135deg, #8fd9b6, #4ecdc4)' },
  { emoji: '🌻', bg: 'linear-gradient(135deg, #ffd36e, #f5a623)' },
  { emoji: '🍑', bg: 'linear-gradient(135deg, #ffb3b3, #ff7a8a)' },
  { emoji: '🐱', bg: 'linear-gradient(135deg, #a8c8f0, #7aa6e8)' },
  { emoji: '🐼', bg: 'linear-gradient(135deg, #c9d6e3, #8fa6bd)' },
  { emoji: '🦊', bg: 'linear-gradient(135deg, #ffbe8a, #f08a4b)' },
  { emoji: '🐳', bg: 'linear-gradient(135deg, #8fd3f4, #5aa9e6)' },
  { emoji: '🌙', bg: 'linear-gradient(135deg, #b6a7f0, #8a6cf0)' },
  { emoji: '☀️', bg: 'linear-gradient(135deg, #ffe08a, #ffb74d)' },
  { emoji: '🍀', bg: 'linear-gradient(135deg, #9be89b, #5cc46a)' }
];

let currentAvatar = 0;
let customAvatarImage = null; // 用户上传并裁剪后的头像（dataURL）

function readProfile() {
  const saved = loadData('profile', null);
  return saved && typeof saved === 'object' ? saved : {};
}

// 侧边栏头像：优先显示用户上传的头像，否则使用预设表情
function renderSideAvatar() {
  const avatar = document.getElementById('sideAvatar');
  if (customAvatarImage) {
    avatar.innerHTML = '<img src="' + customAvatarImage + '" alt="我的头像">';
    avatar.style.background = '#f4f1ec';
    return;
  }
  const preset = avatarPresets[currentAvatar] || avatarPresets[0];
  avatar.textContent = preset.emoji;
  avatar.style.background = preset.bg;
}

function updateAvatarSelection() {
  document.querySelectorAll('.avatar-option').forEach(function (btn) {
    const isUpload = btn.classList.contains('avatar-upload');
    btn.classList.toggle('selected', isUpload
      ? !!customAvatarImage
      : !customAvatarImage && Number(btn.dataset.avatar) === currentAvatar);

    if (isUpload) {
      btn.innerHTML = customAvatarImage
        ? '<img src="' + customAvatarImage + '" alt="自定义头像">'
        : '＋';
    }
  });
}

// 选择预设头像：会清除已上传的自定义头像
function applyAvatar(index) {
  const safe = (index >= 0 && index < avatarPresets.length) ? index : 0;
  currentAvatar = safe;
  customAvatarImage = null;
  renderSideAvatar();
  updateAvatarSelection();
}

function renderAvatarPicker() {
  const picker = document.getElementById('avatarPicker');
  picker.innerHTML = '';
  avatarPresets.forEach(function (preset, index) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'avatar-option';
    btn.dataset.avatar = index;
    btn.style.background = preset.bg;
    btn.textContent = preset.emoji;
    btn.title = '头像 ' + (index + 1);
    btn.addEventListener('click', function () {
      applyAvatar(index);
    });
    picker.appendChild(btn);
  });

  // 最后一个：上传自定义头像
  const uploadBtn = document.createElement('button');
  uploadBtn.type = 'button';
  uploadBtn.className = 'avatar-option avatar-upload';
  uploadBtn.title = '上传头像';
  uploadBtn.addEventListener('click', function () {
    document.getElementById('avatarUploadInput').click();
  });
  picker.appendChild(uploadBtn);
}

// 页面加载：回显已保存的昵称、姓名、头像与体重
function loadProfileView() {
  const profile = readProfile();
  const nickname = profile.nickname || '张三';

  document.getElementById('sideUserName').textContent = nickname;
  if (profile.gender) {
    document.getElementById('sideUserSub').textContent =
      profile.gender + ' · ' + (profile.height ? profile.height + 'cm' : '未填写身高');
  }

  currentAvatar = typeof profile.avatar === 'number' ? profile.avatar : 0;
  customAvatarImage = profile.avatarImage || null;

  renderAvatarPicker();
  renderSideAvatar();
  updateAvatarSelection();

  // 恢复上次保存的身高体重与 BMI
  if (profile.weight > 0) {
    document.getElementById('weightValue').textContent = Number(profile.weight).toFixed(1);
    if (profile.height > 0) {
      setBmiDisplay(profile.weight / Math.pow(profile.height / 100, 2));
    }
  } else {
    // 没有档案时按页面初始体重与默认身高重算，避免 BMI 与体重不一致
    const shownWeight = parseFloat(document.getElementById('weightValue').textContent);
    if (shownWeight > 0) {
      setBmiDisplay(shownWeight / Math.pow(currentHeightCm() / 100, 2));
    }
  }
}

function openProfile() {
  const profile = readProfile();
  // 打开弹窗时回显当前资料
  document.getElementById('pNickname').value = profile.nickname || '张三';
  document.getElementById('pName').value = profile.name || '';
  document.getElementById('pGender').value = currentGender;
  if (profile.height) document.getElementById('pHeight').value = profile.height;
  if (profile.weight) document.getElementById('pWeight').value = profile.weight.toFixed(1);
  currentAvatar = typeof profile.avatar === 'number' ? profile.avatar : currentAvatar;
  customAvatarImage = profile.avatarImage || null;
  renderAvatarPicker();
  renderSideAvatar();
  updateAvatarSelection();
  profileMask.classList.add('open');
  document.body.style.overflow = 'hidden'; // 弹窗打开时禁止页面滚动
}

function closeProfile() {
  profileMask.classList.remove('open');
  if (!document.querySelector('.mask.open')) document.body.style.overflow = '';
}

document.getElementById('userBtn').addEventListener('click', openProfile);
document.getElementById('profileClose').addEventListener('click', closeProfile);

// 点击遮罩空白处也能关闭
profileMask.addEventListener('click', function (event) {
  if (event.target === profileMask) closeProfile();
});

// 保存档案：同步更新「健康数据」中的体重与 BMI
document.getElementById('saveProfile').addEventListener('click', function () {
  const nickname = document.getElementById('pNickname').value.trim() || '健康用户';
  const name = document.getElementById('pName').value.trim(); // 姓名选填，允许为空
  const gender = document.getElementById('pGender').value;
  const height = parseFloat(document.getElementById('pHeight').value);
  const weight = parseFloat(document.getElementById('pWeight').value);

  if (!height || !weight || height <= 0 || weight <= 0) {
    showToast('请填写正确身高和体重');
    return;
  }

  // 体重
  document.getElementById('weightValue').textContent = weight.toFixed(1);
  addWeightRecord(weight);

  // BMI = 体重(kg) / 身高(m) 的平方
  const bmi = weight / Math.pow(height / 100, 2);
  setBmiDisplay(bmi);

  // 昵称用于展示，姓名仅在填写后写入档案
  document.getElementById('userBtn').title = '个人信息 · ' + nickname + '（' + gender + '）';
  document.getElementById('sideUserName').textContent = nickname;
  document.getElementById('sideUserSub').textContent = gender + ' · ' + height + 'cm';

  // 头像、昵称、姓名等一并存入本地，刷新后仍然保留
  saveData('profile', {
    nickname: nickname,
    name: name,
    avatar: currentAvatar,
    avatarImage: customAvatarImage,
    gender: gender,
    height: height,
    weight: weight
  });

  // 根据性别显示/隐藏「健康数据」页中的女性健康档案
  currentGender = gender;
  applyGenderView();

  // 营养目标与体重相关，档案变化后重新计算
  refreshDietViews();

  // 身高或体重变化后同步正常值范围、异常提醒与 BMI 公式
  renderVitalRanges();

  closeProfile();
  showToast(name ? '个人信息已保存' : '个人信息已保存（姓名可稍后补充）');
});

/* ---------- 头像上传与裁剪 ---------- */
const cropMask = document.getElementById('cropMask');
const cropStage = document.getElementById('cropStage');
const cropImg = document.getElementById('cropImage');
const cropZoom = document.getElementById('cropZoom');
const CROP_SIZE = 240;

let cropSource = null;
let cropBaseScale = 1;
let cropScale = 1;
let cropOffsetX = 0;
let cropOffsetY = 0;
let cropDragging = false;
let cropPointerStart = { x: 0, y: 0, ox: 0, oy: 0 };

function cropDisplaySize() {
  return {
    w: cropSource.naturalWidth * cropBaseScale * cropScale,
    h: cropSource.naturalHeight * cropBaseScale * cropScale
  };
}

// 图片始终铺满裁剪框，并限制拖动范围，避免出现空白边缘
function layoutCropImage() {
  if (!cropSource) return;
  const size = cropDisplaySize();
  const maxX = Math.max(0, (size.w - CROP_SIZE) / 2);
  const maxY = Math.max(0, (size.h - CROP_SIZE) / 2);
  cropOffsetX = Math.min(maxX, Math.max(-maxX, cropOffsetX));
  cropOffsetY = Math.min(maxY, Math.max(-maxY, cropOffsetY));

  cropImg.style.width = size.w + 'px';
  cropImg.style.height = size.h + 'px';
  cropImg.style.marginLeft = cropOffsetX + 'px';
  cropImg.style.marginTop = cropOffsetY + 'px';
}

function closeCrop() {
  cropMask.classList.remove('open');
  if (!document.querySelector('.mask.open')) document.body.style.overflow = '';
}

document.getElementById('avatarUploadInput').addEventListener('change', function () {
  const file = this.files && this.files[0];
  this.value = ''; // 允许连续选择同一张图片
  if (!file) return;
  if (file.type.indexOf('image/') !== 0) {
    showToast('请选择图片文件');
    return;
  }

  const reader = new FileReader();
  reader.onload = function () {
    const image = new Image();
    image.onload = function () {
      cropSource = image;
      cropBaseScale = Math.max(CROP_SIZE / image.naturalWidth, CROP_SIZE / image.naturalHeight);
      cropScale = 1;
      cropZoom.value = 100;
      cropOffsetX = 0;
      cropOffsetY = 0;
      cropImg.src = image.src;
      layoutCropImage();
      cropMask.classList.add('open');
      document.body.style.overflow = 'hidden';
    };
    image.onerror = function () {
      showToast('图片加载失败，请换一张试试');
    };
    image.src = reader.result;
  };
  reader.onerror = function () {
    showToast('图片读取失败，请重试');
  };
  reader.readAsDataURL(file);
});

cropStage.addEventListener('pointerdown', function (event) {
  if (!cropSource) return;
  cropDragging = true;
  cropStage.classList.add('dragging');
  cropStage.setPointerCapture(event.pointerId);
  cropPointerStart = {
    x: event.clientX,
    y: event.clientY,
    ox: cropOffsetX,
    oy: cropOffsetY
  };
});

cropStage.addEventListener('pointermove', function (event) {
  if (!cropDragging) return;
  cropOffsetX = cropPointerStart.ox + (event.clientX - cropPointerStart.x);
  cropOffsetY = cropPointerStart.oy + (event.clientY - cropPointerStart.y);
  layoutCropImage();
});

function endCropDrag() {
  cropDragging = false;
  cropStage.classList.remove('dragging');
}

cropStage.addEventListener('pointerup', endCropDrag);
cropStage.addEventListener('pointercancel', endCropDrag);

cropZoom.addEventListener('input', function () {
  cropScale = Number(cropZoom.value) / 100;
  layoutCropImage();
});

document.getElementById('cropSave').addEventListener('click', function () {
  if (!cropSource) {
    closeCrop();
    return;
  }

  const display = cropDisplaySize();
  const left = CROP_SIZE / 2 + cropOffsetX - display.w / 2;
  const top = CROP_SIZE / 2 + cropOffsetY - display.h / 2;
  const ratio = cropSource.naturalWidth / display.w;

  const canvas = document.createElement('canvas');
  canvas.width = CROP_SIZE;
  canvas.height = CROP_SIZE;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, CROP_SIZE, CROP_SIZE);
  ctx.drawImage(
    cropSource,
    -left * ratio, -top * ratio, CROP_SIZE * ratio, CROP_SIZE * ratio,
    0, 0, CROP_SIZE, CROP_SIZE
  );

  customAvatarImage = canvas.toDataURL('image/jpeg', 0.88);
  renderSideAvatar();
  updateAvatarSelection();
  closeCrop();
  showToast('头像已更新，记得点击「保存修改」');
});

document.getElementById('cropClose').addEventListener('click', closeCrop);
document.getElementById('cropCancel').addEventListener('click', closeCrop);
cropMask.addEventListener('click', function (event) {
  if (event.target === cropMask) closeCrop();
});

/* ==========================================================
   四、饮食记录：输入框回车即可记录
   ========================================================== */
document.querySelectorAll('.meal input').forEach(function (input) {
  input.addEventListener('keydown', function (event) {
    if (event.key !== 'Enter' && event.keyCode !== 13) return;
    // 中文输入法选词时的回车不算提交，避免把未上屏的拼音当成食物
    if (event.isComposing || event.keyCode === 229) return;
    event.preventDefault();
    requestMealRecord(input.dataset.meal, input.value, input);
  });
});

// 点「记录」按钮同样可以提交，避免部分输入法 / 移动端回车无效
document.querySelectorAll('.meal-btn').forEach(function (btn) {
  btn.addEventListener('click', function () {
    const input = btn.parentElement.querySelector('input');
    if (!input) return;
    requestMealRecord(input.dataset.meal, input.value, input);
  });
});

/* ==========================================================
   四之二、图片上传
   说明：餐食图片仅做预览；体检报告为示例指标。
        接入豆包视觉模型 / OCR 后可替换为真实识别。
   ========================================================== */

// ---------- 餐食图片上传（当前仅预览，未接入视觉识别） ----------
const dietImageInput = document.getElementById('dietImageInput');
const dietPreview = document.getElementById('dietPreview');
const dietUploadEmpty = document.getElementById('dietUploadEmpty');
const dietPreviewImg = document.getElementById('dietPreviewImg');
const dietFileName = document.getElementById('dietFileName');
const dietStatus = document.getElementById('dietStatus');
const dietResult = document.getElementById('dietResult');
const dietFillMeal = document.getElementById('dietFillMeal');

let dietImageUrl = null;

function chooseDietImage() {
  dietImageInput.value = '';
  dietImageInput.click();
}

document.getElementById('dietChooseBtn').addEventListener('click', chooseDietImage);
document.getElementById('dietReselect').addEventListener('click', chooseDietImage);

// 点击空白上传区也能选择图片
dietUploadEmpty.addEventListener('click', function (event) {
  if (event.target.tagName !== 'BUTTON') chooseDietImage();
});

dietImageInput.addEventListener('change', function () {
  const file = dietImageInput.files[0];
  if (!file) return;

  if (!file.type || file.type.indexOf('image/') !== 0) {
    showToast('请选择图片文件');
    return;
  }

  // 预览图片
  if (dietImageUrl) URL.revokeObjectURL(dietImageUrl);
  dietImageUrl = URL.createObjectURL(file);
  dietPreviewImg.src = dietImageUrl;
  dietFileName.textContent = file.name;
  dietUploadEmpty.hidden = true;
  dietPreview.hidden = false;

  // 目前版本没有接入视觉识别模型：保留图片预览，但不编造识别结果
  dietStatus.className = 'upload-status';
  dietStatus.textContent = '图片已保存。当前版本未接入图像识别模型。';
  dietResult.innerHTML = '<div>请在下方「今日饮食记录」中按实际食物手动填写（例如：米饭 鸡胸肉 西兰花），' +
    '系统会按食物成分表估算热量与蛋白质等营养。配置豆包视觉模型后可自动识别。</div>';
  dietResult.hidden = false;
  dietFillMeal.hidden = true;
});

// 把识别结果填入午餐记录
dietFillMeal.addEventListener('click', function () {
  const lunchInput = document.querySelector('.meal input[data-meal="午餐"]');
  if (!lunchInput) return;
  lunchInput.value = dietFillMeal.dataset.foods || '';
  showToast('已将识别结果填入午餐记录');
});

// ---------- 体检报告图片识别 ----------
const reportImageInput = document.getElementById('reportImageInput');
const reportPreview = document.getElementById('reportPreview');
const reportUploadEmpty = document.getElementById('reportUploadEmpty');
const reportPreviewImg = document.getElementById('reportPreviewImg');
const reportFileName = document.getElementById('reportFileName');
const reportStatus = document.getElementById('reportStatus');
const reportResult = document.getElementById('reportResult');

let reportImageUrl = null;

function chooseReportImage() {
  reportImageInput.value = '';
  reportImageInput.click();
}

document.getElementById('reportChooseBtn').addEventListener('click', chooseReportImage);
document.getElementById('reportReselect').addEventListener('click', chooseReportImage);

reportUploadEmpty.addEventListener('click', function (event) {
  if (event.target.tagName !== 'BUTTON') chooseReportImage();
});

// 核心体征右上角的快捷入口
document.getElementById('quickReportUpload').addEventListener('click', function () {
  chooseReportImage();
  document.getElementById('reportCard').scrollIntoView({ behavior: 'smooth', block: 'center' });
});

reportImageInput.addEventListener('change', function () {
  const file = reportImageInput.files[0];
  if (!file) return;

  if (!file.type || file.type.indexOf('image/') !== 0) {
    showToast('请选择图片文件');
    return;
  }

  if (reportImageUrl) URL.revokeObjectURL(reportImageUrl);
  reportImageUrl = URL.createObjectURL(file);
  reportPreviewImg.src = reportImageUrl;
  reportFileName.textContent = file.name;
  reportUploadEmpty.hidden = true;
  reportPreview.hidden = false;

  reportStatus.className = 'upload-status scanning';
  reportStatus.textContent = 'AI 正在识别报告指标...';
  reportResult.hidden = true;

  setTimeout(function () {
    reportStatus.className = 'upload-status';
    reportStatus.textContent = '当前未接入 OCR，以下为示例指标，请按实际报告修改';
    reportResult.hidden = false;
    document.getElementById('reportDateText').textContent = formatYMD(new Date());
    showToast('已填入示例指标（未接入 OCR）');
  }, 1100);
});

// 将识别结果同步到核心体征
document.getElementById('applyReport').addEventListener('click', function () {
  document.getElementById('weightValue').textContent = '64.8';
  document.getElementById('fatValue').textContent = '24.0';
  document.getElementById('bpValue').textContent = '112/72';
  document.getElementById('glucoseValue').textContent = '5.0';

  // BMI 由体重和身高算出，不直接写入固定值
  setBmiDisplay(64.8 / Math.pow(currentHeightMeters(), 2));

  // 体检同步的体重也进入趋势记录
  addWeightRecord(64.8);
  saveData('bp', { systolic: 112, diastolic: 72 });
  saveData('glucose', 5.0);
  refreshDietViews();
  renderVitalRanges();

  showToast('体检指标已同步到核心体征');
});

/* ==========================================================
   五、运动页：目标与数据由用户填写，完成度自动计算
   ========================================================== */
const sportState = loadData('sport', {
  goal: { kcal: 500, steps: 8000, minutes: 60 },
  history: {}
});

// 运动记录只保留最近 7 天，避免旧数据长期堆积
function pruneSportHistory() {
  const cutoff = toISODate(addDays(new Date(), -6));
  Object.keys(sportState.history).forEach(function (date) {
    if (date < cutoff) delete sportState.history[date];
  });
}

pruneSportHistory();

// 小圆环半径 18，周长 = 2πr ≈ 113.1
const gaugeLength = 2 * Math.PI * 18;

// 今日实际数据：按日期存在 history 里，换天自动从 0 开始
function todaySport() {
  return sportState.history[toISODate(new Date())] || { kcal: 0, steps: 0, minutes: 0 };
}

// 本周合计：从本周一到今天
function weekSport() {
  const today = new Date();
  const monday = addDays(today, -((today.getDay() + 6) % 7));
  const startStr = toISODate(monday);
  const endStr = toISODate(today);
  const total = { kcal: 0, steps: 0, minutes: 0 };

  Object.keys(sportState.history).forEach(function (date) {
    if (date >= startStr && date <= endStr) {
      total.kcal += sportState.history[date].kcal || 0;
      total.steps += sportState.history[date].steps || 0;
      total.minutes += sportState.history[date].minutes || 0;
    }
  });
  return total;
}

// 完成率 = 热量 50% + 步数 30% + 时长 20%，三项分别封顶 100%
function sportPercent(actual, goal) {
  function ratio(value, target) {
    if (!target || target <= 0) return 0;
    return Math.min(1, (value || 0) / target);
  }
  return Math.round((ratio(actual.kcal, goal.kcal) * 0.5 +
    ratio(actual.steps, goal.steps) * 0.3 +
    ratio(actual.minutes, goal.minutes) * 0.2) * 100);
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString('zh-CN');
}

function renderExercise(key) {
  const isWeek = key === 'week';
  const data = isWeek ? weekSport() : todaySport();

  // 本周目标按已过天数折算，避免周初完成率永远很低
  const elapsed = isWeek ? ((new Date().getDay() + 6) % 7) + 1 : 1;
  const goal = {
    kcal: sportState.goal.kcal * elapsed,
    steps: sportState.goal.steps * elapsed,
    minutes: sportState.goal.minutes * elapsed
  };
  const percent = sportPercent(data, goal);

  document.getElementById('exKcal').textContent = formatNumber(data.kcal);
  document.getElementById('exSteps').textContent = formatNumber(data.steps);
  document.getElementById('exMinutes').textContent = formatNumber(data.minutes);
  document.getElementById('exPercent').textContent = percent + '%';

  const arc = document.getElementById('exGaugeArc');
  // 通过虚线偏移量控制圆弧长度
  arc.setAttribute('stroke-dashoffset', (gaugeLength * (1 - percent / 100)).toFixed(1));
}

// 把已保存的目标回填到输入框
function fillSportInputs() {
  document.getElementById('goalKcal').value = sportState.goal.kcal;
  document.getElementById('goalSteps').value = sportState.goal.steps;
  document.getElementById('goalMinutes').value = sportState.goal.minutes;
}

// 保存今日实际数据到对应日期，并刷新统计与评分
function saveTodaySport(data) {
  sportState.history[toISODate(new Date())] = data;
  pruneSportHistory();
  saveData('sport', sportState);

  const activeTab = document.querySelector('#sportTabs button.active');
  renderExercise(activeTab ? activeTab.dataset.tab : 'today');
  refreshDietViews();
}

document.getElementById('saveSportGoal').addEventListener('click', function () {
  const goal = {
    kcal: parseInt(document.getElementById('goalKcal').value, 10),
    steps: parseInt(document.getElementById('goalSteps').value, 10),
    minutes: parseInt(document.getElementById('goalMinutes').value, 10)
  };

  if (!goal.kcal || !goal.steps || !goal.minutes ||
      goal.kcal <= 0 || goal.steps <= 0 || goal.minutes <= 0) {
    showToast('目标值需要大于 0');
    return;
  }

  sportState.goal = goal;
  saveData('sport', sportState);
  renderExercise('today');
  updateScores();
  showToast('运动目标已保存');
});

// ---------- 点击数据卡片填写今日数据 ----------
const sportDataMask = document.getElementById('sportDataMask');

document.querySelectorAll('.ex-stat[data-field]').forEach(function (card) {
  card.addEventListener('click', function () {
    const today = todaySport();
    document.getElementById('sdKcal').value = today.kcal;
    document.getElementById('sdSteps').value = today.steps;
    document.getElementById('sdMinutes').value = today.minutes;
    openMask(sportDataMask);
  });
});

document.getElementById('sdClose').addEventListener('click', function () {
  closeMask(sportDataMask);
});

document.getElementById('sdCancel').addEventListener('click', function () {
  closeMask(sportDataMask);
});

sportDataMask.addEventListener('click', function (event) {
  if (event.target === sportDataMask) closeMask(sportDataMask);
});

document.getElementById('sdSave').addEventListener('click', function () {
  const data = {
    kcal: parseInt(document.getElementById('sdKcal').value, 10) || 0,
    steps: parseInt(document.getElementById('sdSteps').value, 10) || 0,
    minutes: parseInt(document.getElementById('sdMinutes').value, 10) || 0
  };

  if (data.kcal < 0 || data.steps < 0 || data.minutes < 0) {
    showToast('数据不能为负数');
    return;
  }

  saveTodaySport(data);
  closeMask(sportDataMask);
  showToast('今日运动数据已更新');
});

// ---------- 运动计时：开始后自动累计时长与热量 ----------
let sportStartTime = null;
let sportTimerId = null;

// 热量 = MET × 体重(kg) × 小时数（国际通用的 MET 估算公式）
function estimateSportKcal(name, minutes) {
  const sport = sportTypes.filter(function (item) {
    return item.name === name;
  })[0];
  const met = sport ? sport.met : 4;
  return Math.round(met * getCurrentWeight() * (minutes / 60));
}

function updateSportTimer() {
  if (!sportStartTime) return;
  const seconds = Math.floor((Date.now() - sportStartTime) / 1000);
  const minutes = String(Math.floor(seconds / 60)).padStart(2, '0');
  const rest = String(seconds % 60).padStart(2, '0');
  document.getElementById('sportTimer').textContent = minutes + ':' + rest;
}

function startSportSession(name) {
  selectedSport = name;
  document.getElementById('activeSportName').textContent = name;
  document.getElementById('activeSport').hidden = false;
  sportStartTime = Date.now();
  updateSportTimer();
  clearInterval(sportTimerId);
  sportTimerId = setInterval(updateSportTimer, 1000);
  showToast('已开始运动：' + name + '，结束后自动统计时长与热量');
}

function stopSportSession() {
  if (!sportStartTime) return;

  const name = document.getElementById('activeSportName').textContent;
  const minutes = Math.max(1, Math.round((Date.now() - sportStartTime) / 60000));
  const kcal = estimateSportKcal(name, minutes);
  const today = todaySport();

  clearInterval(sportTimerId);
  sportTimerId = null;
  sportStartTime = null;
  document.getElementById('activeSport').hidden = true;
  document.getElementById('sportTimer').textContent = '00:00';

  saveTodaySport({
    kcal: today.kcal + kcal,
    steps: today.steps,
    minutes: today.minutes + minutes
  });

  showToast('已结束' + name + '：' + minutes + ' 分钟，约消耗 ' + kcal +
    ' kcal。可点击上方卡片按手环数据修正。');
}

// 点击运动分类直接开始；「球类」先让用户选择具体项目
document.querySelectorAll('.sport-pill').forEach(function (pill) {
  pill.addEventListener('click', function () {
    const name = pill.dataset.sport || pill.textContent.trim();

    if (name === '球类运动') {
      selectedSport = '';
      resetSportModal();
      renderSportBoards();
      renderSportBoard('球类运动');
      openMask(sportMask);
      return;
    }

    startSportSession(name);
  });
});

// ---------- 本周统计：日期 + 图标，点击查看当天详情 ----------
function renderWeekPanel() {
  const panel = document.getElementById('weekPanel');
  if (!panel) return;

  const today = new Date();
  const monday = addDays(today, -((today.getDay() + 6) % 7));
  const days = [];

  for (let index = 0; index < 7; index++) {
    const day = addDays(monday, index);
    const key = toISODate(day);
    const data = sportState.history[key] || { kcal: 0, steps: 0, minutes: 0 };
    days.push({ date: day, key: key, data: data });
  }

  const maxKcal = Math.max.apply(null, days.map(function (item) {
    return item.data.kcal || 0;
  }).concat([1]));

  panel.innerHTML = '<div class="week-grid" id="weekGrid"></div><div class="week-detail" id="weekDetail">点击上方任意日期，查看当天的运动记录。</div>';
  const grid = document.getElementById('weekGrid');

  days.forEach(function (item) {
    const tile = document.createElement('div');
    tile.className = 'week-day' + (item.data.kcal || item.data.steps ? '' : ' empty');
    const icon = item.data.kcal >= maxKcal * 0.6 && item.data.kcal > 0 ? 'i-flame' : 'i-activity';

    tile.innerHTML = '<div class="date">' + (item.date.getMonth() + 1) + '/' + item.date.getDate() + '</div>' +
      '<svg class="icon"><use href="#' + icon + '"></use></svg>' +
      '<div class="kcal">' + (item.data.kcal ? Math.round(item.data.kcal) + ' kcal' : '无记录') + '</div>';

    tile.addEventListener('click', function () {
      grid.querySelectorAll('.week-day').forEach(function (node) {
        node.classList.remove('selected');
      });
      tile.classList.add('selected');
      document.getElementById('weekDetail').innerHTML =
        '<b>' + (item.date.getMonth() + 1) + ' 月 ' + item.date.getDate() + ' 日</b><br>' +
        '消耗：' + Math.round(item.data.kcal || 0) + ' kcal　步数：' + formatNumber(item.data.steps || 0) +
        '　时长：' + Math.round(item.data.minutes || 0) + ' 分钟';
    });

    grid.appendChild(tile);
  });
}

document.querySelectorAll('#sportTabs button').forEach(function (btn) {
  btn.addEventListener('click', function () {
    document.querySelectorAll('#sportTabs button').forEach(function (b) {
      b.classList.toggle('active', b === btn);
    });

    const isWeek = btn.dataset.tab === 'week';
    document.getElementById('todayStats').hidden = isWeek;
    document.getElementById('weekPanel').classList.toggle('active', isWeek);
    renderExercise(btn.dataset.tab);
  });
});

// ---------- 运动类型：先选大类板块，再选具体项目 ----------
const sportBoards = [
  { name: '户外运动', desc: '健走、快走、慢跑、骑行、徒步、登山、游泳、轮滑' },
  { name: '球类运动', desc: '乒乓球、羽毛球、篮球、足球、网球、排球、台球' },
  { name: '形体运动', desc: '瑜伽、普拉提、健身操、力量训练、太极、舞蹈' },
  { name: '碎片化运动', desc: '爬楼梯、跳绳、开合跳、深蹲、平板支撑、工间操' }
];

const sportTypes = [
  { name: '健走', board: '户外运动', cal: '约 280 kcal/小时', color: '#6b8f3f', icon: 'i-footprints', met: 4.3 },
  { name: '快走', board: '户外运动', cal: '约 260 kcal/小时', color: '#7a9b5c', icon: 'i-footprints', met: 4.0 },
  { name: '慢跑', board: '户外运动', cal: '约 455 kcal/小时', color: '#c08a5a', icon: 'i-run', met: 7.0 },
  { name: '户外骑行', board: '户外运动', cal: '约 350 kcal/小时', color: '#5f8fae', icon: 'i-bike', met: 6.8 },
  { name: '徒步', board: '户外运动', cal: '约 320 kcal/小时', color: '#4f7898', icon: 'i-mountain', met: 6.0 },
  { name: '跑步', board: '户外运动', cal: '约 450 kcal/小时', color: '#b06a3a', icon: 'i-run', met: 8.3 },
  { name: '登山', board: '户外运动', cal: '约 420 kcal/小时', color: '#6e3a18', icon: 'i-mountain', met: 7.5 },
  { name: '游泳', board: '户外运动', cal: '约 500 kcal/小时', color: '#4f7898', icon: 'i-swim', met: 7.0 },
  { name: '轮滑 / 滑板', board: '户外运动', cal: '约 455 kcal/小时', color: '#8b7d70', icon: 'i-activity', met: 7.0 },
  { name: '飞盘', board: '户外运动', cal: '约 260 kcal/小时', color: '#6b8f3f', icon: 'i-activity', met: 4.0 },
  { name: '乒乓球', board: '球类运动', cal: '约 360 kcal/小时', color: '#8b4a22', icon: 'i-ball', met: 4.0 },
  { name: '羽毛球', board: '球类运动', cal: '约 420 kcal/小时', color: '#a9653a', icon: 'i-ball', met: 5.5 },
  { name: '篮球', board: '球类运动', cal: '约 470 kcal/小时', color: '#b06a3a', icon: 'i-ball', met: 6.5 },
  { name: '足球', board: '球类运动', cal: '约 500 kcal/小时', color: '#6b8f3f', icon: 'i-ball', met: 7.0 },
  { name: '网球', board: '球类运动', cal: '约 440 kcal/小时', color: '#7a9b5c', icon: 'i-ball', met: 6.0 },
  { name: '排球', board: '球类运动', cal: '约 260 kcal/小时', color: '#5f8fae', icon: 'i-ball', met: 4.0 },
  { name: '匹克球', board: '球类运动', cal: '约 295 kcal/小时', color: '#9c7a4f', icon: 'i-ball', met: 4.5 },
  { name: '台球', board: '球类运动', cal: '约 165 kcal/小时', color: '#8b7d70', icon: 'i-ball', met: 2.5 },
  { name: '瑜伽', board: '形体运动', cal: '约 180 kcal/小时', color: '#9c7a4f', icon: 'i-yoga', met: 3.0 },
  { name: '普拉提', board: '形体运动', cal: '约 200 kcal/小时', color: '#9c7a4f', icon: 'i-yoga', met: 3.0 },
  { name: '健身操', board: '形体运动', cal: '约 300 kcal/小时', color: '#c08a5a', icon: 'i-dumbbell', met: 5.0 },
  { name: '力量训练', board: '形体运动', cal: '约 330 kcal/小时', color: '#8b4a22', icon: 'i-dumbbell', met: 5.0 },
  { name: '拉伸放松', board: '形体运动', cal: '约 120 kcal/小时', color: '#8b7d70', icon: 'i-activity', met: 2.3 },
  { name: '太极', board: '形体运动', cal: '约 195 kcal/小时', color: '#6b8f3f', icon: 'i-yoga', met: 3.0 },
  { name: '八段锦', board: '形体运动', cal: '约 165 kcal/小时', color: '#7a9b5c', icon: 'i-yoga', met: 2.5 },
  { name: '舞蹈', board: '形体运动', cal: '约 325 kcal/小时', color: '#c08a5a', icon: 'i-activity', met: 5.0 },
  { name: '爬楼梯', board: '碎片化运动', cal: '约 500 kcal/小时', color: '#6e3a18', icon: 'i-mountain', met: 8.8 },
  { name: '快走 10 分钟', board: '碎片化运动', cal: '约 280 kcal/小时', color: '#6b8f3f', icon: 'i-footprints', met: 4.3 },
  { name: '跳绳', board: '碎片化运动', cal: '约 600 kcal/小时', color: '#a9653a', icon: 'i-activity', met: 10.0 },
  { name: '开合跳', board: '碎片化运动', cal: '约 480 kcal/小时', color: '#b06a3a', icon: 'i-activity', met: 8.0 },
  { name: '深蹲', board: '碎片化运动', cal: '约 325 kcal/小时', color: '#8b4a22', icon: 'i-dumbbell', met: 5.0 },
  { name: '平板支撑', board: '碎片化运动', cal: '约 245 kcal/小时', color: '#9c7a4f', icon: 'i-activity', met: 3.8 },
  { name: '原地高抬腿', board: '碎片化运动', cal: '约 520 kcal/小时', color: '#b06a3a', icon: 'i-run', met: 8.0 },
  { name: '靠墙静蹲', board: '碎片化运动', cal: '约 195 kcal/小时', color: '#7a9b5c', icon: 'i-dumbbell', met: 3.0 },
  { name: '工间操', board: '碎片化运动', cal: '约 210 kcal/小时', color: '#8b7d70', icon: 'i-activity', met: 3.5 }
];

const sportMask = document.getElementById('sportMask');
let selectedSport = '';

// 第一层：四个运动板块
function renderSportBoards() {
  const box = document.getElementById('sportBoards');
  box.innerHTML = '';

  sportBoards.forEach(function (board) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'sport-board';
    btn.innerHTML = '<b>' + board.name + '</b><span>' + board.desc + '</span>';
    btn.addEventListener('click', function () {
      renderSportBoard(board.name);
    });
    box.appendChild(btn);
  });
}

function resetSportModal() {
  document.getElementById('sportBoards').hidden = false;
  document.getElementById('sportBoardHead').hidden = true;

  const grid = document.getElementById('sportGrid');
  grid.hidden = true;
  grid.innerHTML = '';
}

// 第二层：某个板块下的具体项目
function renderSportBoard(board) {
  document.getElementById('sportBoards').hidden = true;
  document.getElementById('sportBoardHead').hidden = false;
  document.getElementById('sportBoardName').textContent = board;

  const grid = document.getElementById('sportGrid');
  grid.hidden = false;
  grid.innerHTML = '';

  sportTypes.filter(function (sport) {
    return sport.board === board;
  }).forEach(function (sport) {
    const option = document.createElement('button');
    option.type = 'button';
    option.className = 'sport-option' + (selectedSport === sport.name ? ' selected' : '');

    const avatar = document.createElement('span');
    avatar.className = 'sport-avatar';
    avatar.style.background = sport.color;
    avatar.innerHTML = '<svg class="icon"><use href="#' + sport.icon + '"></use></svg>';

    const info = document.createElement('span');
    const name = document.createElement('span');
    name.className = 'sport-name';
    name.textContent = sport.name;
    const cal = document.createElement('span');
    cal.className = 'sport-cal';
    cal.textContent = sport.cal;
    info.appendChild(name);
    info.appendChild(cal);

    option.appendChild(avatar);
    option.appendChild(info);

    option.addEventListener('click', function () {
      selectedSport = sport.name;
      grid.querySelectorAll('.sport-option').forEach(function (item) {
        item.classList.remove('selected');
      });
      option.classList.add('selected');
    });

    grid.appendChild(option);
  });
}

document.getElementById('sportBack').addEventListener('click', function () {
  selectedSport = '';
  resetSportModal();
  renderSportBoards();
});

document.getElementById('startSport').addEventListener('click', function () {
  selectedSport = '';
  resetSportModal();
  renderSportBoards();
  openMask(sportMask);
});

document.getElementById('sportClose').addEventListener('click', function () {
  closeMask(sportMask);
});

document.getElementById('sportCancel').addEventListener('click', function () {
  closeMask(sportMask);
});

sportMask.addEventListener('click', function (event) {
  if (event.target === sportMask) closeMask(sportMask);
});

document.getElementById('sportConfirm').addEventListener('click', function () {
  if (!selectedSport) {
    showToast('请先选择一种运动类型');
    return;
  }

  closeMask(sportMask);
  startSportSession(selectedSport);
});

document.getElementById('stopSport').addEventListener('click', function () {
  stopSportSession();
});

// ---------- 科学变美：目标与计划 ----------
const beautyState = {
  type: '',
  startWeight: 0,
  currentWeight: 0,
  targetWeight: 0,
  weeks: 0,
  times: 0
};

const beautyDays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];

// 每周运动次数对应的训练日
const beautyDayIndexes = {
  2: [0, 3],
  3: [0, 2, 4],
  4: [0, 2, 4, 6],
  5: [0, 1, 3, 5, 6],
  6: [0, 1, 2, 4, 5, 6],
  7: [0, 1, 2, 3, 4, 5, 6]
};

const beautyActivityPools = {
  '健身减脂': ['健走 40 分钟 + 拉伸', '力量训练 30 分钟', '户外骑行 45 分钟', '跳绳 20 分钟', '瑜伽拉伸 30 分钟'],
  '增肌塑形': ['上肢力量训练 30 分钟', '下肢力量训练 30 分钟', '核心训练 25 分钟', '游泳 30 分钟', '蛋白质补充 + 拉伸'],
  '体态改善': ['肩颈拉伸 15 分钟', '核心稳定训练 25 分钟', '瑜伽 30 分钟', '靠墙站立 10 分钟', '散步 30 分钟'],
  '提升体能': ['间歇跑 20 分钟', '跳绳 15 分钟', '核心训练 25 分钟', '游泳 30 分钟', '爬楼梯 10 分钟'],
  '缓解压力': ['瑜伽 30 分钟', '户外散步 30 分钟', '拉伸放松 20 分钟', '呼吸训练 10 分钟', '慢跑 20 分钟'],
  '改善睡眠': ['睡前拉伸 15 分钟', '晚饭后散步 30 分钟', '瑜伽 20 分钟', '呼吸训练 10 分钟', '轻力量训练 20 分钟'],
  '经期舒缓': ['经期拉伸 15 分钟', '散步 20 分钟', '猫式伸展 10 分钟', '腹式呼吸 10 分钟', '热敷放松 15 分钟']
};

function updateBeautyProgress() {
  let percent = 0;

  if (beautyState.type === '健身减脂' && beautyState.startWeight > beautyState.targetWeight) {
    percent = (beautyState.startWeight - beautyState.currentWeight) /
      (beautyState.startWeight - beautyState.targetWeight) * 100;
  } else if (beautyState.type === '增肌塑形' && beautyState.targetWeight > beautyState.startWeight) {
    percent = (beautyState.currentWeight - beautyState.startWeight) /
      (beautyState.targetWeight - beautyState.startWeight) * 100;
  }

  percent = Math.max(0, Math.min(100, percent));
  document.getElementById('beautyProgress').style.width = percent.toFixed(0) + '%';

  const isWeightType = beautyState.type === '健身减脂' || beautyState.type === '增肌塑形';
  document.getElementById('beautyProgressText').textContent =
    isWeightType ? Math.round(percent) + '%' : '进行中';
}

document.getElementById('generatePlan').addEventListener('click', function () {
  const type = document.getElementById('beautyType').value;
  const target = parseFloat(document.getElementById('beautyTarget').value);
  const weeks = parseInt(document.getElementById('beautyWeeks').value, 10);
  const times = parseInt(document.getElementById('beautyTimes').value, 10);
  const current = parseFloat(document.getElementById('weightValue').textContent) || 60.0;

  if (!target || target < 20 || target > 200) {
    showToast('请输入 20-200 kg 的目标体重');
    return;
  }
  if (!weeks || weeks < 2 || weeks > 52) {
    showToast('目标周期请设置在 2-52 周');
    return;
  }
  if (!times || times < 2 || times > 7) {
    showToast('每周运动次数请设置在 2-7 次');
    return;
  }
  if (type === '健身减脂' && target >= current) {
    showToast('减脂目标体重应低于当前体重');
    return;
  }
  if (type === '增肌塑形' && target <= current) {
    showToast('增肌目标体重应高于当前体重');
    return;
  }

  beautyState.type = type;
  beautyState.startWeight = current;
  beautyState.currentWeight = current;
  beautyState.targetWeight = target;
  beautyState.weeks = weeks;
  beautyState.times = times;

  const weeklyChange = Math.abs(current - target) / weeks;
  const dailyCalories = Math.round(weeklyChange * 7700 / 7);
  const isWeightType = type === '健身减脂' || type === '增肌塑形';

  document.getElementById('beautyCurrent').textContent = current.toFixed(1);
  document.getElementById('beautyTargetText').textContent = target.toFixed(1);
  document.getElementById('beautyWeekly').textContent = isWeightType ? weeklyChange.toFixed(1) : '—';
  document.getElementById('beautyDeficit').textContent = isWeightType
    ? (type === '健身减脂' ? '-' : '+') + dailyCalories
    : '—';

  let summary = '';
  if (type === '健身减脂') {
    summary = '按每周约 ' + weeklyChange.toFixed(1) + ' kg 的节奏，预计 ' + weeks +
      ' 周达到目标体重。建议每周运动 ' + times +
      ' 次，有氧与力量结合，每日保持约 ' + dailyCalories + ' kcal 的热量缺口，并保证蛋白质摄入。';
    if (weeklyChange > 1) {
      summary += ' 当前目标略激进，建议把周期适当拉长，避免过度节食。';
    }
  } else if (type === '增肌塑形') {
    summary = '按每周约 ' + weeklyChange.toFixed(1) + ' kg 的节奏，预计 ' + weeks +
      ' 周达到目标。建议每周运动 ' + times +
      ' 次，以力量训练为主，每日增加约 ' + dailyCalories + ' kcal 的热量与充足蛋白质。';
    if (weeklyChange > 1) {
      summary += ' 体重增长过快容易增加脂肪，建议适当放缓。';
    }
  } else if (type === '体态改善') {
    summary = '以体态改善为主，建议每周训练 ' + times +
      ' 次，重点加强核心、肩背与拉伸放松；体重目标仅作为参考，不必过度追求数字。';
  } else {
    const extra = {
      '提升体能': '训练量循序渐进，每周比上周多 10% 左右，注意热身后再提高强度。',
      '缓解压力': '以呼吸训练、瑜伽和户外散步为主，帮助降低焦虑水平。',
      '改善睡眠': '训练尽量安排在睡前 2 小时以前，配合固定作息效果更好。',
      '经期舒缓': '经期以舒缓动作为主，避免跳跃与高强度训练，注意腹部保暖。'
    }[type] || '注意热身与拉伸，循序渐进。';
    summary = '本次以「' + type + '」为目标，建议每周训练 ' + times + ' 次。' + extra;
  }
  document.getElementById('beautySummary').textContent = summary;

  // 生成一周计划
  const activeDays = beautyDayIndexes[times] || [0, 2, 4, 6];
  const pool = beautyActivityPools[type] || beautyActivityPools['健身减脂'];
  const weekEl = document.getElementById('beautyWeek');
  weekEl.innerHTML = '';

  beautyDays.forEach(function (day, index) {
    const slot = activeDays.indexOf(index);
    const row = document.createElement('div');
    row.className = 'plan-day';

    // 每天计划前的勾选框：完成后划线标记
    const check = document.createElement('button');
    check.type = 'button';
    check.className = 'plan-check';
    check.textContent = '✓';
    check.title = '标记今天是否完成';
    check.addEventListener('click', function () {
      row.classList.toggle('done');
    });

    const dayEl = document.createElement('span');
    dayEl.textContent = day;

    const activityEl = document.createElement('span');
    activityEl.textContent = slot === -1 ? '休息 / 轻松散步' : pool[slot % pool.length];

    row.appendChild(check);
    row.appendChild(dayEl);
    row.appendChild(activityEl);
    weekEl.appendChild(row);
  });

  document.getElementById('beautyEmpty').hidden = true;
  document.getElementById('beautyResultBody').hidden = false;
  document.getElementById('beautyWeightNow').value = '';

  // 生成计划后同步推荐饮食种类与体重曲线
  renderBeautyDietTip(type);
  renderWeightChart();

  updateBeautyProgress();
  showToast('已生成' + type + '计划');
});

// 记录当前体重并更新目标进度
document.getElementById('logBeautyWeight').addEventListener('click', function () {
  const value = parseFloat(document.getElementById('beautyWeightNow').value);

  if (!beautyState.startWeight) {
    showToast('请先生成运动计划');
    return;
  }
  if (!value || value < 20 || value > 200) {
    showToast('请输入正确的体重');
    return;
  }

  beautyState.currentWeight = value;
  document.getElementById('beautyCurrent').textContent = value.toFixed(1);
  addWeightRecord(value);
  updateBeautyProgress();
  showToast('已记录当前体重：' + value.toFixed(1) + ' kg');
});

/* ==========================================================
   六、健康档案：性别视图、周期设置、状态标签与家人记录
   ========================================================== */

// ---------- 日期工具 ----------
const MS_PER_DAY = 24 * 60 * 60 * 1000;

function addDays(date, days) {
  const result = new Date(date.getTime());
  result.setDate(result.getDate() + days);
  return result;
}

function parseISODate(value) {
  if (!value) return null;
  const parts = value.split('-');
  if (parts.length !== 3) return null;
  const date = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
  return isNaN(date.getTime()) ? null : date;
}

function toISODate(date) {
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return date.getFullYear() + '-' + month + '-' + day;
}

function formatMD(date) {
  return (date.getMonth() + 1) + '月' + date.getDate() + '日';
}

function formatYMD(date) {
  return date.getFullYear() + '年' + (date.getMonth() + 1) + '月' + date.getDate() + '日';
}

// ---------- 根据性别切换视图 ----------
let currentGender = '女';

function applyGenderView() {
  const isFemale = currentGender === '女';

  // 女性健康档案已并入「健康数据」页，仅女性用户显示
  document.getElementById('femaleHealthSection').hidden = !isFemale;
  document.getElementById('pGender').value = currentGender;
}

// ---------- 生理周期：长度与日期都可自由选择 ----------
let lastPeriodStart = new Date(2026, 9, 11); // 最近一次经期开始日
let periodDays = 5;                          // 经期长度（天）
let cycleDays = 28;                          // 周期长度（天）

const periodDaysSelect = document.getElementById('periodDays');
const cycleDaysMainSelect = document.getElementById('cycleDaysMain');
const cycleDaysInput = document.getElementById('cycleDaysInput');

// 生成下拉选项
function fillSelect(select, from, to, unit, selected) {
  select.innerHTML = '';
  for (let i = from; i <= to; i++) {
    const option = document.createElement('option');
    option.value = String(i);
    option.textContent = i + ' ' + unit;
    if (i === selected) option.selected = true;
    select.appendChild(option);
  }
}

// 若记录出的天数不在预设范围内，动态补充选项
function ensureOption(select, value, unit) {
  const exists = Array.from(select.options).some(function (option) {
    return option.value === String(value);
  });
  if (!exists) {
    const option = document.createElement('option');
    option.value = String(value);
    option.textContent = value + ' ' + unit;
    select.appendChild(option);
  }
}

function renderCycle() {
  ensureOption(periodDaysSelect, periodDays, '天');
  ensureOption(cycleDaysMainSelect, cycleDays, '天');
  ensureOption(cycleDaysInput, cycleDays, '天');

  periodDaysSelect.value = String(periodDays);
  cycleDaysMainSelect.value = String(cycleDays);
  cycleDaysInput.value = String(cycleDays);

  const end = addDays(lastPeriodStart, periodDays - 1);
  document.getElementById('lastPeriodRange').textContent =
    formatMD(lastPeriodStart) + ' - ' + formatMD(end);

  // 排卵日按“下次月经前 14 天”估算
  document.getElementById('ovulationDate').textContent =
    formatMD(addDays(lastPeriodStart, cycleDays - 14));
}

fillSelect(periodDaysSelect, 3, 10, '天', periodDays);
fillSelect(cycleDaysMainSelect, 21, 40, '天', cycleDays);
fillSelect(cycleDaysInput, 21, 40, '天', cycleDays);

periodDaysSelect.addEventListener('change', function () {
  periodDays = parseInt(periodDaysSelect.value, 10);
  renderCycle();
});

cycleDaysMainSelect.addEventListener('change', function () {
  cycleDays = parseInt(cycleDaysMainSelect.value, 10);
  renderCycle();
});

// ---------- 弹窗开关辅助 ----------
function openMask(mask) {
  mask.classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeMask(mask) {
  mask.classList.remove('open');
  if (!document.querySelector('.mask.open')) document.body.style.overflow = '';
}

// ---------- 生理期记录弹窗 ----------
const periodMask = document.getElementById('periodMask');

// 弹窗内实时预览经期长度与排卵日
function updatePeriodPreview() {
  const start = parseISODate(document.getElementById('periodStart').value);
  const end = parseISODate(document.getElementById('periodEnd').value);
  const cycle = parseInt(cycleDaysInput.value, 10) || cycleDays;
  const daysEl = document.getElementById('periodPreviewDays');
  const ovulationEl = document.getElementById('periodPreviewOvulation');

  if (!start || !end || end < start) {
    daysEl.textContent = '—';
    ovulationEl.textContent = '—';
    return;
  }

  daysEl.textContent = (Math.round((end - start) / MS_PER_DAY) + 1) + ' 天';
  ovulationEl.textContent = formatMD(addDays(start, cycle - 14));
}

document.getElementById('openPeriod').addEventListener('click', function () {
  document.getElementById('periodStart').value = toISODate(lastPeriodStart);
  document.getElementById('periodEnd').value = toISODate(addDays(lastPeriodStart, periodDays - 1));
  cycleDaysInput.value = String(cycleDays);
  updatePeriodPreview();
  openMask(periodMask);
});

['periodStart', 'periodEnd'].forEach(function (id) {
  document.getElementById(id).addEventListener('change', updatePeriodPreview);
});
cycleDaysInput.addEventListener('change', updatePeriodPreview);

document.getElementById('periodClose').addEventListener('click', function () {
  closeMask(periodMask);
});

document.getElementById('periodCancel').addEventListener('click', function () {
  closeMask(periodMask);
});

periodMask.addEventListener('click', function (event) {
  if (event.target === periodMask) closeMask(periodMask);
});

document.getElementById('periodSave').addEventListener('click', function () {
  const start = parseISODate(document.getElementById('periodStart').value);
  const end = parseISODate(document.getElementById('periodEnd').value);
  const nextCycle = parseInt(cycleDaysInput.value, 10);

  if (!start || !end) {
    showToast('请选择开始和结束日期');
    return;
  }
  if (end < start) {
    showToast('结束日期不能早于开始日期');
    return;
  }

  const days = Math.round((end - start) / MS_PER_DAY) + 1;
  if (days < 1 || days > 15) {
    showToast('经期长度需在 1-15 天之间');
    return;
  }
  if (!nextCycle || nextCycle < 21 || nextCycle > 40) {
    showToast('请选择正确的周期长度');
    return;
  }

  lastPeriodStart = start;
  periodDays = days;
  cycleDays = nextCycle;

  renderCycle();
  closeMask(periodMask);
  showToast('生理期记录已保存');
});

// ---------- 状态标签：从预设选项中多选 ----------
const femaleTagValues = ['轻微腹痛', '情绪平稳', '腰酸', '疲惫', '头痛', '失眠', '食欲不振', '状态良好'];

// 今日状态对应的小建议：勾选后立即更新提示
const statusAdvice = {
  '轻微腹痛': '腹部注意保暖，可用热水袋热敷，避免生冷食物与剧烈运动。',
  '腰酸': '减少久坐久站，睡前热敷腰部，可做猫式伸展放松腰背。',
  '疲惫': '今天以恢复为主，保证 7-9 小时睡眠，运动改为散步或拉伸。',
  '头痛': '规律饮水与进食，减少屏幕时间；若持续加重请及时就医。',
  '失眠': '睡前 1 小时远离手机，避免咖啡因，可尝试 4-7-8 呼吸法。',
  '食欲不振': '少量多餐，选择温热易消化的食物，如粥、面条、蒸蛋。',
  '状态良好': '状态不错，可以按计划进行中等强度运动，运动后注意补充蛋白质。',
  '情绪平稳': '情绪平稳，适合安排 20-30 分钟有氧运动，继续保持规律作息。'
};

function updateStatusTip(values) {
  const tip = document.getElementById('statusTip');
  if (!tip) return;

  const messages = values.map(function (value) {
    return statusAdvice[value];
  }).filter(Boolean);

  tip.textContent = messages.length
    ? '科学建议：' + messages.slice(0, 2).join(' ')
    : '科学建议：记录今日状态后，这里会给出对应的护理建议。';
}

function closeTagMenus() {
  document.querySelectorAll('.tag-menu.open').forEach(function (menu) {
    menu.classList.remove('open');
  });
}

function createTagEditor(config) {
  const tagsEl = document.getElementById(config.tagsId);
  const addBtn = document.getElementById(config.addBtnId);
  const menu = document.getElementById(config.menuId);
  const optionsEl = document.getElementById(config.optionsId);
  const selected = new Set(config.initial);

  // 重新绘制已选标签
  function renderTags() {
    tagsEl.querySelectorAll('.tag:not(.add)').forEach(function (tag) {
      tag.remove();
    });

    selected.forEach(function (value) {
      const tag = document.createElement('span');
      tag.className = 'tag';
      tag.textContent = value;

      const remove = document.createElement('button');
      remove.type = 'button';
      remove.className = 'x';
      remove.textContent = '×';
      remove.title = '移除标签';
      remove.setAttribute('aria-label', '移除标签');
      remove.addEventListener('click', function () {
        selected.delete(value);
        renderTags();
        renderOptions();
      });

      tag.appendChild(remove);
      tagsEl.insertBefore(tag, addBtn);
    });

    updateStatusTip(Array.from(selected));
  }

  // 绘制可选项，点击切换选中状态
  function renderOptions() {
    optionsEl.innerHTML = '';
    config.values.forEach(function (value) {
      const option = document.createElement('button');
      option.type = 'button';
      option.className = 'tag-option' + (selected.has(value) ? ' selected' : '');
      option.textContent = value;
      option.addEventListener('click', function () {
        if (selected.has(value)) {
          selected.delete(value);
        } else {
          selected.add(value);
        }
        option.classList.toggle('selected');
        renderTags(); // 勾选后立即同步标签区
      });
      optionsEl.appendChild(option);
    });
  }

  addBtn.addEventListener('click', function (event) {
    event.stopPropagation();
    closeTagMenus();
    renderOptions();
    menu.classList.add('open');
  });

  menu.addEventListener('click', function (event) {
    event.stopPropagation();
  });

  menu.querySelector('[data-close-tag]').addEventListener('click', function () {
    menu.classList.remove('open');
    renderTags();
  });

  renderTags();
}

createTagEditor({
  tagsId: 'femaleTags',
  addBtnId: 'femaleAddTag',
  menuId: 'femaleTagMenu',
  optionsId: 'femaleTagOptions',
  values: femaleTagValues,
  initial: ['轻微腹痛', '情绪平稳']
});

// 点击标签面板以外的地方时收起面板
document.addEventListener('click', function (event) {
  if (!event.target.closest('.tag-menu') && !event.target.closest('.tag.add')) {
    closeTagMenus();
  }
});

// ---------- 家人健康：成员、健康记录与关怀提醒 ----------
const familyMask = document.getElementById('familyMask');
const memberMask = document.getElementById('memberMask');
const reminderMask = document.getElementById('reminderMask');
const familyPersonSelect = document.getElementById('familyPerson');
const familyTypeSelect = document.getElementById('familyType');
const reminderMemberSelect = document.getElementById('reminderMember');

// 家人列表（可通过「添加家人」继续扩展）
let familyMembers = [
  {
    id: 'm1',
    relation: '母亲',
    name: '',
    age: 58,
    conditions: '高血压',
    medications: '降压药 每日 1 片',
    emergencyName: '王小明（儿子）',
    emergencyPhone: '13800000000'
  },
  {
    id: 'm2',
    relation: '爱人',
    name: '',
    age: 28,
    conditions: '无',
    medications: '无',
    emergencyName: '',
    emergencyPhone: ''
  }
];

const todayDate = new Date();

// 健康记录
let familyRecords = [
  {
    memberId: 'm1',
    type: '体检',
    date: toISODate(addDays(todayDate, -39)),
    content: '各项指标正常'
  }
];

// 关怀提醒：默认给出「今天」与「三天后」两条示例，之后读取本地保存的数据
let reminders = loadData('reminders', [
  {
    id: 'r1',
    memberId: 'm1',
    title: '提醒母亲测量血压',
    date: toISODate(todayDate),
    done: false
  },
  {
    id: 'r2',
    memberId: 'm2',
    title: '提醒爱人注意经期保暖',
    date: toISODate(addDays(todayDate, 3)),
    done: false
  }
]);

function getMember(memberId) {
  return familyMembers.filter(function (member) {
    return member.id === memberId;
  })[0];
}

function memberLabel(member) {
  if (!member) return '家人';
  return member.relation + (member.name ? ' · ' + member.name : '');
}

// 取某位家人最近的一条记录
function latestRecord(memberId) {
  const records = familyRecords.filter(function (record) {
    return record.memberId === memberId;
  });
  if (!records.length) return null;
  return records.slice().sort(function (a, b) {
    return b.date.localeCompare(a.date);
  })[0];
}

// 渲染家人卡片
function renderFamilyMembers() {
  const grid = document.getElementById('familyGrid');
  grid.innerHTML = '';

  familyMembers.forEach(function (member) {
    const card = document.createElement('div');
    card.className = 'person-card';

    const head = document.createElement('div');
    head.className = 'person-head';

    const avatar = document.createElement('div');
    avatar.className = 'person-avatar';
    avatar.textContent = member.relation.charAt(0);

    const info = document.createElement('div');
    const name = document.createElement('span');
    name.className = 'person-name';
    name.textContent = memberLabel(member);
    info.appendChild(name);

    if (member.age) {
      const age = document.createElement('span');
      age.className = 'person-age';
      age.textContent = member.age + '岁';
      info.appendChild(age);
    }

    head.appendChild(avatar);
    head.appendChild(info);
    card.appendChild(head);

    // 卡片上的三行关键信息：基础病史 / 常用药物 / 紧急联系人
    function appendInfoLine(label, value) {
      const line = document.createElement('div');
      line.className = 'family-line';
      line.appendChild(document.createTextNode(label));
      const text = document.createElement('b');
      text.textContent = value || '暂无';
      line.appendChild(text);
      card.appendChild(line);
    }

    appendInfoLine('基础病史', member.conditions);
    appendInfoLine('常用药物', member.medications);
    appendInfoLine('紧急联系人', emergencyText(member));

    // 最近记录
    const record = latestRecord(member.id);
    const recordLine = document.createElement('div');
    recordLine.className = 'family-line clickable';
    recordLine.appendChild(document.createTextNode('最近记录'));
    const recordValue = document.createElement('b');
    recordValue.textContent = record
      ? formatYMD(parseISODate(record.date)) + ' · ' + record.type + ' ›'
      : '暂无记录 ›';
    recordLine.appendChild(recordValue);
    card.appendChild(recordLine);

    // 点击整张卡片查看完整健康数据
    card.title = '点击查看完整健康档案';
    card.addEventListener('click', function () {
      openMemberDetail(member);
    });

    grid.appendChild(card);
  });
}

// 紧急联系人展示文本
function emergencyText(member) {
  if (!member) return '';
  const name = member.emergencyName || '';
  const phone = member.emergencyPhone || '';
  if (!name && !phone) return '未填写';
  return name + (phone ? (name ? ' · ' : '') + phone : '');
}

// 渲染某位家人的全部记录（在详情弹窗中展示）
function renderFamilyRecords(memberId) {
  const records = familyRecords.filter(function (record) {
    return record.memberId === memberId;
  }).sort(function (a, b) {
    return b.date.localeCompare(a.date);
  });

  if (!records.length) return '<div class="member-record-empty">暂无健康记录，点击「添加记录」为该家人建档。</div>';

  return records.map(function (record) {
    return '<div class="member-record"><span class="date">' + formatYMD(parseISODate(record.date)) +
      '</span><span>' + escapeHtml(record.type) +
      (record.content ? ' · ' + escapeHtml(record.content) : '') + '</span></div>';
  }).join('');
}

// 点击家人卡片：打开完整健康档案
function openMemberDetail(member) {
  const body = document.getElementById('memberDetailBody');
  if (!body || !member) return;

  document.getElementById('memberRecordsTitle').textContent = memberLabel(member) + ' · 健康档案';

  const pending = reminders.filter(function (reminder) {
    return reminder.memberId === member.id && !reminder.done;
  }).sort(function (a, b) {
    return a.date.localeCompare(b.date);
  });

  const infoRows = [
    { label: '基础病史', value: member.conditions },
    { label: '常用药物', value: member.medications },
    { label: '紧急联系人', value: emergencyText(member) }
  ].map(function (row) {
    return '<div class="detail-item"><span>' + row.label + '</span><b>' +
      escapeHtml(row.value || '暂无') + '</b></div>';
  }).join('');

  const reminderRows = pending.length
    ? pending.map(function (reminder) {
      return '<div class="member-record"><span class="date">' +
        formatMD(parseISODate(reminder.date)) + '</span><span>' +
        escapeHtml(reminder.title) + '</span></div>';
    }).join('')
    : '<div class="member-record-empty">暂无待办提醒，可在「关怀提醒」中添加。</div>';

  body.innerHTML =
    '<div class="member-detail-head">' +
      '<div class="person-avatar">' + escapeHtml(member.relation.charAt(0)) + '</div>' +
      '<div class="member-detail-name"><b>' + escapeHtml(memberLabel(member)) + '</b><span>' +
        (member.age ? member.age + ' 岁' : '年龄未填写') + '</span></div>' +
    '</div>' +
    '<div class="detail-grid">' + infoRows + '</div>' +
    '<h4 class="detail-title">健康记录</h4>' + renderFamilyRecords(member.id) +
    '<h4 class="detail-title">待办提醒</h4>' + reminderRows;

  openMask(document.getElementById('memberRecordsMask'));
}

// 简单的 HTML 转义，避免用户输入的内容破坏结构
function escapeHtml(text) {
  return String(text == null ? '' : text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

const memberRecordsMask = document.getElementById('memberRecordsMask');

document.getElementById('memberRecordsClose').addEventListener('click', function () {
  closeMask(memberRecordsMask);
});

memberRecordsMask.addEventListener('click', function (event) {
  if (event.target === memberRecordsMask) closeMask(memberRecordsMask);
});

// ---------- 常用提醒：可自定义，保存在本地长期使用 ----------
const DEFAULT_QUICK_REMINDERS = [
  { label: '测量血压', text: '提醒家人测量血压' },
  { label: '按时吃药', text: '提醒家人按时吃药' },
  { label: '陪伴散步', text: '陪家人散步 30 分钟' },
  { label: '复诊体检', text: '预约复诊 / 体检' },
  { label: '多喝水', text: '提醒家人多喝水' },
  { label: '注意保暖', text: '提醒家人注意保暖' }
];

let quickReminders = loadData('quickReminders', DEFAULT_QUICK_REMINDERS);

function renderQuickReminders() {
  const box = document.getElementById('quickReminderBox');
  if (!box) return;
  box.innerHTML = '<span>常用提醒</span>';

  quickReminders.forEach(function (item) {
    const chip = document.createElement('button');
    chip.className = 'quick-chip';
    chip.type = 'button';
    chip.textContent = item.label;
    chip.title = item.text;
    chip.addEventListener('click', function () {
      openReminderDialog(item.text, [toISODate(addDays(new Date(), 1))]);
    });
    box.appendChild(chip);
  });

  // 手动添加常用提醒
  const addBtn = document.createElement('button');
  addBtn.className = 'quick-chip';
  addBtn.type = 'button';
  addBtn.style.borderStyle = 'dashed';
  addBtn.textContent = '＋ 自定义';
  addBtn.addEventListener('click', function () {
    const text = window.prompt('输入常用提醒内容，例如：提醒奶奶测血糖');
    const value = (text || '').trim();
    if (!value) return;
    if (quickReminders.some(function (item) { return item.text === value; })) {
      showToast('这条常用提醒已存在');
      return;
    }
    quickReminders.push({ label: value, text: value });
    saveData('quickReminders', quickReminders);
    renderQuickReminders();
    showToast('已添加到常用提醒');
  });
  box.appendChild(addBtn);
}

// ---------- 提醒日期：支持一次选择多个 ----------
let reminderPickedDates = [];

function renderReminderDates() {
  const box = document.getElementById('reminderDateList');
  if (!box) return;
  box.innerHTML = '';

  if (!reminderPickedDates.length) {
    box.innerHTML = '<span class="date-empty">还没有选择日期，可在上方快捷选择或手动添加</span>';
    return;
  }

  reminderPickedDates.slice().sort().forEach(function (iso) {
    const tag = document.createElement('span');
    tag.className = 'date-tag';
    tag.innerHTML = '<span>' + iso.slice(5) + ' 周' + '日一二三四五六'[parseISODate(iso).getDay()] + '</span>';

    const del = document.createElement('button');
    del.type = 'button';
    del.textContent = '×';
    del.title = '移除这个日期';
    del.addEventListener('click', function () {
      reminderPickedDates = reminderPickedDates.filter(function (date) { return date !== iso; });
      renderReminderDates();
    });

    tag.appendChild(del);
    box.appendChild(tag);
  });
}

function addReminderDate(iso) {
  if (!iso) return;
  if (reminderPickedDates.indexOf(iso) !== -1) {
    showToast('这个日期已经选过啦');
    return;
  }
  reminderPickedDates.push(iso);
  reminderPickedDates.sort();
  renderReminderDates();
}

function openReminderDialog(title, dates) {
  renderMemberOptions();
  document.getElementById('reminderTitle').value = title || '';
  document.getElementById('reminderDate').value = '';
  reminderPickedDates = (dates || []).slice();
  renderReminderDates();
  openMask(reminderMask);
}

// 快捷日期按钮
document.querySelectorAll('.date-chip').forEach(function (btn) {
  btn.addEventListener('click', function () {
    addReminderDate(toISODate(addDays(new Date(), Number(btn.dataset.day))));
  });
});

// 手动添加日期：点按钮或直接回车
document.getElementById('reminderDateAdd').addEventListener('click', function () {
  const input = document.getElementById('reminderDate');
  if (!input.value) {
    showToast('请选择要添加的日期');
    return;
  }
  addReminderDate(input.value);
  input.value = '';
});

document.getElementById('reminderDate').addEventListener('keydown', function (event) {
  if (event.key !== 'Enter' || event.isComposing) return;
  event.preventDefault();
  document.getElementById('reminderDateAdd').click();
});

// 渲染关怀提醒
function renderReminders() {
  const list = document.getElementById('reminderList');
  list.innerHTML = '';

  const pendingCount = reminders.filter(function (reminder) {
    return !reminder.done;
  }).length;
  document.getElementById('reminderCount').textContent =
    pendingCount ? pendingCount + ' 条待办' : '暂无待办';

  if (!reminders.length) {
    const empty = document.createElement('div');
    empty.className = 'reminder-empty';
    empty.textContent = '暂无关怀提醒，点击「添加提醒」设置一条吧。';
    list.appendChild(empty);
    return;
  }

  const todayStr = toISODate(new Date());

  reminders.slice().sort(function (a, b) {
    if (a.done !== b.done) return a.done ? 1 : -1;
    return a.date.localeCompare(b.date);
  }).forEach(function (reminder) {
    const member = getMember(reminder.memberId);
    const target = parseISODate(reminder.date);
    const diffDays = Math.round((target - parseISODate(todayStr)) / MS_PER_DAY);

    const item = document.createElement('div');
    item.className = 'reminder-item' + (reminder.done ? ' done' : '');

    // 完成按钮
    const check = document.createElement('button');
    check.type = 'button';
    check.className = 'reminder-check';
    check.textContent = reminder.done ? '✓' : '';
    check.title = reminder.done ? '标记为未完成' : '标记为已完成';
    check.addEventListener('click', function () {
      reminder.done = !reminder.done;
      saveData('reminders', reminders);
      renderReminders();
      renderFamilyMembers();
      showToast(reminder.done ? '已完成这条关怀提醒' : '已恢复为待办');
    });

    const main = document.createElement('div');
    main.className = 'reminder-main';

    const title = document.createElement('div');
    title.className = 'reminder-title';
    title.textContent = reminder.title;

    const meta = document.createElement('div');
    meta.className = 'reminder-meta';
    meta.textContent = formatYMD(target) + ' · ' + memberLabel(member);

    main.appendChild(title);
    main.appendChild(meta);

    // 日期状态标签
    const badge = document.createElement('span');
    badge.className = 'reminder-badge';
    if (reminder.done) {
      badge.textContent = '已完成';
      badge.classList.add('done');
    } else if (diffDays === 0) {
      badge.textContent = '今天';
      badge.classList.add('today');
    } else if (diffDays === 1) {
      badge.textContent = '明天';
    } else if (diffDays < 0) {
      badge.textContent = '已逾期';
      badge.classList.add('overdue');
    } else {
      badge.textContent = formatMD(target);
    }

    // 删除这条提醒
    const del = document.createElement('button');
    del.type = 'button';
    del.className = 'reminder-del';
    del.textContent = '删除';
    del.title = '删除这条关怀提醒';
    del.addEventListener('click', function () {
      const index = reminders.indexOf(reminder);
      if (index === -1) return;
      reminders.splice(index, 1);
      saveData('reminders', reminders);
      renderReminders();
      renderFamilyMembers();
      showToast('已删除这条关怀提醒');
    });

    item.appendChild(check);
    item.appendChild(main);
    item.appendChild(badge);
    item.appendChild(del);
    list.appendChild(item);
  });
}

// 同步「记录 / 提醒」弹窗中的家人下拉框
function renderMemberOptions() {
  [familyPersonSelect, reminderMemberSelect].forEach(function (select) {
    const previous = select.value;

    select.innerHTML = '';
    familyMembers.forEach(function (member) {
      const option = document.createElement('option');
      option.value = member.id;
      option.textContent = memberLabel(member);
      select.appendChild(option);
    });

    const exists = familyMembers.some(function (member) {
      return member.id === previous;
    });
    if (exists) select.value = previous;
  });

  renderFamilyTypes();
}

// 仅「爱人」可以记录生理期
function renderFamilyTypes() {
  const member = getMember(familyPersonSelect.value);
  const types = member && member.relation === '爱人'
    ? ['体检', '用药', '生理期', '其他']
    : ['体检', '用药', '其他'];

  const previous = familyTypeSelect.value;
  familyTypeSelect.innerHTML = '';

  types.forEach(function (type) {
    const option = document.createElement('option');
    option.value = type;
    option.textContent = type;
    familyTypeSelect.appendChild(option);
  });

  if (types.indexOf(previous) !== -1) {
    familyTypeSelect.value = previous;
  }
}

familyPersonSelect.addEventListener('change', renderFamilyTypes);

// ---------- 添加健康记录弹窗 ----------
document.getElementById('openFamilyRecord').addEventListener('click', function () {
  renderMemberOptions();
  document.getElementById('familyDate').value = toISODate(new Date());
  openMask(familyMask);
});

document.getElementById('familyClose').addEventListener('click', function () {
  closeMask(familyMask);
});

document.getElementById('familyCancel').addEventListener('click', function () {
  closeMask(familyMask);
});

familyMask.addEventListener('click', function (event) {
  if (event.target === familyMask) closeMask(familyMask);
});

document.getElementById('familySave').addEventListener('click', function () {
  const member = getMember(familyPersonSelect.value);
  const type = familyTypeSelect.value;
  const date = parseISODate(document.getElementById('familyDate').value);
  const content = document.getElementById('familyContent').value.trim();

  if (!member) {
    showToast('请先添加家人信息');
    return;
  }
  if (!date) {
    showToast('请选择记录日期');
    return;
  }

  familyRecords.push({
    memberId: member.id,
    type: type,
    date: toISODate(date),
    content: content
  });

  renderFamilyMembers();

  document.getElementById('familyContent').value = '';
  closeMask(familyMask);
  showToast('已为' + memberLabel(member) + '添加' + type + '记录');
});

// ---------- 添加家人信息弹窗 ----------
document.getElementById('openMember').addEventListener('click', function () {
  document.getElementById('memberRelation').value = '';
  document.getElementById('memberAge').value = '';
  document.getElementById('memberName').value = '';
  document.getElementById('memberConditions').value = '';
  document.getElementById('memberMedications').value = '';
  document.getElementById('memberEmergencyName').value = '';
  document.getElementById('memberEmergencyPhone').value = '';
  openMask(memberMask);
});

document.getElementById('memberClose').addEventListener('click', function () {
  closeMask(memberMask);
});

document.getElementById('memberCancel').addEventListener('click', function () {
  closeMask(memberMask);
});

memberMask.addEventListener('click', function (event) {
  if (event.target === memberMask) closeMask(memberMask);
});

document.getElementById('memberSave').addEventListener('click', function () {
  const relation = document.getElementById('memberRelation').value.trim();
  const age = parseInt(document.getElementById('memberAge').value, 10);
  const name = document.getElementById('memberName').value.trim();
  const conditions = document.getElementById('memberConditions').value.trim();
  const medications = document.getElementById('memberMedications').value.trim();
  const emergencyName = document.getElementById('memberEmergencyName').value.trim();
  const emergencyPhone = document.getElementById('memberEmergencyPhone').value.trim();

  if (!relation) {
    showToast('请填写家人的称呼或关系');
    return;
  }

  familyMembers.push({
    id: 'm' + Date.now(),
    relation: relation,
    name: name,
    age: age || '',
    conditions: conditions,
    medications: medications,
    emergencyName: emergencyName,
    emergencyPhone: emergencyPhone
  });

  renderFamilyMembers();
  renderMemberOptions();
  closeMask(memberMask);
  showToast('已添加家人：' + relation);
});

// ---------- 添加关怀提醒弹窗 ----------
document.getElementById('openReminder').addEventListener('click', function () {
  openReminderDialog('', [toISODate(new Date())]);
});

document.getElementById('reminderClose').addEventListener('click', function () {
  closeMask(reminderMask);
});

document.getElementById('reminderCancel').addEventListener('click', function () {
  closeMask(reminderMask);
});

reminderMask.addEventListener('click', function (event) {
  if (event.target === reminderMask) closeMask(reminderMask);
});

document.getElementById('reminderSave').addEventListener('click', function () {
  const member = getMember(reminderMemberSelect.value);
  const title = document.getElementById('reminderTitle').value.trim();

  if (!member) {
    showToast('请先添加家人信息');
    return;
  }
  if (!title) {
    showToast('请填写提醒内容');
    return;
  }
  if (!reminderPickedDates.length) {
    showToast('请至少选择一个提醒日期');
    return;
  }

  // 每个选中的日期各生成一条提醒
  reminderPickedDates.slice().sort().forEach(function (date, index) {
    reminders.push({
      id: 'r' + Date.now() + '-' + index,
      memberId: member.id,
      title: title,
      date: date,
      done: false
    });
  });
  saveData('reminders', reminders);

  renderReminders();
  renderFamilyMembers();
  closeMask(reminderMask);
  showToast('已添加 ' + reminderPickedDates.length + ' 条关怀提醒');
});

// 初始化页面状态
renderCycle();
applyGenderView();
renderMemberOptions();
renderFamilyMembers();
renderReminders();
renderQuickReminders();

/* ==========================================================
   六之三、本地数据层与新增功能
   ========================================================== */

// ---------- localStorage 读写 ----------
function loadData(key, fallback) {
  try {
    const raw = window.localStorage.getItem('hm_' + key);
    return raw ? JSON.parse(raw) : fallback;
  } catch (error) {
    return fallback;
  }
}

function saveData(key, value) {
  try {
    window.localStorage.setItem('hm_' + key, JSON.stringify(value));
  } catch (error) {
    // 无痕模式等场景下写入失败，忽略即可
  }
}

// ---------- 核心数据：修改弹窗 + 近一个月记录 ----------
const vitalMask = document.getElementById('vitalMask');
let currentVital = 'weight';

const vitalConfig = {
  weight: { title: '修改体重', fields: [{ key: 'weight', label: '体重（kg）', step: '0.1' }] },
  fat: { title: '修改体脂率', fields: [{ key: 'fat', label: '体脂率（%）', step: '0.1' }] },
  bmi: { title: '修改 BMI', fields: [{ key: 'bmi', label: 'BMI（保存后自动换算体重）', step: '0.1' }] },
  bp: {
    title: '修改血压',
    fields: [
      { key: 'systolic', label: '收缩压 / 高压', step: '1' },
      { key: 'diastolic', label: '舒张压 / 低压', step: '1' }
    ]
  },
  glucose: { title: '修改血糖', fields: [{ key: 'glucose', label: '空腹血糖（mmol/L）', step: '0.1' }] }
};

function loadVitalsHistory() {
  return loadData('vitalsHistory', {});
}

// 记录一次数据，只保留最近 30 天
function pushVitalRecord(key, text) {
  const history = loadVitalsHistory();
  const now = new Date();
  const cutoff = toISODate(addDays(now, -30));

  if (!history[key]) history[key] = [];
  history[key].push({
    date: toISODate(now) + ' ' + now.toTimeString().slice(0, 5),
    text: text
  });
  history[key] = history[key].filter(function (item) {
    return item.date.slice(0, 10) >= cutoff;
  }).slice(-60);
  saveData('vitalsHistory', history);
}

function renderVitalHistory(key) {
  const box = document.getElementById('vitalHistory');
  const list = (loadVitalsHistory()[key] || []).slice().reverse();

  if (!list.length) {
    box.innerHTML = '<div class="vital-history-empty">近一个月还没有记录。</div>';
    return;
  }

  box.innerHTML = list.map(function (item) {
    return '<div class="vital-history-row"><span>' + item.date + '</span><b>' + item.text + '</b></div>';
  }).join('');
}

function openVitalModal(key) {
  currentVital = key;
  const config = vitalConfig[key];
  document.getElementById('vitalTitle').textContent = config.title;

  const fields = document.getElementById('vitalFields');
  fields.innerHTML = '';
  config.fields.forEach(function (field) {
    const wrap = document.createElement('div');
    wrap.className = 'field';
    wrap.innerHTML = '<label for="vf_' + field.key + '">' + field.label + '</label>' +
      '<input id="vf_' + field.key + '" type="number" step="' + field.step + '">';
    fields.appendChild(wrap);
  });

  // 回填当前数值
  if (key === 'weight') document.getElementById('vf_weight').value = document.getElementById('weightValue').textContent;
  if (key === 'fat') document.getElementById('vf_fat').value = document.getElementById('fatValue').textContent;
  if (key === 'bmi') document.getElementById('vf_bmi').value = document.getElementById('bmiValue').textContent;
  if (key === 'glucose') document.getElementById('vf_glucose').value = document.getElementById('glucoseValue').textContent;
  if (key === 'bp') {
    const parts = document.getElementById('bpValue').textContent.split('/');
    document.getElementById('vf_systolic').value = parts[0] || '';
    document.getElementById('vf_diastolic').value = parts[1] || '';
  }

  renderVitalHistory(key);
  openMask(vitalMask);
}

document.querySelectorAll('[data-vital]').forEach(function (btn) {
  btn.addEventListener('click', function () {
    openVitalModal(btn.dataset.vital);
  });
});

document.getElementById('vitalClose').addEventListener('click', function () {
  closeMask(vitalMask);
});

document.getElementById('vitalCancel').addEventListener('click', function () {
  closeMask(vitalMask);
});

vitalMask.addEventListener('click', function (event) {
  if (event.target === vitalMask) closeMask(vitalMask);
});

function setBmiDisplay(bmi) {
  document.getElementById('bmiValue').textContent = bmi.toFixed(1);
  const badge = document.getElementById('bmiBadge');

  // 中国成人 BMI 标准：＜18.5 偏瘦，18.5–23.9 正常，24.0–27.9 超重，≥28.0 肥胖
  if (bmi < 18.5) {
    badge.textContent = '偏瘦';
    badge.className = 'badge warn';
  } else if (bmi < 24) {
    badge.textContent = '正常';
    badge.className = 'badge';
  } else if (bmi < 28) {
    badge.textContent = '超重';
    badge.className = 'badge warn';
  } else {
    badge.textContent = '肥胖';
    badge.className = 'badge warn';
  }
}

function currentHeightMeters() {
  return (parseFloat(document.getElementById('pHeight').value) || 165) / 100;
}

/* ==========================================================
   核心体征：正常值范围与异常提醒
   标准来源：WS/T 428-2013（成人 BMI）、中国高血压防治指南、
            中国 2 型糖尿病防治指南、常用体成分参考值
   ========================================================== */
function currentHeightCm() {
  const saved = parseFloat(readProfile().height);
  if (saved > 0) return saved;
  const input = parseFloat(document.getElementById('pHeight').value);
  return input > 0 ? input : 165;
}

function setRangeState(id, text, warn) {
  const el = document.getElementById(id);
  el.textContent = text;
  el.className = 'rr-state' + (warn ? ' warn' : '');
}

function renderVitalRanges() {
  const heightCm = currentHeightCm();
  const heightM = heightCm / 100;
  const weight = parseFloat(document.getElementById('weightValue').textContent);
  const bmi = parseFloat(document.getElementById('bmiValue').textContent);
  const fat = parseFloat(document.getElementById('fatValue').textContent);
  const glucose = parseFloat(document.getElementById('glucoseValue').textContent);
  const bp = (document.getElementById('bpValue').textContent || '').split('/');
  const systolic = parseInt(bp[0], 10);
  const diastolic = parseInt(bp[1], 10);
  const isFemale = (currentGender || document.getElementById('pGender').value) === '女';

  const warnings = [];

  // 体重：按正常 BMI 区间反推
  const lowWeight = 18.5 * heightM * heightM;
  const highWeight = 23.9 * heightM * heightM;
  document.getElementById('refWeight').textContent =
    lowWeight.toFixed(1) + '–' + highWeight.toFixed(1) + ' kg';

  if (weight) {
    if (weight < lowWeight) {
      setRangeState('stateWeight', '偏低', true);
      warnings.push('体重 ' + weight.toFixed(1) + ' kg 低于参考下限 ' + lowWeight.toFixed(1) +
        ' kg（BMI＜18.5），建议增加优质蛋白与主食摄入。');
    } else if (weight > highWeight) {
      setRangeState('stateWeight', '偏高', true);
      warnings.push('体重 ' + weight.toFixed(1) + ' kg 高于参考上限 ' + highWeight.toFixed(1) +
        ' kg（BMI＞23.9），建议控制总热量并增加日常活动。');
    } else {
      setRangeState('stateWeight', '正常', false);
    }
  }

  if (bmi) {
    if (bmi < 18.5) {
      setRangeState('stateBmi', '偏瘦', true);
      warnings.push('BMI ' + bmi.toFixed(1) + ' 属于偏瘦（＜18.5），建议保证三餐并适度增加力量训练。');
    } else if (bmi < 24) {
      setRangeState('stateBmi', '正常', false);
    } else if (bmi < 28) {
      setRangeState('stateBmi', '超重', true);
      warnings.push('BMI ' + bmi.toFixed(1) + ' 属于超重（24.0–27.9），建议减少高油高糖食物并增加有氧运动。');
    } else {
      setRangeState('stateBmi', '肥胖', true);
      warnings.push('BMI ' + bmi.toFixed(1) + ' 达到肥胖（≥28.0），建议在医生或营养师指导下制定减重计划。');
    }
  }

  // 体脂率：常用参考值，女性 20%–30%，男性 10%–20%
  const lowFat = isFemale ? 20 : 10;
  const highFat = isFemale ? 30 : 20;
  document.getElementById('refFat').textContent = isFemale ? '女 20%–30%' : '男 10%–20%';

  if (fat) {
    if (fat < lowFat) {
      setRangeState('stateFat', '偏低', true);
      warnings.push('体脂率 ' + fat.toFixed(1) + '% 低于' + (isFemale ? '女性' : '男性') +
        '参考下限 ' + lowFat + '%，建议适当增加健康脂肪与蛋白质摄入。');
    } else if (fat > highFat) {
      setRangeState('stateFat', '偏高', true);
      warnings.push('体脂率 ' + fat.toFixed(1) + '% 高于' + (isFemale ? '女性' : '男性') +
        '参考上限 ' + highFat + '%，建议结合力量训练与有氧运动。');
    } else {
      setRangeState('stateFat', '正常', false);
    }
  }

  // 血压：＜120/80 正常，120–139/80–89 正常高值，≥140/90 偏高
  if (systolic && diastolic) {
    if (systolic < 90 || diastolic < 60) {
      setRangeState('stateBp', '偏低', true);
      warnings.push('血压 ' + systolic + '/' + diastolic + ' mmHg 偏低，若伴随头晕乏力请及时就医。');
    } else if (systolic < 120 && diastolic < 80) {
      setRangeState('stateBp', '正常', false);
    } else if (systolic < 140 && diastolic < 90) {
      setRangeState('stateBp', '正常高值', true);
      warnings.push('血压 ' + systolic + '/' + diastolic + ' mmHg 处于正常高值（120–139/80–89），建议减少盐分摄入并规律监测。');
    } else {
      setRangeState('stateBp', '偏高', true);
      warnings.push('血压 ' + systolic + '/' + diastolic + ' mmHg 达到高血压范围（≥140/90），建议尽快就医评估。');
    }
  }

  // 空腹血糖：3.9–6.1 正常，6.1–7.0 空腹血糖受损，≥7.0 偏高
  if (glucose) {
    if (glucose < 3.9) {
      setRangeState('stateGlucose', '偏低', true);
      warnings.push('空腹血糖 ' + glucose.toFixed(1) + ' mmol/L 低于 3.9，注意按时进餐，必要时就医。');
    } else if (glucose <= 6.1) {
      setRangeState('stateGlucose', '正常', false);
    } else if (glucose < 7.0) {
      setRangeState('stateGlucose', '空腹血糖受损', true);
      warnings.push('空腹血糖 ' + glucose.toFixed(1) + ' mmol/L 处于空腹血糖受损区间（6.1–7.0），建议复查并咨询医生。');
    } else {
      setRangeState('stateGlucose', '偏高', true);
      warnings.push('空腹血糖 ' + glucose.toFixed(1) + ' mmol/L 达到糖尿病诊断参考值（≥7.0），请尽快就医确认。');
    }
  }

  // 异常提醒列表
  const box = document.getElementById('abnormalBox');
  const list = document.getElementById('abnormalList');
  list.innerHTML = '';
  if (warnings.length) {
    box.classList.remove('ok');
    warnings.forEach(function (text) {
      const li = document.createElement('li');
      li.textContent = text;
      list.appendChild(li);
    });
  } else {
    box.classList.add('ok');
    const li = document.createElement('li');
    li.textContent = '各项体征均在参考范围内，继续保持。';
    list.appendChild(li);
  }

  // BMI 公式代入当前身高体重
  if (weight) {
    const computed = weight / Math.pow(heightM, 2);
    document.getElementById('bmiFormulaValue').textContent =
      '当前：' + weight.toFixed(1) + ' ÷ ' + heightM.toFixed(2) + '² ≈ ' + computed.toFixed(1) +
      '（身高 ' + heightCm.toFixed(0) + ' cm）';
  }
}

// 体重变化后同步 BMI、个人档案与趋势
function applyWeightChange(weight) {
  document.getElementById('weightValue').textContent = weight.toFixed(1);
  document.getElementById('pWeight').value = weight.toFixed(1);

  // 已保存档案时同步体重，刷新页面后仍能恢复
  const profile = readProfile();
  if (profile.weight !== undefined) {
    profile.weight = weight;
    saveData('profile', profile);
  }

  const bmi = weight / Math.pow(currentHeightMeters(), 2);
  setBmiDisplay(bmi);
  addWeightRecord(weight);
  return bmi;
}

document.getElementById('vitalSave').addEventListener('click', function () {
  const heightM = currentHeightMeters();

  if (currentVital === 'weight') {
    const value = parseFloat(document.getElementById('vf_weight').value);
    if (!value || value < 20 || value > 200) {
      showToast('请输入 20-200 kg 之间的体重');
      return;
    }
    const bmi = applyWeightChange(value);
    pushVitalRecord('weight', value.toFixed(1) + ' kg');
    pushVitalRecord('bmi', bmi.toFixed(1));
    showToast('体重已更新为 ' + value.toFixed(1) + ' kg');
  } else if (currentVital === 'fat') {
    const value = parseFloat(document.getElementById('vf_fat').value);
    if (!value || value < 3 || value > 60) {
      showToast('请输入 3-60% 之间的体脂率');
      return;
    }
    document.getElementById('fatValue').textContent = value.toFixed(1);
    pushVitalRecord('fat', value.toFixed(1) + ' %');
    showToast('体脂率已更新为 ' + value.toFixed(1) + '%');
  } else if (currentVital === 'bmi') {
    const bmi = parseFloat(document.getElementById('vf_bmi').value);
    if (!bmi || bmi < 12 || bmi > 45) {
      showToast('请输入 12-45 之间的 BMI');
      return;
    }
    const weight = bmi * heightM * heightM;
    applyWeightChange(weight);
    setBmiDisplay(bmi);
    pushVitalRecord('bmi', bmi.toFixed(1));
    pushVitalRecord('weight', weight.toFixed(1) + ' kg');
    showToast('已按 BMI 换算体重：' + weight.toFixed(1) + ' kg');
  } else if (currentVital === 'bp') {
    const systolic = parseInt(document.getElementById('vf_systolic').value, 10);
    const diastolic = parseInt(document.getElementById('vf_diastolic').value, 10);

    if (!systolic || !diastolic || systolic < 60 || systolic > 220 ||
        diastolic < 40 || diastolic > 140 || diastolic >= systolic) {
      showToast('请输入正确的血压，例如 118/76');
      return;
    }

    document.getElementById('bpValue').textContent = systolic + '/' + diastolic;
    saveData('bp', { systolic: systolic, diastolic: diastolic });
    pushVitalRecord('bp', systolic + '/' + diastolic + ' mmHg');
    showToast('血压已更新为 ' + systolic + '/' + diastolic + ' mmHg');
  } else if (currentVital === 'glucose') {
    const value = parseFloat(document.getElementById('vf_glucose').value);
    if (!value || value < 1 || value > 30) {
      showToast('请输入 1-30 mmol/L 之间的血糖');
      return;
    }
    document.getElementById('glucoseValue').textContent = value.toFixed(1);
    saveData('glucose', value);
    pushVitalRecord('glucose', value.toFixed(1) + ' mmol/L');
    showToast('血糖已更新为 ' + value.toFixed(1) + ' mmol/L');
  }

  closeMask(vitalMask);
  refreshDietViews();
  renderVitalRanges();
});

// 恢复上次保存的血压与血糖
const savedBp = loadData('bp', null);
if (savedBp && savedBp.systolic && savedBp.diastolic) {
  document.getElementById('bpValue').textContent = savedBp.systolic + '/' + savedBp.diastolic;
}
const savedGlucose = loadData('glucose', null);
if (savedGlucose) {
  document.getElementById('glucoseValue').textContent = Number(savedGlucose).toFixed(1);
}

// ---------- 体重历史与趋势曲线 ----------
// 体重记录：只保留最近 15 天
const WEIGHT_KEEP_DAYS = 15;
let weightHistory = loadData('weightHistory', []);

function pruneWeightHistory() {
  const cutoff = toISODate(addDays(new Date(), -(WEIGHT_KEEP_DAYS - 1)));
  weightHistory = weightHistory.filter(function (item) {
    return item.date >= cutoff;
  });
}

pruneWeightHistory();

function addWeightRecord(weight) {
  if (!weight || weight < 20 || weight > 200) return;

  const date = toISODate(new Date());
  const last = weightHistory[weightHistory.length - 1];

  // 同一天重复记录同一数值时跳过，否则每次都保留一个点，保证曲线上能看到变化
  if (last && last.date === date && Math.abs(last.weight - weight) < 0.01) {
    return;
  }
  weightHistory.push({ date: date, weight: weight });

  pruneWeightHistory();
  saveData('weightHistory', weightHistory);
  renderWeightChart();

  // 体重变化后重新计算营养目标与评分
  refreshDietViews();
}

// 曲线数据：只取 15 天内，同一天多次记录以最后一次为准
function recentWeightData() {
  const cutoff = toISODate(addDays(new Date(), -(WEIGHT_KEEP_DAYS - 1)));
  const byDate = {};

  weightHistory.forEach(function (item) {
    if (item.date < cutoff) return;
    byDate[item.date] = item.weight;
  });

  return Object.keys(byDate).sort().map(function (date) {
    return { date: date, weight: byDate[date] };
  });
}

function renderWeightChart() {
  // 体重曲线只保留在运动计划的目标进度中
  const boxes = ['weightChart'].map(function (id) {
    return document.getElementById(id);
  }).filter(Boolean);
  if (!boxes.length) return;

  let html = '';

  if (!weightHistory.length) {
    html = '<div class="weight-chart-empty">在「运动计划 · 记录当前体重」中记录后，这里会画出体重变化曲线。</div>';
  } else {
    const data = recentWeightData();
    const latest = data[data.length - 1].weight;
    const head = '<div class="weight-chart-head"><span>近 15 天体重趋势（' + data.length + ' 天有记录）</span><b>' +
      latest.toFixed(1) + ' kg</b></div>';

    if (data.length === 1) {
      html = head + '<div class="weight-chart-empty">再记录一次体重，就能看到趋势曲线。</div>';
    } else {
      const width = 440;
      const height = 176;
      const left = 32;
      const right = 14;
      const top = 16;
      const bottom = 50;
      const plotW = width - left - right;
      const plotH = height - top - bottom;

      const weights = data.map(function (item) { return item.weight; });
      const max = Math.max.apply(null, weights);
      const min = Math.min.apply(null, weights);
      const span = Math.max(1, max - min);

      function xFor(index) {
        return left + plotW * index / (data.length - 1);
      }

      function yFor(weight) {
        return top + plotH * (1 - (weight - min) / span);
      }

      let svg = '<svg viewBox="0 0 ' + width + ' ' + height + '">';

      // 最高 / 中间 / 最低三条参考线
      [max, (max + min) / 2, min].forEach(function (value, index) {
        const y = yFor(value).toFixed(1);
        svg += '<line x1="' + left + '" y1="' + y + '" x2="' + (width - right) + '" y2="' + y +
          '" stroke="#e9dfd2" stroke-width="1"' +
          (index === 1 ? ' stroke-dasharray="3 3"' : '') + '/>';
        svg += '<text x="4" y="' + (Number(y) + 3).toFixed(1) + '">' + value.toFixed(1) + '</text>';
      });

      const points = data.map(function (item, index) {
        return xFor(index).toFixed(1) + ',' + yFor(item.weight).toFixed(1);
      }).join(' ');

      svg += '<polyline points="' + points + '" fill="none" stroke="#8b4a22" stroke-width="2" ' +
        'stroke-linejoin="round" stroke-linecap="round"/>';

      data.forEach(function (item, index) {
        svg += '<circle cx="' + xFor(index).toFixed(1) + '" cy="' + yFor(item.weight).toFixed(1) +
          '" r="3" fill="#fff" stroke="#8b4a22" stroke-width="1.6"/>';
      });

      // 每个折点下方标注对应日期（旋转 45°，避免重叠）
      data.forEach(function (item, index) {
        const cx = xFor(index);
        const labelY = height - 30;
        svg += '<text x="' + cx.toFixed(1) + '" y="' + labelY +
          '" text-anchor="end" transform="rotate(-45 ' + cx.toFixed(1) + ' ' + labelY + ')" ' +
          'font-size="8" fill="#a08d7d">' + item.date.slice(5) + '</text>';
      });
      svg += '</svg>';

      html = head + svg;
    }
  }

  boxes.forEach(function (box) {
    box.innerHTML = html;
  });
}

// ---------- 饮食：食物营养估算 ----------
// 说明：按常见食物给出每人份的估算值，用户可直接输入食物名称记录
const nutritionTable = [
  { keys: ['米饭', '白饭'], name: '米饭', portion: '1 碗 ≈ 150g', kcal: 230, protein: 4, carb: 50, fat: 1, fiber: 1 },
  { keys: ['面条', '拉面', '意面', '米粉', '馄饨', '饺子'], name: '面食', portion: '1 碗 ≈ 200g', kcal: 280, protein: 8, carb: 55, fat: 3, fiber: 2 },
  { keys: ['鸡蛋', '水煮蛋', '煎蛋', '蛋花'], name: '鸡蛋', portion: '1 个 ≈ 50g', kcal: 140, protein: 12, carb: 1, fat: 10, fiber: 0 },
  { keys: ['牛奶', '酸奶'], name: '奶制品', portion: '1 杯 ≈ 250ml', kcal: 130, protein: 8, carb: 12, fat: 5, fiber: 0 },
  { keys: ['鸡胸', '鸡肉', '瘦肉', '牛肉', '排骨'], name: '瘦肉', portion: '1 份 ≈ 100g', kcal: 165, protein: 25, carb: 0, fat: 6, fiber: 0 },
  { keys: ['鱼', '虾'], name: '鱼虾', portion: '1 份 ≈ 100g', kcal: 120, protein: 20, carb: 0, fat: 4, fiber: 0 },
  { keys: ['豆腐', '豆浆', '豆制品', '黄豆'], name: '豆制品', portion: '1 份 ≈ 100g', kcal: 110, protein: 10, carb: 6, fat: 5, fiber: 2 },
  { keys: ['蔬菜', '青菜', '西兰花', '菠菜', '沙拉', '生菜', '番茄', '黄瓜', '蘑菇'], name: '蔬菜', portion: '1 份 ≈ 150g', kcal: 80, protein: 4, carb: 10, fat: 2, fiber: 5 },
  { keys: ['水果', '苹果', '香蕉', '蓝莓', '橙', '葡萄', '西瓜'], name: '水果', portion: '1 份 ≈ 150g', kcal: 90, protein: 1, carb: 22, fat: 1, fiber: 3 },
  { keys: ['面包', '吐司'], name: '全麦面包', portion: '2 片 ≈ 60g', kcal: 180, protein: 7, carb: 30, fat: 3, fiber: 4 },
  { keys: ['燕麦', '粥'], name: '燕麦粥', portion: '1 碗 ≈ 250g', kcal: 160, protein: 6, carb: 27, fat: 3, fiber: 4 },
  { keys: ['坚果', '花生', '核桃'], name: '坚果', portion: '1 小把 ≈ 25g', kcal: 180, protein: 5, carb: 6, fat: 15, fiber: 2 },
  { keys: ['汉堡', '炸鸡', '薯条', '披萨'], name: '快餐', portion: '1 份（汉堡+薯条）', kcal: 550, protein: 20, carb: 50, fat: 28, fiber: 3 },
  { keys: ['奶茶', '可乐', '蛋糕', '甜品', '冰淇淋'], name: '含糖饮品 / 甜点', portion: '1 杯 / 1 块 ≈ 500ml / 100g', kcal: 300, protein: 3, carb: 45, fat: 10, fiber: 0 },
  { keys: ['咖啡'], name: '咖啡', portion: '1 杯 ≈ 250ml', kcal: 20, protein: 1, carb: 3, fat: 0, fiber: 0 }
];

const defaultNutrition = { kcal: 150, protein: 6, carb: 20, fat: 5, fiber: 2 };

// 根据输入文字匹配食物，未匹配到则按普通一餐估算
function estimateNutrition(text) {
  const result = { kcal: 0, protein: 0, carb: 0, fat: 0, fiber: 0 };
  let matched = 0;

  nutritionTable.forEach(function (food) {
    const hit = food.keys.some(function (key) {
      return text.indexOf(key) !== -1;
    });
    if (!hit) return;

    result.kcal += food.kcal;
    result.protein += food.protein;
    result.carb += food.carb;
    result.fat += food.fat;
    result.fiber += food.fiber;
    matched += 1;
  });

  if (!matched) {
    result.kcal = defaultNutrition.kcal;
    result.protein = defaultNutrition.protein;
    result.carb = defaultNutrition.carb;
    result.fat = defaultNutrition.fat;
    result.fiber = defaultNutrition.fiber;
  }
  return result;
}

// ---------- 饮食记录（保留最近 30 天，支持两周对比） ----------
let mealLog = loadData('mealLog', []);

function saveMealRecord(meal, text, nutrition) {
  mealLog.push({
    date: toISODate(new Date()),
    meal: meal,
    text: text,
    kcal: nutrition.kcal,
    protein: nutrition.protein,
    carb: nutrition.carb,
    fat: nutrition.fat,
    fiber: nutrition.fiber
  });

  // 只保留最近 30 天，避免数据无限增长
  const cutoff = toISODate(addDays(new Date(), -30));
  mealLog = mealLog.filter(function (item) {
    return item.date >= cutoff;
  });
  saveData('mealLog', mealLog);

  renderMealLog();
  refreshDietViews();
}

function recordMealEntry(meal, rawText) {
  const text = (rawText || '').trim();
  if (!text) return;
  saveMealRecord(meal, text, estimateNutrition(text));
  showToast('已记录' + meal + '：' + text);
}

// ---------- 输入食物后弹出分量参考弹窗 ----------
const foodMask = document.getElementById('foodMask');
const foodCountInput = document.getElementById('foodCount');
let pendingMeal = null;

// 根据输入文字匹配食物库
function matchFoods(text) {
  return nutritionTable.filter(function (food) {
    return food.keys.some(function (key) {
      return text.indexOf(key) !== -1;
    });
  });
}

function sumFoodNutrition(foods) {
  return foods.reduce(function (total, food) {
    return {
      kcal: total.kcal + food.kcal,
      protein: total.protein + food.protein,
      carb: total.carb + food.carb,
      fat: total.fat + food.fat,
      fiber: total.fiber + food.fiber
    };
  }, { kcal: 0, protein: 0, carb: 0, fat: 0, fiber: 0 });
}

function foodCountValue() {
  return parseFloat(foodCountInput.value) || 0;
}

function updateFoodTotal() {
  const box = document.getElementById('foodTotal');
  if (!pendingMeal) return;

  const count = foodCountValue();
  if (count < 0.25 || count > 10) {
    box.textContent = '份数需在 0.25～10 之间，例如半碗填 0.5。';
    return;
  }

  const total = sumFoodNutrition(pendingMeal.matches);
  box.textContent = '按 ' + count + ' 份计算：约 ' + Math.round(total.kcal * count) + ' kcal，' +
    '蛋白质 ' + (total.protein * count).toFixed(1) + 'g，碳水 ' + (total.carb * count).toFixed(0) +
    'g，脂肪 ' + (total.fat * count).toFixed(1) + 'g。';
}

// 输入食物后先校验是否为常见食物，再弹出分量参考
function requestMealRecord(meal, rawText, input) {
  const text = (rawText || '').trim();
  if (!text) {
    showToast('请先输入吃了什么，例如：米饭 鸡胸肉 西兰花');
    return;
  }

  const matches = matchFoods(text);
  if (!matches.length) {
    showToast('「' + text + '」不在常见食物库中，请按“食物名 + 分量”输入，例如：米饭 150g、牛奶 1 杯');
    return;
  }

  pendingMeal = { meal: meal, text: text, input: input, matches: matches };
  document.getElementById('foodSummary').textContent =
    '本餐识别到 ' + matches.length + ' 种食物：' + matches.map(function (food) {
      return food.name;
    }).join('、');

  document.getElementById('foodPortions').innerHTML = matches.map(function (food) {
    return '<div class="food-portion-row"><span>' + food.name + ' · 参考分量 ' + food.portion +
      '</span><b>' + food.kcal + ' kcal / 份</b></div>';
  }).join('');

  foodCountInput.value = 1;
  updateFoodTotal();
  openMask(foodMask);
}

foodCountInput.addEventListener('input', updateFoodTotal);

document.getElementById('foodClose').addEventListener('click', function () {
  closeMask(foodMask);
});

document.getElementById('foodCancel').addEventListener('click', function () {
  closeMask(foodMask);
});

foodMask.addEventListener('click', function (event) {
  if (event.target === foodMask) closeMask(foodMask);
});

document.getElementById('foodSave').addEventListener('click', function () {
  if (!pendingMeal) return;

  const count = foodCountValue();
  if (count < 0.25 || count > 10) {
    showToast('份数需在 0.25～10 之间');
    return;
  }

  const base = sumFoodNutrition(pendingMeal.matches);
  const label = pendingMeal.text + (count !== 1 ? '（' + count + ' 份）' : '');

  saveMealRecord(pendingMeal.meal, label, {
    kcal: base.kcal * count,
    protein: base.protein * count,
    carb: base.carb * count,
    fat: base.fat * count,
    fiber: base.fiber * count
  });

  if (pendingMeal.input) pendingMeal.input.value = '';
  const meal = pendingMeal.meal;
  pendingMeal = null;
  closeMask(foodMask);
  showToast('已记录' + meal + '：' + label);
});

function renderMealLog() {
  const box = document.getElementById('mealLog');
  if (!box) return;
  box.innerHTML = '';

  const today = toISODate(new Date());
  const items = mealLog.filter(function (item) { return item.date === today; });

  if (!items.length) {
    box.innerHTML = '<div class="meal-log-empty">今天还没有记录，在上面的早餐 / 午餐 / 晚餐输入框输入食物后按回车即可添加。</div>';
    return;
  }

  items.forEach(function (item) {
    const chip = document.createElement('span');
    chip.className = 'meal-log-item';
    chip.textContent = item.meal + ' · ' + item.text + '（约 ' + Math.round(item.kcal) + ' kcal）';

    const del = document.createElement('button');
    del.type = 'button';
    del.textContent = '×';
    del.title = '删除这条记录';
    del.addEventListener('click', function () {
      const index = mealLog.indexOf(item);
      if (index === -1) return;
      mealLog.splice(index, 1);
      saveData('mealLog', mealLog);
      renderMealLog();
      refreshDietViews();
      showToast('已删除这条饮食记录');
    });

    chip.appendChild(del);
    box.appendChild(chip);
  });
}

// 当前体重：优先取最近一次体重记录，其次取个人档案
function getCurrentWeight() {
  if (weightHistory.length) {
    return weightHistory[weightHistory.length - 1].weight;
  }
  return parseFloat(document.getElementById('pWeight').value) || 65;
}

// 活动水平由用户在下拉框中选择，不再由系统擅自推测运动量
function getActivityFactor() {
  const select = document.getElementById('dietActivity');
  const factor = select ? (parseFloat(select.value) || 1.375) : 1.375;

  let proteinPerKg = 1.2;
  if (factor >= 1.7) proteinPerKg = 1.6;
  else if (factor >= 1.55) proteinPerKg = 1.5;
  else if (factor >= 1.375) proteinPerKg = 1.35;

  return { factor: factor, proteinPerKg: proteinPerKg };
}

// 按个人资料 + 体重变化 + 运动量计算每日营养目标（Mifflin-St Jeor，年龄按 22 岁估算）
function getNutritionTargets() {
  const weight = getCurrentWeight();
  const height = parseFloat(document.getElementById('pHeight').value) || 165;
  const gender = document.getElementById('pGender').value || '女';
  const activity = getActivityFactor();

  const bmr = gender === '男'
    ? 10 * weight + 6.25 * height - 5 * 22 + 5
    : 10 * weight + 6.25 * height - 5 * 22 - 161;
  const kcal = Math.round(bmr * activity.factor / 10) * 10;

  return {
    kcal: kcal,
    bmr: Math.round(bmr),
    activity: activity.factor,
    protein: Math.round(weight * activity.proteinPerKg),
    carb: Math.round(kcal * 0.5 / 4),
    fat: Math.round(weight * 0.8),
    fiber: 25
  };
}

/* ---------- 顶部三项评分：随饮食、运动、体重数据自动更新 ---------- */
// 单项达成度：落在目标的 80%-120% 记满分，偏离越多扣分越多
function ratioScore(value, target) {
  if (!target) return 0;
  const ratio = value / target;

  if (ratio >= 0.8 && ratio <= 1.2) return 100;
  if (ratio < 0.8) return Math.max(0, ratio / 0.8 * 100);
  return Math.max(0, 100 - (ratio - 1.2) * 150);
}

// 饮食评分：取近 7 天有记录日期的平均达成度，没有记录则为 0
function computeDietScore() {
  const targets = getNutritionTargets();
  const today = new Date();
  let sum = 0;
  let days = 0;

  for (let offset = 0; offset < 7; offset++) {
    const key = toISODate(addDays(today, -offset));
    const day = dateRangeSum(key, key);
    if (!day.days) continue;

    sum += (ratioScore(day.total.protein, targets.protein) +
      ratioScore(day.total.carb, targets.carb) +
      ratioScore(day.total.fiber, targets.fiber) +
      ratioScore(day.total.fat, targets.fat) +
      ratioScore(day.total.kcal, targets.kcal)) / 5;
    days += 1;
  }

  return days ? Math.round(sum / days) : 0;
}

// 运动评分：今日目标完成率
function computeSportScore() {
  return sportPercent(todaySport(), sportState.goal);
}

// BMI 评分：正常区间满分，偏瘦 / 超重按程度扣分
function computeBmiScore() {
  const height = (parseFloat(document.getElementById('pHeight').value) || 165) / 100;
  const bmi = getCurrentWeight() / (height * height);

  if (bmi >= 18.5 && bmi < 24) return 100;
  if (bmi >= 24 && bmi < 28) return 80;
  if (bmi >= 17 && bmi < 18.5) return 75;
  return 60;
}

function setScore(id, value) {
  const num = Math.max(0, Math.min(100, Math.round(value)));
  const textEl = document.getElementById(id);
  const barEl = document.getElementById(id + 'Bar');
  if (textEl) textEl.textContent = num;
  if (barEl) barEl.style.width = num + '%';
}

function updateScores() {
  const diet = computeDietScore();
  const sport = computeSportScore();
  const bmi = computeBmiScore();
  const total = diet * 0.4 + sport * 0.4 + bmi * 0.2;

  setScore('scoreDiet', diet);
  setScore('scoreSport', sport);
  setScore('scoreTotal', total);

  // 核心体征右侧环形评分同步
  const ringScore = document.getElementById('ringScore');
  const ringArc = document.getElementById('ringArc');
  if (ringScore) ringScore.textContent = Math.round(total) + '%';
  if (ringArc) {
    const circumference = 2 * Math.PI * 52;
    ringArc.setAttribute('stroke-dashoffset',
      (circumference * (1 - total / 100)).toFixed(1));
  }
}

// ---------- 点击顶部评分查看分析与建议 ----------
const scoreMask = document.getElementById('scoreMask');

function scoreLevelText(value) {
  if (value >= 85) return '优秀';
  if (value >= 70) return '良好';
  if (value >= 60) return '一般';
  return '待改善';
}

function listHtml(items) {
  return '<ul>' + items.map(function (item) {
    return '<li>' + item + '</li>';
  }).join('') + '</ul>';
}

function buildDietAnalysis() {
  const targets = getNutritionTargets();
  const today = toISODate(new Date());
  const eaten = dateRangeSum(today, today);
  const weekStart = toISODate(addDays(new Date(), -6));
  const week = dateRangeSum(weekStart, today);

  if (!eaten.days) {
    return '<p>今天还没有饮食记录，暂时无法评估具体营养摄入。</p>' +
      '<p>建议先记录早餐、午餐或晚餐，评分和本页分析会随记录自动更新。</p>';
  }

  const html = ['<p>今天摄入约 ' + Math.round(eaten.total.kcal) + ' kcal（目标 ' + targets.kcal +
    ' kcal），蛋白质 ' + Math.round(eaten.total.protein) + 'g（目标 ' + targets.protein +
    'g），膳食纤维 ' + Math.round(eaten.total.fiber) + 'g（目标 ' + targets.fiber + 'g）。</p>'];

  const items = [];
  if (eaten.total.protein < targets.protein * 0.8) {
    items.push('蛋白质不足，建议增加鸡蛋、鱼虾、鸡胸肉或豆制品。');
  }
  if (eaten.total.fiber < targets.fiber * 0.6) {
    items.push('膳食纤维偏少，建议补充两份深色蔬菜和一份水果。');
  }
  if (eaten.total.kcal > targets.kcal * 1.15) {
    items.push('热量已超出目标，晚餐宜清淡，减少油炸与含糖饮料。');
  }
  if (eaten.total.carb < targets.carb * 0.6) {
    items.push('碳水化合物偏低，可适量补充糙米、燕麦或红薯。');
  }
  if (!items.length) {
    items.push('主要营养指标基本达标，继续保持规律三餐与足量饮水。');
  }

  html.push('<h4>本日评估</h4>' + listHtml(items));
  if (week.days) {
    html.push('<h4>近 7 天</h4><p>共记录 ' + week.days + ' 天，平均每日约 ' +
      Math.round(week.total.kcal / week.days) + ' kcal，平均蛋白质 ' +
      Math.round(week.total.protein / week.days) + 'g。</p>');
  }

  return html.join('');
}

function buildSportAnalysis() {
  const actual = todaySport();
  const goal = sportState.goal;
  const percent = computeSportScore();
  const week = weekSport();

  const html = ['<p>今日完成度 ' + percent + '%：消耗 ' + Math.round(actual.kcal) +
    ' / ' + goal.kcal + ' kcal，步数 ' + formatNumber(actual.steps) + ' / ' +
    formatNumber(goal.steps) + '，运动时长 ' + Math.round(actual.minutes) +
    ' / ' + goal.minutes + ' 分钟。</p>'];

  const items = [];
  if (!actual.minutes) {
    items.push('今天还没有运动记录，可以先从 20 分钟快走或拉伸开始。');
  }
  if (percent < 60) {
    items.push('距离目标还有差距，建议增加一次 20-30 分钟中等强度运动。');
  }
  if (actual.steps < goal.steps * 0.6) {
    items.push('步数偏少，可以把通勤中的一段路改为步行。');
  }
  if (actual.minutes > goal.minutes * 1.5) {
    items.push('今天运动量较大，注意补水与拉伸，避免连续高强度训练。');
  }
  if (!items.length) {
    items.push('今日目标完成良好，保持每周 3-5 次中等强度运动即可。');
  }

  html.push('<h4>评估与建议</h4>' + listHtml(items));
  html.push('<h4>本周累计</h4><p>消耗 ' + Math.round(week.kcal) + ' kcal，步数 ' +
    formatNumber(week.steps) + '，运动 ' + Math.round(week.minutes) + ' 分钟。</p>');

  return html.join('');
}

function buildTotalAnalysis() {
  const diet = computeDietScore();
  const sport = computeSportScore();
  const bmi = computeBmiScore();
  const weight = getCurrentWeight();
  const height = currentHeightMeters();
  const bmiValue = weight / (height * height);

  const html = ['<p>综合评分 = 饮食 40% + 运动 40% + BMI 20%。当前：饮食 ' + diet +
    ' 分、运动 ' + sport + ' 分、BMI ' + bmi + ' 分（' + bmiValue.toFixed(1) + '）。</p>'];

  const items = [];
  if (diet < 60) items.push('饮食评分偏低：优先补足蛋白质与蔬菜，减少含糖饮料。');
  if (sport < 60) items.push('运动评分偏低：先把每日步数提升到目标的一半，再逐步增加时长。');
  if (bmi < 100 && bmiValue >= 24) items.push('BMI 偏高：建议每周 150 分钟中等强度有氧，并控制精制碳水。');
  if (bmi < 100 && bmiValue < 18.5) items.push('BMI 偏低：适当增加优质蛋白与主食，配合力量训练。');
  if (!items.length) items.push('各项指标都在良好区间，保持当前作息和运动频率即可。');

  html.push('<h4>优先改善</h4>' + listHtml(items));
  return html.join('');
}

function openScoreModal(type) {
  const values = {
    total: Number(document.getElementById('scoreTotal').textContent),
    diet: computeDietScore(),
    sport: computeSportScore()
  };
  const titles = {
    total: '综合健康评分分析',
    diet: '饮食健康评分分析',
    sport: '运动完成评分分析'
  };
  const bodies = {
    total: buildTotalAnalysis,
    diet: buildDietAnalysis,
    sport: buildSportAnalysis
  };

  const value = values[type];
  document.getElementById('scoreModalTitle').textContent = titles[type];
  document.getElementById('scoreModalValue').textContent = value;
  document.getElementById('scoreModalLevel').textContent = scoreLevelText(value);
  document.getElementById('scoreModalBody').innerHTML = bodies[type]();
  openMask(scoreMask);
}

document.querySelectorAll('.score[data-score]').forEach(function (item) {
  item.addEventListener('click', function () {
    openScoreModal(item.dataset.score);
  });
});

document.getElementById('scoreClose').addEventListener('click', function () {
  closeMask(scoreMask);
});

scoreMask.addEventListener('click', function (event) {
  if (event.target === scoreMask) closeMask(scoreMask);
});

// 统计某个日期区间的营养合计与记录天数
function dateRangeSum(startStr, endStr) {
  const total = { kcal: 0, protein: 0, carb: 0, fat: 0, fiber: 0 };
  const days = {};

  mealLog.forEach(function (item) {
    if (item.date < startStr || item.date > endStr) return;
    total.kcal += item.kcal;
    total.protein += item.protein;
    total.carb += item.carb;
    total.fat += item.fat;
    total.fiber += item.fiber;
    days[item.date] = true;
  });

  return { total: total, days: Object.keys(days).length };
}

function renderNutrition() {
  const targets = getNutritionTargets();
  const today = toISODate(new Date());
  const eaten = dateRangeSum(today, today).total;

  document.getElementById('macroProtein').textContent = Math.round(eaten.protein) + '/' + targets.protein + 'g';
  document.getElementById('macroCarb').textContent = Math.round(eaten.carb) + '/' + targets.carb + 'g';
  document.getElementById('macroFiber').textContent = Math.round(eaten.fiber) + '/' + targets.fiber + 'g';
  document.getElementById('macroFat').textContent = Math.round(eaten.fat) + '/' + targets.fat + 'g';
  document.getElementById('macroKcal').textContent = Math.round(eaten.kcal) + '/' + targets.kcal + 'k';

  const rows = [
    { label: '蛋白质', value: eaten.protein, target: targets.protein, unit: 'g' },
    { label: '碳水化合物', value: eaten.carb, target: targets.carb, unit: 'g' },
    { label: '膳食纤维', value: eaten.fiber, target: targets.fiber, unit: 'g' },
    { label: '脂肪', value: eaten.fat, target: targets.fat, unit: 'g' },
    { label: '总热量', value: eaten.kcal, target: targets.kcal, unit: 'kcal' }
  ];

  const box = document.getElementById('nutriList');
  box.innerHTML = '';

  rows.forEach(function (row) {
    const percent = row.target ? Math.min(100, row.value / row.target * 100) : 0;
    const item = document.createElement('div');
    item.innerHTML =
      '<div class="nutri-head"><span>' + row.label + '</span><span><b>' +
      Math.round(row.value) + '</b> / ' + row.target + ' ' + row.unit + '</span></div>' +
      '<div class="nutri-bar' + (percent >= 100 ? ' over' : '') +
      '"><i style="width:' + percent.toFixed(1) + '%"></i></div>';
    box.appendChild(item);
  });

  // 把计算依据写清楚，避免“为什么体重一改热量就变”的困惑
  const note = document.getElementById('nutriNote');
  if (note) {
    note.textContent = '计算依据：基础代谢 ' + targets.bmr + ' kcal × 活动系数 ' + targets.activity +
      ' ≈ ' + targets.kcal + ' kcal（Mifflin-St Jeor 公式）；蛋白质 ' + targets.protein +
      'g、脂肪 ' + targets.fat + 'g 按当前体重 ' + getCurrentWeight().toFixed(1) +
      'kg 计算。体重变化会改变基础代谢，所以目标值会随之调整。';
  }
}

// 蛋白质达标天数（达到目标的 80%）
function countProteinDays(startStr, endStr, target) {
  const byDate = {};

  mealLog.forEach(function (item) {
    if (item.date < startStr || item.date > endStr) return;
    byDate[item.date] = (byDate[item.date] || 0) + item.protein;
  });

  return Object.keys(byDate).filter(function (date) {
    return byDate[date] >= target * 0.8;
  }).length;
}

// 蔬果记录次数
function countVegFruit(startStr, endStr) {
  const keys = ['蔬菜', '青菜', '西兰花', '菠菜', '沙拉', '生菜', '水果', '苹果', '香蕉', '蓝莓', '橙'];
  return mealLog.filter(function (item) {
    if (item.date < startStr || item.date > endStr) return false;
    return keys.some(function (key) { return item.text.indexOf(key) !== -1; });
  }).length;
}

// 本周 vs 上周对比
function renderWeekCompare() {
  const box = document.getElementById('weekCompare');
  if (!box) return;

  const today = new Date();
  const todayStr = toISODate(today);
  const thisStart = toISODate(addDays(today, -6));
  const lastEnd = toISODate(addDays(today, -7));
  const lastStart = toISODate(addDays(today, -13));

  const current = dateRangeSum(thisStart, todayStr);
  const previous = dateRangeSum(lastStart, lastEnd);
  const targets = getNutritionTargets();

  const curAvgKcal = current.days ? current.total.kcal / current.days : 0;
  const prevAvgKcal = previous.days ? previous.total.kcal / previous.days : 0;
  const curAvgProtein = current.days ? current.total.protein / current.days : 0;
  const prevAvgProtein = previous.days ? previous.total.protein / previous.days : 0;
  const curHit = countProteinDays(thisStart, todayStr, targets.protein);
  const prevHit = countProteinDays(lastStart, lastEnd, targets.protein);
  const curVeg = countVegFruit(thisStart, todayStr);
  const prevVeg = countVegFruit(lastStart, lastEnd);

  function diffCell(value, unit) {
    if (!value) return '<td>持平</td>';
    const cls = value > 0 ? 'up' : 'down';
    const sign = value > 0 ? '+' : '';
    return '<td class="' + cls + '">' + sign + Math.round(value) + ' ' + unit + '</td>';
  }

  let html = '<table><thead><tr><th>指标</th><th>本周</th><th>上周</th><th>变化</th></tr></thead><tbody>';
  html += '<tr><td>平均每日热量</td><td>' + Math.round(curAvgKcal) + ' kcal</td><td>' +
    Math.round(prevAvgKcal) + ' kcal</td>' + diffCell(curAvgKcal - prevAvgKcal, 'kcal') + '</tr>';
  html += '<tr><td>平均每日蛋白质</td><td>' + Math.round(curAvgProtein) + ' g</td><td>' +
    Math.round(prevAvgProtein) + ' g</td>' + diffCell(curAvgProtein - prevAvgProtein, 'g') + '</tr>';
  html += '<tr><td>蛋白质达标天数</td><td>' + curHit + ' 天</td><td>' + prevHit + ' 天</td>' +
    diffCell(curHit - prevHit, '天') + '</tr>';
  html += '<tr><td>蔬果记录次数</td><td>' + curVeg + ' 次</td><td>' + prevVeg + ' 次</td>' +
    diffCell(curVeg - prevVeg, '次') + '</tr>';
  html += '<tr><td>有记录天数</td><td>' + current.days + ' 天</td><td>' + previous.days + ' 天</td>' +
    diffCell(current.days - previous.days, '天') + '</tr>';
  html += '</tbody></table>';

  // 近 7 天热量柱状图
  const days = [];
  for (let offset = 6; offset >= 0; offset--) {
    const day = addDays(today, -offset);
    const key = toISODate(day);
    days.push({
      label: (day.getMonth() + 1) + '/' + day.getDate(),
      kcal: dateRangeSum(key, key).total.kcal
    });
  }

  const maxKcal = Math.max.apply(null, days.map(function (day) {
    return day.kcal;
  }).concat([targets.kcal, 1]));

  html += '<div class="mini-bars">';
  days.forEach(function (day) {
    const height = day.kcal ? Math.max(4, Math.round(day.kcal / maxKcal * 64)) : 4;
    html += '<div class="mini-bar"><em>' + (day.kcal ? Math.round(day.kcal) : '') +
      '</em><i style="height:' + height + 'px"></i><span>' + day.label + '</span></div>';
  });
  html += '</div>';

  box.innerHTML = html;
}

// 根据今日摄入自动生成建议
function buildDietAdvice() {
  const targets = getNutritionTargets();
  const today = toISODate(new Date());
  const eaten = dateRangeSum(today, today);

  if (!eaten.days) {
    return '今天还没有饮食记录。输入早餐、午餐或晚餐后按回车，系统会自动估算营养并给出建议。';
  }

  const tips = [];
  if (eaten.total.protein < targets.protein * 0.8) {
    tips.push('蛋白质还差约 ' + Math.round(targets.protein - eaten.total.protein) +
      'g，晚餐可以加一份鸡胸肉、鱼虾或豆腐。');
  }
  if (eaten.total.fiber < targets.fiber * 0.6) {
    tips.push('膳食纤维不足，建议再增加两份深色蔬菜和一份水果。');
  }
  if (eaten.total.kcal > targets.kcal * 1.15) {
    tips.push('今日热量已超出目标约 ' + Math.round(eaten.total.kcal - targets.kcal) +
      ' kcal，晚餐尽量清淡，少油少糖。');
  }
  if (eaten.total.carb < targets.carb * 0.6) {
    tips.push('碳水偏少可能影响精力，主食可以选择糙米、燕麦或红薯。');
  }

  // 结合运动与心情给出联动建议
  const sport = todaySport();
  if (sport.minutes > 0) {
    tips.push('今天已运动 ' + Math.round(sport.minutes) + ' 分钟，运动后 30 分钟内补充蛋白质和水分，更利于恢复。');
  }
  const mood = loadData('moodLog', {})[today];
  if (mood && (mood.mood === '疲惫' || mood.mood === '焦虑' || mood.mood === '低落')) {
    tips.push('今天心情偏' + mood.mood + '，晚餐尽量清淡，睡前拉伸 10 分钟并提前休息。');
  }

  if (!tips.length) {
    tips.push('今天的营养搭配比较均衡，注意多喝水、规律作息，继续保持。');
  }
  return tips.join('');
}

function refreshDietViews() {
  renderNutrition();
  renderWeekCompare();
  document.getElementById('dietTipText').textContent = buildDietAdvice();
  // 营养目标变化也会影响顶部评分
  updateScores();
}

// ---------- 科学变美：按计划类型推荐饮食种类 ----------
const beautyDietTips = {
  '健身减脂': [
    '优质蛋白：鸡胸肉、鱼虾、鸡蛋、无糖酸奶、豆腐，每餐一掌心',
    '复合碳水：糙米、燕麦、玉米、红薯，每餐一拳大小',
    '高纤维蔬菜：西兰花、菠菜、生菜、彩椒，每餐两拳',
    '低糖水果：苹果、蓝莓、猕猴桃，每日 200-350g',
    '少油少糖：以蒸煮为主，减少奶茶、油炸食品和夜宵'
  ],
  '增肌塑形': [
    '蛋白质加量：每日约 1.5-1.8g/kg 体重，分 4-5 餐摄入',
    '训练后 30 分钟内补充：乳清蛋白或牛奶 + 香蕉',
    '主食充足：燕麦、米饭、全麦面包，保证训练能量',
    '健康脂肪：坚果、牛油果、深海鱼',
    '补钙与维生素 D：牛奶、酸奶、蛋黄、深绿叶菜'
  ],
  '体态改善': [
    '足量蛋白：鸡蛋、豆制品、鱼肉，维持肌肉量',
    '钙 + 维生素 D：牛奶 300ml/天、豆制品、深绿叶菜',
    '抗氧化蔬果：番茄、彩椒、蓝莓、橙子',
    '少盐少钠：减少腌制食品，帮助减轻水肿',
    '规律三餐，避免长时间空腹或暴饮暴食'
  ],
  '提升体能': [
    '复合碳水：燕麦、糙米、全麦面包，训练前 1-2 小时补充',
    '优质蛋白：鸡胸肉、鱼虾、鸡蛋，训练后 30 分钟内补充',
    '补铁食物：瘦牛肉、猪肝、菠菜，搭配维 C 促进吸收',
    '充足饮水：运动前后各 200-300ml，出汗多时补充电解质',
    '少油少糖，避免训练前吃太饱'
  ],
  '缓解压力': [
    '富含镁的食物：香蕉、坚果、深绿叶菜，有助放松神经',
    '优质蛋白与复合碳水搭配，稳定血糖和情绪',
    '减少咖啡因与酒精，尤其下午之后',
    '规律进食，避免情绪性暴食',
    '多喝水，少量多次'
  ],
  '改善睡眠': [
    '晚餐清淡，睡前 2-3 小时不再进食',
    '助眠食物：牛奶、香蕉、燕麦、小米粥',
    '避免睡前咖啡、浓茶、酒精',
    '白天保证足够日照与活动量',
    '睡前可喝一小杯温牛奶'
  ],
  '经期舒缓': [
    '补铁：瘦红肉、动物肝脏、菠菜，搭配橙子等维 C 食物',
    '温热食物为主，减少生冷、冰饮',
    '适量补充钙与镁：牛奶、豆制品、坚果',
    '少盐，减轻水肿与腹胀',
    '少量多餐，避免空腹时间过长'
  ]
};

function renderBeautyDietTip(type) {
  const box = document.getElementById('beautyDietTip');
  if (!box) return;

  const tips = beautyDietTips[type] || beautyDietTips['健身减脂'];
  box.innerHTML = '<b>推荐饮食种类 · ' + type + '</b><ul>' +
    tips.map(function (tip) { return '<li>' + tip + '</li>'; }).join('') + '</ul>';
  box.hidden = false;
}

// ---------- 每日心情与小贴士 ----------
const moodTips = {
  '开心': '好心情值得被记住：把让你开心的事写下来，低落时回看会很有力量。也别忘了保持规律作息和运动，让好状态延续。',
  '平静': '平稳的一天适合做长期有益的事：散步 20 分钟、拉伸肩颈，或者比平时提前半小时入睡。',
  '疲惫': '身体在提醒你需要恢复。今晚尽量提前 30 分钟休息，睡前少看手机；明天把剧烈运动换成散步或拉伸。',
  '焦虑': '试试 4-7-8 呼吸法：吸气 4 秒、屏息 7 秒、呼气 8 秒，重复 4 轮。把担心的事写成清单，只处理今天能做的第一件。',
  '低落': '允许自己慢下来，先做一件很小的事（喝水、洗脸、出门走 5 分钟）。如果低落持续两周以上，建议寻求专业心理支持。'
};

let currentMood = '';

document.querySelectorAll('#moodPicker .mood-opt').forEach(function (btn) {
  btn.addEventListener('click', function () {
    currentMood = btn.dataset.mood;
    document.querySelectorAll('#moodPicker .mood-opt').forEach(function (item) {
      item.classList.toggle('selected', item === btn);
    });
    document.getElementById('moodTip').textContent = moodTips[currentMood];
  });
});

document.getElementById('saveMood').addEventListener('click', function () {
  if (!currentMood) {
    showToast('请先选择今天的心情');
    return;
  }

  const log = loadData('moodLog', {});
  log[toISODate(new Date())] = {
    mood: currentMood,
    note: document.getElementById('moodNote').value.trim()
  };
  saveData('moodLog', log);
  document.getElementById('moodTip').textContent = moodTips[currentMood];
  renderMoodWeek();
  renderWeekPanel();
  showToast('今日心情已保存：' + currentMood);
});

// 回显今天已保存的心情
const savedMood = loadData('moodLog', {})[toISODate(new Date())];
if (savedMood) {
  currentMood = savedMood.mood;
  document.getElementById('moodNote').value = savedMood.note || '';
  const moodBtn = document.querySelector('#moodPicker .mood-opt[data-mood="' + savedMood.mood + '"]');
  if (moodBtn) moodBtn.classList.add('selected');
  document.getElementById('moodTip').textContent = moodTips[savedMood.mood] || '';
}

// 一周心情记录：用表情展示，点击查看当天备注
function renderMoodWeek() {
  const box = document.getElementById('moodWeek');
  if (!box) return;

  const today = new Date();
  const monday = addDays(today, -((today.getDay() + 6) % 7));
  const log = loadData('moodLog', {});
  box.innerHTML = '';

  for (let index = 0; index < 7; index++) {
    const day = addDays(monday, index);
    const key = toISODate(day);
    const entry = log[key];

    const item = document.createElement('div');
    item.className = 'day' + (key === toISODate(today) ? ' selected' : '');
    item.innerHTML = '<span class="emoji">' + (entry ? moodEmojiOf(entry.mood) : '·') + '</span>' +
      '<span class="date">' + (day.getMonth() + 1) + '/' + day.getDate() + '</span>';
    item.title = entry ? (entry.mood + (entry.note ? '：' + entry.note : '')) : '未记录';

    item.addEventListener('click', function () {
      if (!entry) {
        showToast('这一天还没有心情记录');
        return;
      }
      document.getElementById('moodTip').textContent =
        entry.mood + '｜' + (entry.note || moodTips[entry.mood] || '');
    });

    box.appendChild(item);
  }
}

// ---------- 饮食活动水平：选择后立即重算目标 ----------
const dietActivity = document.getElementById('dietActivity');
const savedActivity = loadData('dietActivity', null);
if (savedActivity) dietActivity.value = String(savedActivity);

dietActivity.addEventListener('change', function () {
  saveData('dietActivity', parseFloat(dietActivity.value));
  refreshDietViews();
});

// ---------- 科普资讯：点击卡片查看正文 ----------
const newsArticles = {
  diet: {
    title: '如何科学搭配三餐饮食？',
    html: '<p>《中国居民膳食指南》建议，每天的食物应尽量覆盖谷薯类、蔬菜水果、畜禽鱼蛋奶和豆类四大类，平均每天摄入 12 种以上食物，每周 25 种以上。</p>' +
      '<h4>一、三餐怎么分配</h4>' +
      '<p>早餐占全天能量的 25%-30%，午餐 30%-40%，晚餐 30%-35%。早餐建议包含主食 + 蛋白质 + 蔬果，例如燕麦牛奶配一个鸡蛋和半个苹果。</p>' +
      '<h4>二、餐盘比例</h4>' +
      '<ul><li>一半是蔬菜和水果，深色蔬菜应占蔬菜总量的一半</li>' +
      '<li>四分之一是主食，优先选择全谷物、杂豆和薯类</li>' +
      '<li>四分之一是优质蛋白，鱼、禽、蛋、瘦肉、豆制品轮换</li></ul>' +
      '<h4>三、几个容易忽略的细节</h4>' +
      '<p>每天食盐不超过 5g，烹调油 25-30g，添加糖最好控制在 25g 以内。喝水 1500-1700ml，少喝含糖饮料。进食顺序上先吃蔬菜、再吃蛋白质、最后吃主食，有助于平稳餐后血糖。</p>' +
      '<p class="note">以上为一般人群的健康建议。若有慢性疾病或特殊饮食需求，请遵医嘱或咨询注册营养师。</p>'
  },
  stretch: {
    title: '久坐族的5分钟拉伸指南',
    html: '<p>连续久坐超过 60 分钟，肩颈和腰背的肌肉会持续处于紧张状态。每坐 45-60 分钟起身活动 3-5 分钟，比一次性长时间拉伸更有效。</p>' +
      '<h4>动作一：颈部侧屈（每侧 20 秒）</h4>' +
      '<p>坐直，右手轻扶头部左侧，缓慢向右侧倾斜，感受左侧颈部拉伸，不要耸肩，保持均匀呼吸后换另一侧。</p>' +
      '<h4>动作二：肩胛后缩（15 次）</h4>' +
      '<p>双臂自然下垂，肩胛骨向后向下收紧，像把两侧肩胛骨夹在一起，保持 2 秒再放松，可改善圆肩驼背。</p>' +
      '<h4>动作三：胸椎伸展（10 次）</h4>' +
      '<p>双手交叉抱头，手肘打开，缓慢向后仰 10-15 度，感受胸椎伸展，避免腰部代偿。</p>' +
      '<h4>动作四：站立体前屈（30 秒）</h4>' +
      '<p>双脚与髋同宽，膝盖微屈，身体缓慢前屈，双手自然下垂，放松腰背。起身时要慢，避免头晕。</p>' +
      '<p class="note">拉伸以轻微牵拉感为宜，出现明显疼痛应立即停止。有颈椎、腰椎疾病者请先咨询医生。</p>'
  },
  sleep: {
    title: '为什么你总是睡不够？',
    html: '<p>成年人建议每晚睡 7-9 小时，但“睡够时长”并不等于“睡得好”。一整夜会经历 4-6 个睡眠周期，每个周期包含浅睡、深睡和快速眼动睡眠。</p>' +
      '<h4>深睡决定恢复质量</h4>' +
      '<p>深睡阶段身体修复组织、分泌生长激素、巩固免疫记忆。频繁被打断、睡前饮酒、卧室过亮或过热，都会压缩深睡时间。</p>' +
      '<h4>四个可执行的改善方法</h4>' +
      '<ul><li>固定起床时间，比固定入睡时间更容易坚持</li>' +
      '<li>睡前一小时调暗灯光，减少手机等强光刺激</li>' +
      '<li>卧室温度保持在 18-22℃，保持安静与遮光</li>' +
      '<li>下午三点后避免咖啡、浓茶，睡前避免大量进食和饮酒</li></ul>' +
      '<h4>什么时候需要就医</h4>' +
      '<p>如果每周至少 3 晚入睡困难或早醒，持续 3 个月以上，或伴随明显打鼾、呼吸暂停、白天嗜睡，建议到睡眠专科就诊。</p>' +
      '<p class="note">本页内容为健康科普，不能替代医生的诊断与治疗。</p>'
  },
  bp: {
    title: '血压血糖，家庭自测怎么做才准？',
    html: '<p>家庭自测能反映日常状态，比诊室单次测量更有参考价值。建议固定在早晨起床后 1 小时内、排尿后、早餐和服药前测量。</p>' +
      '<h4>测血压的四个要点</h4>' +
      '<ul><li>测量前安静坐 5 分钟，不说话、不翘腿</li>' +
      '<li>袖带与心脏同高，手臂平放在桌面上</li>' +
      '<li>每次测 2-3 遍，间隔 1 分钟，取平均值</li>' +
      '<li>连续记录 7 天，去掉第一天，取后 6 天平均值</li></ul>' +
      '<p>家庭血压一般以低于 135/85 mmHg 为参考标准，具体目标应遵医嘱。</p>' +
      '<h4>测血糖的注意事项</h4>' +
      '<p>空腹血糖需空腹 8-10 小时；餐后 2 小时血糖从吃第一口饭开始计时。采血前用温水洗手并擦干，不要用力挤压指尖，以免组织液稀释血液影响结果。</p>' +
      '<h4>记录比单次数值更重要</h4>' +
      '<p>把日期、时间、数值和当时的状态（是否运动、是否服药）一起记录，复诊时医生才能判断趋势。若出现血压持续高于 180/110 mmHg，或血糖低于 3.9 mmol/L 伴心慌出汗，应及时就医。</p>' +
      '<p class="note">以上为健康科普内容，用药与治疗请遵循医生意见。</p>'
  }
};

const newsMask = document.getElementById('newsMask');

document.querySelectorAll('.news-card').forEach(function (card) {
  card.addEventListener('click', function () {
    const article = newsArticles[card.dataset.article];
    if (!article) return;

    document.getElementById('newsTitle').textContent = article.title;
    document.getElementById('newsBody').innerHTML = article.html;
    openMask(newsMask);
  });
});

document.getElementById('newsClose').addEventListener('click', function () {
  closeMask(newsMask);
});

newsMask.addEventListener('click', function (event) {
  if (event.target === newsMask) closeMask(newsMask);
});

// ---------- 科普资讯搜索：按标题、摘要与正文关键词过滤 ----------
const newsSearch = document.getElementById('newsSearch');

function filterNews() {
  const keyword = newsSearch.value.trim().toLowerCase();
  let visible = 0;

  document.querySelectorAll('.news-card').forEach(function (card) {
    const article = newsArticles[card.dataset.article];
    const text = (card.textContent + (article ? article.html : '')).toLowerCase();
    const matched = !keyword || text.indexOf(keyword) !== -1;

    card.style.display = matched ? '' : 'none';
    if (matched) visible += 1;
  });

  document.getElementById('newsCount').textContent = keyword ? '找到 ' + visible + ' 条' : '';
  document.getElementById('newsEmpty').hidden = visible > 0;
}

newsSearch.addEventListener('input', filterNews);

// ---------- 新功能初始化 ----------
loadProfileView();
renderVitalRanges();
renderMealLog();
refreshDietViews();
fillSportInputs();
renderExercise('today');
renderWeightChart();
renderMoodWeek();
renderWeekPanel();

/* ==========================================================
   七、AI 健康小管家聊天
   ========================================================== */
const chat = document.getElementById('chat');
const chatBody = document.getElementById('chatBody');
const chatInput = document.getElementById('chatInput');

function openChat() {
  chat.classList.add('open');
  document.getElementById('fabDot').style.display = 'none';
  chatInput.focus();
}

function closeChat() {
  chat.classList.remove('open');
}

function toggleChat() {
  if (chat.classList.contains('open')) {
    closeChat();
  } else {
    openChat();
  }
}

document.getElementById('fab').addEventListener('click', toggleChat);
document.getElementById('chatClose').addEventListener('click', closeChat);

// 追加一条聊天气泡
function addBubble(text, who) {
  const bubble = document.createElement('div');
  bubble.className = 'msg ' + who;
  bubble.textContent = text;
  chatBody.appendChild(bubble);
  chatBody.scrollTop = chatBody.scrollHeight;
  return bubble;
}

// 简单的关键词规则库（离线演示，不依赖网络接口）
const chatRules = [
  {
    keys: ['饮食', '吃', '营养', '食谱', '三餐', '热量', '早餐', '午餐', '晚餐'],
    reply: '饮食建议：三餐尽量规律，主食粗细搭配，保证每餐有一掌心大小的优质蛋白（鸡蛋、鱼、瘦肉或豆制品），再搭配两拳蔬菜。今日蛋白质目标 60g，别忘记补充哦。'
  },
  {
    keys: ['运动', '锻炼', '跑步', '健身', '步数', '拉伸', '久坐'],
    reply: '运动建议：成年人每周建议 150 分钟中等强度运动。久坐时每小时起身活动 3—5 分钟，做几组肩颈拉伸；今天目标完成率 65%，再走 2000 步就差不多达标啦。'
  },
  {
    keys: ['睡眠', '失眠', '熬夜', '睡不够', '入睡'],
    reply: '睡眠建议：尽量固定作息，睡前一小时减少看手机；卧室温度保持在 18—22℃，并保持安静昏暗。若长期入睡困难，建议记录睡眠日志并咨询医生。'
  },
  {
    keys: ['生理期', '月经', '痛经', '经期', '排卵'],
    reply: '生理期护理：注意腹部保暖，避免剧烈运动和生冷饮食；可以适量饮用温水或红糖姜茶。若疼痛明显或周期长期紊乱，建议到医院妇科检查。'
  },
  {
    keys: ['血压', '血糖', '体检', 'bmi', '体脂', '指标'],
    reply: '你的核心体征目前为：BMI 22.0（正常）、血压 110/70 mmHg、空腹血糖 5.2 mmol/L。整体处于健康范围，建议每 3—6 个月复测一次并保持规律运动。'
  },
  {
    keys: ['减肥', '减脂', '体重', '瘦'],
    reply: '减脂建议以“热量缺口 + 力量训练”为主：每天减少 300—500 kcal 摄入，每周 2—3 次力量训练，配合快走或慢跑。不要过度节食，保证蛋白质摄入才能减少肌肉流失。'
  },
  {
    keys: ['心情', '情绪', '压力', '焦虑', '难过'],
    reply: '情绪照顾同样重要：可以试试 4-7-8 呼吸法（吸气 4 秒、屏息 7 秒、呼气 8 秒），或把此刻的感受写进“心理情绪记录”。如果低落持续两周以上，建议寻求专业心理支持。'
  }
];

// 根据用户输入匹配回复
function getReply(text) {
  const lower = text.toLowerCase();
  for (let i = 0; i < chatRules.length; i++) {
    const rule = chatRules[i];
    for (let j = 0; j < rule.keys.length; j++) {
      if (lower.indexOf(rule.keys[j]) !== -1) return rule.reply;
    }
  }
  return '收到～我是健康小管家。你可以问我饮食搭配、运动计划、睡眠改善或生理期护理等问题，我会给出简单可执行的建议。';
}

// 发送消息
function sendChat() {
  const text = chatInput.value.trim();
  if (!text) return;

  addBubble(text, 'user');
  chatInput.value = '';

  // 模拟 AI “正在输入”
  const typingBubble = addBubble('正在输入...', 'bot typing');

  setTimeout(function () {
    typingBubble.remove();
    addBubble(getReply(text), 'bot');
  }, 500);
}

document.getElementById('chatSend').addEventListener('click', sendChat);

// 回车发送
chatInput.addEventListener('keydown', function (event) {
  if (event.key === 'Enter') sendChat();
});

/* ==========================================================
   八、键盘 Esc：关闭弹窗与聊天窗
   ========================================================== */
document.addEventListener('keydown', function (event) {
  if (event.key !== 'Escape') return;
  closeCrop();
  closeProfile();
  closeChat();
  closeMask(periodMask);
  closeMask(familyMask);
  closeMask(memberMask);
  closeMask(reminderMask);
  closeMask(sportMask);
  closeMask(sportDataMask);
  closeMask(vitalMask);
  closeMask(foodMask);
  closeMask(scoreMask);
  closeMask(memberRecordsMask);
  closeMask(newsMask);
  closeTagMenus();
});
</script>
</body>
</html>
"""


# ============================================================
# HTTP 服务：页面 + /api/* 接口，由 backend.app.HealthAppHandler 提供
# ============================================================
# 页面 HTML 与局域网地址在 main() 启动前注入处理器：
#   HealthAppHandler.page_html  = PAGE_HTML
#   HealthAppHandler.mobile_url = mobile_url


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


# ============================================================
# AI 智能体图标：用户提供的跑步插画，压缩后内嵌为 data URI，
# 保证单文件离线运行与 GitHub Pages 静态部署都能直接显示。
# ============================================================
AI_LOGO_DATA_URI = "data:image/png;base64,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"
PAGE_HTML = PAGE_HTML.replace("__AI_LOGO__", AI_LOGO_DATA_URI)


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


def main():
    port = find_free_port()
    local_url = "http://127.0.0.1:%d/" % port

    lan_ip = get_lan_ip()
    mobile_url = "http://%s:%d/" % (lan_ip, port) if lan_ip != "127.0.0.1" else local_url

    # 初始化数据库（health.db）并确保演示账号存在
    prepare()

    # 把页面与手机访问地址注入后端处理器
    HealthAppHandler.page_html = PAGE_HTML
    HealthAppHandler.mobile_url = mobile_url

    # 服务启动后 0.8 秒自动打开浏览器
    threading.Timer(0.8, lambda: webbrowser.open(local_url)).start()

    # 监听 0.0.0.0，手机与电脑在同一 Wi-Fi 下即可访问
    server = ThreadingHTTPServer(("0.0.0.0", port), HealthAppHandler)
    print("=" * 58)
    print("健康管理系统已启动")
    print("电脑访问：", local_url)
    print("手机访问：", mobile_url, "（需连接同一 Wi-Fi）")
    print("接口地址：", local_url + "api/health")
    print("数据文件：health.db（与本文件同目录）")
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
