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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

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
   3. 顶部渐变横幅
   ========================================================== */
.hero {
  margin-top: 24px;
  border-radius: 16px;
  padding: 26px 30px;
  min-height: 150px;
  color: #fff;
  position: relative;
  overflow: hidden;
  background: linear-gradient(105deg, #4ed0bd 0%, #4fb6cf 45%, #4a7df0 100%);
  box-shadow: 0 8px 24px rgba(74, 125, 240, 0.18);
}

.hero h1 {
  font-size: 28px;
  letter-spacing: 1px;
  font-weight: 700;
}

.hero p {
  font-size: 14px;
  opacity: 0.92;
  margin-top: 8px;
}

.score { margin-top: 22px; max-width: 340px; }

.score .row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  opacity: 0.95;
  margin-bottom: 8px;
}

.bar {
  height: 8px;
  border-radius: 99px;
  background: rgba(255, 255, 255, 0.3);
  overflow: hidden;
}

.bar i {
  display: block;
  height: 100%;
  width: 85%;
  border-radius: 99px;
  background: linear-gradient(90deg, #eafff9, #ffffff);
  transition: width 0.8s ease;
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

.ring-box {
  width: 190px;
  flex: 0 0 190px;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 2px;
}

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

.ring {
  position: relative;
  width: 140px;
  height: 140px;
}

.ring > svg { transform: rotate(-90deg); }

.ring .center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.ring .num { font-size: 28px; font-weight: 800; color: #2b3648; line-height: 1.1; }
.ring .txt { font-size: 12px; color: var(--muted); margin-top: 6px; }

.ring-note {
  font-size: 12px;
  color: #9aa3b2;
  margin-top: 12px;
  text-align: center;
}

/* ==========================================================
   6. 饮食页
   ========================================================== */
.diet-wrap { max-width: 720px; margin: 0 auto; }

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
.exercise-wrap { max-width: 780px; margin: 0 auto; }

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
.family-wrap { max-width: 760px; margin: 0 auto; }

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
   科学变美 · 目标与计划
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

.modal-body { padding: 20px 20px 6px; }

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

.modal-foot {
  display: flex;
  justify-content: flex-end;
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
  width: 54px;
  height: 54px;
  border: 0;
  border-radius: 50%;
  background: linear-gradient(135deg, #4ed3b0, #3bb8a3);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 10px 24px rgba(59, 184, 163, 0.4);
  transition: transform 0.2s;
}

.fab:hover { transform: scale(1.06); }
.fab .icon { width: 26px; height: 26px; }

.fab .dot {
  position: absolute;
  top: 4px;
  right: 4px;
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
.ring .num { color: #4a3525; }

/* 顶部横幅 */
.hero {
  background: linear-gradient(110deg, #d9edc1 0%, #c6e4c8 48%, #9fc6e4 100%);
  color: #6e3a18;
  box-shadow: 0 8px 24px rgba(139, 74, 34, 0.14);
}
.hero h1 {
  font-family: Georgia, "Times New Roman", "Songti SC", "SimSun", serif;
}
.hero p { color: #7d5438; opacity: 1; }
.score .row { color: #6e3a18; }
.bar { background: rgba(139, 74, 34, 0.18); }
.bar i { background: linear-gradient(90deg, #8b4a22, #b06a3a); }

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
.fab {
  background: linear-gradient(135deg, #8b4a22, #a9653a);
  box-shadow: 0 10px 24px rgba(139, 74, 34, 0.35);
}
.chat-head { background: linear-gradient(135deg, #8b4a22, #a9653a); }
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
  .ring-box { width: 100%; flex: none; }
  .report-link { align-self: flex-end; }
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

@media (max-width: 560px) {
  .container { padding: 0 16px; }
  .hero { padding: 22px 20px; }
  .hero h1 { font-size: 24px; }
  .vitals { grid-template-columns: 1fr; }
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

.weight-chart svg { width: 100%; height: 140px; display: block; }
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
.score-group {
  display: flex;
  gap: 16px;
  margin-top: 22px;
}

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

@media (max-width: 700px) {
  .sport-inputs { grid-template-columns: 1fr; }
  .plan-day { grid-template-columns: 22px 36px 1fr; }
  .score-group { flex-direction: column; gap: 10px; }
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
        <p>填写后，我们会为你生成更贴合的健康建议与变美计划。</p>
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
              <input id="obWeight" type="number" step="0.1" value="65.2">
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
    <div class="avatar"><svg class="icon"><use href="#i-user"/></svg></div>
    <div class="side-user-info">
      <span class="side-user-name" id="sideUserName">张三</span>
      <span class="side-user-sub" id="sideUserSub">女 · 165cm</span>
    </div>
    <svg class="icon caret"><use href="#i-chevron"/></svg>
  </div>
</aside>

<div class="main-area">
<main class="container">

  <!-- 所有页面共用的渐变横幅 -->
  <section class="hero">
    <h1>科学管理健康</h1>
    <p>遇见更好的自己</p>
    <div class="score-group">
      <div class="score">
        <div class="row"><span>综合健康评分</span><span><b id="scoreTotal">0</b>/100</span></div>
        <div class="bar"><i id="scoreTotalBar"></i></div>
      </div>
      <div class="score">
        <div class="row"><span>饮食健康评分</span><span><b id="scoreDiet">0</b>/100</span></div>
        <div class="bar"><i id="scoreDietBar"></i></div>
      </div>
      <div class="score">
        <div class="row"><span>运动完成评分</span><span><b id="scoreSport">0</b>/100</span></div>
        <div class="bar"><i id="scoreSportBar"></i></div>
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
              <div class="value"><span id="weightValue">65.2</span><span class="unit">kg</span></div>
            </div>
            <div class="vital">
              <div class="vital-head">
                <div class="label">体脂率</div>
                <button class="vital-edit" type="button" data-vital="fat">修改</button>
              </div>
              <div class="value"><span id="fatValue">18.5</span><span class="unit">%</span></div>
            </div>
            <div class="vital">
              <div class="vital-head">
                <div class="label">BMI</div>
                <button class="vital-edit" type="button" data-vital="bmi">修改</button>
              </div>
              <div class="value">
                <span id="bmiValue">21.3</span>
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

        <!-- 右侧环形评分 -->
        <div class="ring-box">
          <button class="report-link" id="quickReportUpload">上传体检报告 ›</button>
          <div class="ring">
            <svg width="140" height="140" viewBox="0 0 120 120">
              <defs>
                <linearGradient id="ringGrad" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0" stop-color="#7ee0c0"/>
                  <stop offset="1" stop-color="#2fbf9b"/>
                </linearGradient>
              </defs>
              <circle cx="60" cy="60" r="52" fill="none" stroke="#eef1f5" stroke-width="10"/>
              <!-- 周长 ≈ 326.7，偏移量由综合评分动态计算 -->
              <circle cx="60" cy="60" r="52" fill="none" stroke="url(#ringGrad)" stroke-width="10"
                      stroke-linecap="round" stroke-dasharray="326.7" stroke-dashoffset="326.7" id="ringArc"/>
            </svg>
            <div class="center">
              <div class="num" id="ringScore">0%</div>
              <div class="txt">综合健康度</div>
            </div>
          </div>
          <div class="ring-note">根据饮食、运动与体重实时更新</div>
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
              <div class="value">18.2<span class="unit">%</span></div>
            </div>
            <div class="report-item">
              <div class="label">BMI</div>
              <div class="value">21.2</div>
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

          <!-- 回车即可记录一条饮食 -->
          <div class="meal">
            <span class="meal-tag morning">早</span>
            <input data-meal="早餐" placeholder="例如：一杯牛奶，两片全麦面包...">
          </div>
          <div class="meal">
            <span class="meal-tag noon">中</span>
            <input data-meal="午餐" placeholder="记录午餐...">
          </div>
          <div class="meal">
            <span class="meal-tag night">晚</span>
            <input data-meal="晚餐" placeholder="记录晚餐...">
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
              <button class="btn-primary" id="generatePlan" type="button">生成变美计划</button>
            </div>

            <!-- 计划结果 -->
            <div class="beauty-result">
              <div class="beauty-empty" id="beautyEmpty">
                设置目标体重与周期后，<br>这里会生成属于你的变美计划。
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

          <!-- 家人卡片由 JavaScript 根据数据动态生成 -->
          <div class="family-grid" id="familyGrid"></div>

          <div class="family-record-head">
            <h3>最近记录</h3>
          </div>
          <div class="family-records">
            <div id="familyRecordList"></div>
          </div>
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
        <label for="pName">姓名</label>
        <input id="pName" type="text" value="张三">
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
          <input id="pWeight" type="number" step="0.1" value="65.2">
        </div>
      </div>
    </div>

    <div class="modal-foot">
      <button class="btn-save" id="saveProfile">保存修改</button>
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
        <label for="memberNote">备注</label>
        <input id="memberNote" type="text" placeholder="如：每日降压药、经期注意保暖">
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
        <label for="reminderDate">提醒日期</label>
        <input id="reminderDate" type="date">
      </div>
    </div>

    <div class="modal-foot">
      <button class="btn-cancel" id="reminderCancel">取消</button>
      <button class="btn-save" id="reminderSave">保存</button>
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
<button class="fab" id="fab" aria-label="打开健康小管家">
  <svg class="icon"><use href="#i-chat"/></svg>
  <span class="dot" id="fabDot"></span>
</button>

<div class="chat" id="chat">
  <div class="chat-head">
    <div class="ico"><svg class="icon"><use href="#i-chat"/></svg></div>
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

  // 同步到个人信息弹窗
  document.getElementById('pName').value = name;
  document.getElementById('pGender').value = gender;
  if (height > 0) document.getElementById('pHeight').value = height;
  if (weight > 0) document.getElementById('pWeight').value = weight.toFixed(1);

  // 同步到核心体征并重算 BMI
  if (weight > 0) {
    document.getElementById('weightValue').textContent = weight.toFixed(1);
  }
  if (height > 0 && weight > 0) {
    const bmi = weight / Math.pow(height / 100, 2);
    document.getElementById('bmiValue').textContent = bmi.toFixed(1);

    const badge = document.getElementById('bmiBadge');
    if (bmi < 18.5) {
      badge.textContent = '偏瘦';
      badge.className = 'badge warn';
    } else if (bmi < 24) {
      badge.textContent = '正常';
      badge.className = 'badge';
    } else {
      badge.textContent = '偏高';
      badge.className = 'badge warn';
    }
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

function openProfile() {
  // 打开弹窗时回显当前性别
  document.getElementById('pGender').value = currentGender;
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
  const name = document.getElementById('pName').value.trim() || '未命名';
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
  document.getElementById('bmiValue').textContent = bmi.toFixed(1);

  const badge = document.getElementById('bmiBadge');
  if (bmi < 18.5) {
    badge.textContent = '偏瘦';
    badge.className = 'badge warn';
  } else if (bmi < 24) {
    badge.textContent = '正常';
    badge.className = 'badge';
  } else {
    badge.textContent = '偏高';
    badge.className = 'badge warn';
  }

  document.getElementById('userBtn').title = '个人信息 · ' + name + '（' + gender + '）';
  document.getElementById('sideUserName').textContent = name;
  document.getElementById('sideUserSub').textContent = gender + ' · ' + height + 'cm';

  // 根据性别显示/隐藏「健康数据」页中的女性健康档案
  currentGender = gender;
  applyGenderView();

  // 营养目标与体重相关，档案变化后重新计算
  refreshDietViews();

  closeProfile();
  showToast(gender === '男' ? '个人信息已保存，女性健康档案已隐藏' : '个人信息已保存');
});

/* ==========================================================
   四、饮食记录：输入框回车即可记录
   ========================================================== */
document.querySelectorAll('.meal input').forEach(function (input) {
  input.addEventListener('keydown', function (event) {
    if (event.key !== 'Enter') return;
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
  document.getElementById('fatValue').textContent = '18.2';
  document.getElementById('bmiValue').textContent = '21.2';
  document.getElementById('bpValue').textContent = '112/72';
  document.getElementById('glucoseValue').textContent = '5.0';

  // 体检同步的体重也进入趋势记录
  addWeightRecord(64.8);
  saveData('bp', { systolic: 112, diastolic: 72 });
  saveData('glucose', 5.0);
  refreshDietViews();

  const badge = document.getElementById('bmiBadge');
  badge.textContent = '正常';
  badge.className = 'badge';

  showToast('体检指标已同步到核心体征');
});

/* ==========================================================
   五、运动页：目标与数据由用户填写，完成度自动计算
   ========================================================== */
const sportState = loadData('sport', {
  goal: { kcal: 500, steps: 8000, minutes: 60 },
  history: {}
});

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
function moodEmojiOf(mood) {
  return { '开心': '😄', '平静': '🙂', '疲惫': '😴', '焦虑': '😰', '低落': '😔' }[mood] || '·';
}

function renderWeekPanel() {
  const panel = document.getElementById('weekPanel');
  if (!panel) return;

  const today = new Date();
  const monday = addDays(today, -((today.getDay() + 6) % 7));
  const moodLog = loadData('moodLog', {});
  const days = [];

  for (let index = 0; index < 7; index++) {
    const day = addDays(monday, index);
    const key = toISODate(day);
    const data = sportState.history[key] || { kcal: 0, steps: 0, minutes: 0 };
    days.push({ date: day, key: key, data: data, mood: moodLog[key] ? moodLog[key].mood : '' });
  }

  const maxKcal = Math.max.apply(null, days.map(function (item) {
    return item.data.kcal || 0;
  }).concat([1]));

  panel.innerHTML = '<div class="week-grid" id="weekGrid"></div><div class="week-detail" id="weekDetail">点击上方任意日期，查看当天的运动与心情记录。</div>';
  const grid = document.getElementById('weekGrid');

  days.forEach(function (item) {
    const tile = document.createElement('div');
    tile.className = 'week-day' + (item.data.kcal || item.data.steps ? '' : ' empty');
    const icon = item.data.kcal >= maxKcal * 0.6 && item.data.kcal > 0 ? 'i-flame' : 'i-activity';

    tile.innerHTML = '<div class="date">' + (item.date.getMonth() + 1) + '/' + item.date.getDate() + '</div>' +
      (item.mood ? '<span class="emoji">' + moodEmojiOf(item.mood) + '</span>' : '<svg class="icon"><use href="#' + icon + '"></use></svg>') +
      '<div class="kcal">' + (item.data.kcal ? Math.round(item.data.kcal) + ' kcal' : '无记录') + '</div>';

    tile.addEventListener('click', function () {
      grid.querySelectorAll('.week-day').forEach(function (node) {
        node.classList.remove('selected');
      });
      tile.classList.add('selected');
      document.getElementById('weekDetail').innerHTML =
        '<b>' + (item.date.getMonth() + 1) + ' 月 ' + item.date.getDate() + ' 日</b><br>' +
        '消耗：' + Math.round(item.data.kcal || 0) + ' kcal　步数：' + formatNumber(item.data.steps || 0) +
        '　时长：' + Math.round(item.data.minutes || 0) + ' 分钟<br>' +
        '心情：' + (item.mood ? moodEmojiOf(item.mood) + ' ' + item.mood : '未记录');
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
  { name: '户外运动', desc: '跑步、骑行、徒步、登山、游泳' },
  { name: '球类运动', desc: '乒乓球、羽毛球、篮球、足球、网球' },
  { name: '形体运动', desc: '瑜伽、普拉提、健身操、力量训练' },
  { name: '碎片化运动', desc: '爬楼梯、跳绳、开合跳、工间操' }
];

const sportTypes = [
  { name: '健走', board: '户外运动', cal: '约 280 kcal/小时', color: '#6b8f3f', icon: 'i-footprints', met: 4.3 },
  { name: '户外骑行', board: '户外运动', cal: '约 350 kcal/小时', color: '#5f8fae', icon: 'i-bike', met: 6.8 },
  { name: '徒步', board: '户外运动', cal: '约 320 kcal/小时', color: '#4f7898', icon: 'i-mountain', met: 6.0 },
  { name: '跑步', board: '户外运动', cal: '约 450 kcal/小时', color: '#b06a3a', icon: 'i-run', met: 8.3 },
  { name: '登山', board: '户外运动', cal: '约 420 kcal/小时', color: '#6e3a18', icon: 'i-mountain', met: 7.5 },
  { name: '游泳', board: '户外运动', cal: '约 500 kcal/小时', color: '#4f7898', icon: 'i-swim', met: 7.0 },
  { name: '乒乓球', board: '球类运动', cal: '约 360 kcal/小时', color: '#8b4a22', icon: 'i-ball', met: 4.0 },
  { name: '羽毛球', board: '球类运动', cal: '约 420 kcal/小时', color: '#a9653a', icon: 'i-ball', met: 5.5 },
  { name: '篮球', board: '球类运动', cal: '约 470 kcal/小时', color: '#b06a3a', icon: 'i-ball', met: 6.5 },
  { name: '足球', board: '球类运动', cal: '约 500 kcal/小时', color: '#6b8f3f', icon: 'i-ball', met: 7.0 },
  { name: '网球', board: '球类运动', cal: '约 440 kcal/小时', color: '#7a9b5c', icon: 'i-ball', met: 6.0 },
  { name: '瑜伽', board: '形体运动', cal: '约 180 kcal/小时', color: '#9c7a4f', icon: 'i-yoga', met: 3.0 },
  { name: '普拉提', board: '形体运动', cal: '约 200 kcal/小时', color: '#9c7a4f', icon: 'i-yoga', met: 3.0 },
  { name: '健身操', board: '形体运动', cal: '约 300 kcal/小时', color: '#c08a5a', icon: 'i-dumbbell', met: 5.0 },
  { name: '力量训练', board: '形体运动', cal: '约 330 kcal/小时', color: '#8b4a22', icon: 'i-dumbbell', met: 5.0 },
  { name: '拉伸放松', board: '形体运动', cal: '约 120 kcal/小时', color: '#8b7d70', icon: 'i-activity', met: 2.3 },
  { name: '爬楼梯', board: '碎片化运动', cal: '约 500 kcal/小时', color: '#6e3a18', icon: 'i-mountain', met: 8.8 },
  { name: '快走 10 分钟', board: '碎片化运动', cal: '约 280 kcal/小时', color: '#6b8f3f', icon: 'i-footprints', met: 4.3 },
  { name: '跳绳', board: '碎片化运动', cal: '约 600 kcal/小时', color: '#a9653a', icon: 'i-activity', met: 10.0 },
  { name: '开合跳', board: '碎片化运动', cal: '约 480 kcal/小时', color: '#b06a3a', icon: 'i-activity', met: 8.0 },
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
  const current = parseFloat(document.getElementById('weightValue').textContent) || 65.2;

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
    showToast('请先生成变美计划');
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
  { id: 'm1', relation: '母亲', name: '', age: 58, note: '每日降压药' },
  { id: 'm2', relation: '爱人', name: '', age: 28, note: '经期前后注意保暖' }
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

// 取某位家人最近一条未完成的提醒
function nextReminder(memberId) {
  const list = reminders.filter(function (reminder) {
    return reminder.memberId === memberId && !reminder.done;
  });
  if (!list.length) return null;
  return list.slice().sort(function (a, b) {
    return a.date.localeCompare(b.date);
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

    // 最近记录
    const record = latestRecord(member.id);
    const recordLine = document.createElement('div');
    recordLine.className = 'family-line';
    recordLine.appendChild(document.createTextNode('最近记录'));
    const recordValue = document.createElement('b');
    recordValue.textContent = record
      ? formatYMD(parseISODate(record.date)) + ' · ' + record.type
      : '暂无记录';
    recordLine.appendChild(recordValue);
    card.appendChild(recordLine);

    // 最近提醒
    const reminder = nextReminder(member.id);
    const reminderLine = document.createElement('div');
    reminderLine.className = 'family-line';
    reminderLine.appendChild(document.createTextNode('关怀提醒'));
    const reminderValue = document.createElement('b');
    reminderValue.textContent = reminder
      ? formatMD(parseISODate(reminder.date)) + ' · ' + reminder.title
      : '暂无提醒';
    reminderLine.appendChild(reminderValue);
    card.appendChild(reminderLine);

    // 备注
    const noteLine = document.createElement('div');
    noteLine.className = 'family-line';
    noteLine.appendChild(document.createTextNode('备注'));
    const noteValue = document.createElement('b');
    noteValue.textContent = member.note || '暂无';
    noteLine.appendChild(noteValue);
    card.appendChild(noteLine);

    grid.appendChild(card);
  });
}

// 渲染「最近记录」列表
function renderFamilyRecords() {
  const list = document.getElementById('familyRecordList');
  list.innerHTML = '';

  if (!familyRecords.length) {
    const empty = document.createElement('div');
    empty.className = 'record-empty';
    empty.textContent = '暂无记录，点击「添加记录」为家人建立健康档案。';
    list.appendChild(empty);
    return;
  }

  familyRecords.slice().sort(function (a, b) {
    return b.date.localeCompare(a.date);
  }).forEach(function (record) {
    const member = getMember(record.memberId);

    const item = document.createElement('div');
    item.className = 'record-item';

    const dateEl = document.createElement('span');
    dateEl.className = 'date';
    dateEl.textContent = formatYMD(parseISODate(record.date));

    const textEl = document.createElement('span');
    textEl.textContent = memberLabel(member) + ' · ' + record.type +
      (record.content ? ' · ' + record.content : '');

    item.appendChild(dateEl);
    item.appendChild(textEl);
    list.appendChild(item);
  });
}

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
  renderFamilyRecords();

  document.getElementById('familyContent').value = '';
  closeMask(familyMask);
  showToast('已为' + memberLabel(member) + '添加' + type + '记录');
});

// ---------- 添加家人信息弹窗 ----------
document.getElementById('openMember').addEventListener('click', function () {
  document.getElementById('memberRelation').value = '';
  document.getElementById('memberAge').value = '';
  document.getElementById('memberName').value = '';
  document.getElementById('memberNote').value = '';
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
  const note = document.getElementById('memberNote').value.trim();

  if (!relation) {
    showToast('请填写家人的称呼或关系');
    return;
  }

  familyMembers.push({
    id: 'm' + Date.now(),
    relation: relation,
    name: name,
    age: age || '',
    note: note
  });

  renderFamilyMembers();
  renderMemberOptions();
  closeMask(memberMask);
  showToast('已添加家人：' + relation);
});

// ---------- 添加关怀提醒弹窗 ----------
document.getElementById('openReminder').addEventListener('click', function () {
  renderMemberOptions();
  document.getElementById('reminderTitle').value = '';
  document.getElementById('reminderDate').value = toISODate(new Date());
  openMask(reminderMask);
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
  const date = parseISODate(document.getElementById('reminderDate').value);

  if (!member) {
    showToast('请先添加家人信息');
    return;
  }
  if (!title) {
    showToast('请填写提醒内容');
    return;
  }
  if (!date) {
    showToast('请选择提醒日期');
    return;
  }

  reminders.push({
    id: 'r' + Date.now(),
    memberId: member.id,
    title: title,
    date: toISODate(date),
    done: false
  });
  saveData('reminders', reminders);

  renderReminders();
  renderFamilyMembers();
  closeMask(reminderMask);
  showToast('关怀提醒已添加');
});

// 初始化页面状态
renderCycle();
applyGenderView();
renderMemberOptions();
renderFamilyMembers();
renderFamilyRecords();
renderReminders();

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

  if (bmi < 18.5) {
    badge.textContent = '偏瘦';
    badge.className = 'badge warn';
  } else if (bmi < 24) {
    badge.textContent = '正常';
    badge.className = 'badge';
  } else {
    badge.textContent = '偏高';
    badge.className = 'badge warn';
  }
}

function currentHeightMeters() {
  return (parseFloat(document.getElementById('pHeight').value) || 165) / 100;
}

// 体重变化后同步 BMI、个人档案与趋势
function applyWeightChange(weight) {
  document.getElementById('weightValue').textContent = weight.toFixed(1);
  document.getElementById('pWeight').value = weight.toFixed(1);

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
const weightHistory = loadData('weightHistory', []);

function addWeightRecord(weight) {
  if (!weight || weight < 20 || weight > 200) return;

  const date = toISODate(new Date());
  const last = weightHistory[weightHistory.length - 1];

  // 同一天重复记录同一数值时跳过，否则每次都保留一个点，保证曲线上能看到变化
  if (last && last.date === date && Math.abs(last.weight - weight) < 0.01) {
    return;
  }
  weightHistory.push({ date: date, weight: weight });

  while (weightHistory.length > 60) weightHistory.shift();
  saveData('weightHistory', weightHistory);
  renderWeightChart();

  // 体重变化后重新计算营养目标与评分
  refreshDietViews();
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
    const data = weightHistory.slice(-14);
    const latest = data[data.length - 1].weight;
    const head = '<div class="weight-chart-head"><span>近 ' + data.length + ' 次体重记录</span><b>' +
      latest.toFixed(1) + ' kg</b></div>';

    if (data.length === 1) {
      html = head + '<div class="weight-chart-empty">再记录一次体重，就能看到趋势曲线。</div>';
    } else {
      const width = 320;
      const height = 140;
      const left = 32;
      const right = 12;
      const top = 16;
      const bottom = 26;
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

      svg += '<text x="' + left + '" y="' + (height - 6) + '">' + data[0].date.slice(5) + '</text>';
      svg += '<text x="' + (width - right) + '" y="' + (height - 6) + '" text-anchor="end">' +
        data[data.length - 1].date.slice(5) + '</text>';
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
    reply: '你的核心体征目前为：BMI 21.3（正常）、血压 110/70 mmHg、空腹血糖 5.2 mmol/L。整体处于健康范围，建议每 3—6 个月复测一次并保持规律运动。'
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
  closeMask(newsMask);
  closeTagMenus();
});
</script>
</body>
</html>
"""


# ============================================================
# HTTP 服务：把上面的 HTML 返回给浏览器
# ============================================================
class HealthPageHandler(BaseHTTPRequestHandler):
    """处理浏览器请求：根路径返回页面，其余路径返回 404。"""

    # 供登录页显示的手机访问地址，由 main() 启动时写入
    mobile_url = "http://127.0.0.1:8000/"

    def do_GET(self):
        # 去掉查询参数，例如 /?x=1 → /
        path = self.path.split("?")[0]

        if path in ("/", "/index.html"):
            # 把登录页中的占位符替换为实际局域网地址
            html = PAGE_HTML.replace("__MOBILE_URL__", self.mobile_url)
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path == "/favicon.ico":
            # 没有图标文件，直接返回 204，避免浏览器报 404
            self.send_response(204)
            self.end_headers()
        else:
            body = "404 Not Found".encode("utf-8")
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def log_message(self, fmt, *args):
        """在终端打印简短的访问日志。"""
        print("[HTTP] " + fmt % args)


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


def main():
    port = find_free_port()
    local_url = "http://127.0.0.1:%d/" % port

    lan_ip = get_lan_ip()
    mobile_url = "http://%s:%d/" % (lan_ip, port) if lan_ip != "127.0.0.1" else local_url

    # 登录页展示手机访问链接
    HealthPageHandler.mobile_url = mobile_url

    # 服务启动后 0.8 秒自动打开浏览器
    threading.Timer(0.8, lambda: webbrowser.open(local_url)).start()

    # 监听 0.0.0.0，手机与电脑在同一 Wi-Fi 下即可访问
    server = ThreadingHTTPServer(("0.0.0.0", port), HealthPageHandler)
    print("=" * 58)
    print("健康管理系统已启动")
    print("电脑访问：", local_url)
    print("手机访问：", mobile_url, "（需连接同一 Wi-Fi）")
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
