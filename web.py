# -*- coding: utf-8 -*-
"""
健康管理系统 · 单文件 Web 演示
================================================
将小组设计的功能界面草稿提供给AI，得到「健康管理系统」基础网页，包含：
  1. 健康数据  2. 饮食  3. 运动  4. 女生健康  5. 睡眠  6. 科普资讯
  7. 个人信息档案弹窗  8. AI 健康小管家（悬浮聊天窗）

运行方式（无需安装任何第三方库，仅使用 Python 标准库）：
  - VS Code 打开本文件，点击右上角 ▶ 运行；
  - 或在终端执行：python web.py
  - 启动后浏览器会自动打开 http://127.0.0.1:8000/

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

:root {
  --teal: #4ecdc4;
  --teal-dark: #2fbf9b;
  --text: #2c3648;
  --muted: #8a94a6;
  --line: #eef0f5;
  --bg: #f6f7fb;
  --shadow: 0 2px 14px rgba(30, 42, 70, 0.06);
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
   2. 顶部导航栏
   ========================================================== */
.topbar {
  position: sticky;
  top: 0;
  z-index: 50;
  background: #fff;
  box-shadow: 0 1px 0 var(--line);
}

.topbar .inner {
  height: 64px;
  display: flex;
  align-items: center;
  gap: 36px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
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
}

.logo .icon { width: 19px; height: 19px; stroke-width: 2.2; }

.nav {
  display: flex;
  gap: 34px;
  flex: 1;
}

.nav button {
  position: relative;
  background: none;
  border: 0;
  font-size: 14px;
  color: #6b7688;
  padding: 22px 0;
  transition: color 0.2s;
}

.nav button:hover { color: var(--text); }
.nav button.active { color: #1f2d3d; font-weight: 600; }

/* 当前页签下方的绿色短线 */
.nav button.active::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 12px;
  height: 2px;
  border-radius: 2px;
  background: var(--teal);
}

.user {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 7px;
  border-radius: 20px;
  cursor: pointer;
  transition: background 0.2s;
  flex: none;
}

.user:hover { background: #f5f7fa; }

.avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: #e3e8ef;
  color: #7b8798;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar .icon { width: 16px; height: 16px; }
.caret { width: 14px; height: 14px; color: #8a94a6; }

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
   8. 女生健康页
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

.family-line b { color: #39404f; font-weight: 600; }

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
   14. 响应式适配（窄屏）
   ========================================================== */
@media (max-width: 900px) {
  .brand span { display: none; }
  .topbar .inner { gap: 18px; }
  .nav { gap: 20px; overflow-x: auto; }
  .nav::-webkit-scrollbar { display: none; }
  .nav button { white-space: nowrap; }

  .health-card { flex-direction: column; }
  .ring-box { width: 100%; flex: none; }
  .report-link { align-self: flex-end; }
  .vitals { grid-template-columns: repeat(2, 1fr); }

  .ex-stats { grid-template-columns: repeat(2, 1fr); }
  .female-grid { grid-template-columns: 1fr; }
  .family-grid { grid-template-columns: 1fr; }
  .news-grid { grid-template-columns: 1fr; }
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
</svg>

<!-- ========================================================
     顶部导航
     ======================================================== -->
<header class="topbar">
  <div class="container inner">
    <div class="brand">
      <div class="logo"><svg class="icon"><use href="#i-pulse"/></svg></div>
      <span>健康管理系统</span>
    </div>

    <nav class="nav" id="nav">
      <button class="active" data-page="data">健康数据</button>
      <button data-page="diet">饮食</button>
      <button data-page="sport">运动</button>
      <button data-page="female" id="navFemale">女生健康</button>
      <button data-page="sleep">睡眠</button>
      <button data-page="news">科普资讯</button>
    </nav>

    <div class="user" id="userBtn" title="个人信息">
      <div class="avatar"><svg class="icon"><use href="#i-user"/></svg></div>
      <svg class="icon caret"><use href="#i-chevron"/></svg>
    </div>
  </div>
</header>

<main class="container">

  <!-- 所有页面共用的渐变横幅 -->
  <section class="hero">
    <h1>科学管理健康</h1>
    <p>遇见更好的自己</p>
    <div class="score">
      <div class="row"><span>综合健康评分</span><span>85/100</span></div>
      <div class="bar"><i></i></div>
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
              <div class="label">体重</div>
              <div class="value"><span id="weightValue">65.2</span><span class="unit">kg</span></div>
            </div>
            <div class="vital">
              <div class="label">体脂率</div>
              <div class="value">18.5<span class="unit">%</span></div>
            </div>
            <div class="vital">
              <div class="label">BMI</div>
              <div class="value">
                <span id="bmiValue">21.3</span>
                <span class="badge" id="bmiBadge">正常</span>
              </div>
            </div>
            <div class="vital">
              <div class="label">血压</div>
              <div class="value">110/70<span class="unit">mmHg</span></div>
            </div>
            <div class="vital">
              <div class="label">血糖（空腹）</div>
              <div class="value">5.2<span class="unit">mmol/L</span></div>
            </div>
          </div>
        </div>

        <!-- 右侧环形评分 -->
        <div class="ring-box">
          <button class="report-link" data-toast="体检报告分析：各项指标均在正常范围，继续保持！">体检报告分析 ›</button>
          <div class="ring">
            <svg width="140" height="140" viewBox="0 0 120 120">
              <defs>
                <linearGradient id="ringGrad" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0" stop-color="#7ee0c0"/>
                  <stop offset="1" stop-color="#2fbf9b"/>
                </linearGradient>
              </defs>
              <circle cx="60" cy="60" r="52" fill="none" stroke="#eef1f5" stroke-width="10"/>
              <!-- 周长 ≈ 326.7，85% 对应的偏移量 ≈ 49 -->
              <circle cx="60" cy="60" r="52" fill="none" stroke="url(#ringGrad)" stroke-width="10"
                      stroke-linecap="round" stroke-dasharray="326.7" stroke-dashoffset="49"/>
            </svg>
            <div class="center">
              <div class="num">85%</div>
              <div class="txt">综合健康度</div>
            </div>
          </div>
          <div class="ring-note">较上月提升 2%</div>
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

          <!-- 每日营养目标 -->
          <div class="macros">
            <div class="macro"><div class="label">蛋白质</div><div class="value">60g</div></div>
            <div class="macro"><div class="label">碳水</div><div class="value">150g</div></div>
            <div class="macro"><div class="label">纤维素</div><div class="value">25g</div></div>
            <div class="macro"><div class="label">脂肪</div><div class="value">45g</div></div>
            <div class="macro"><div class="label">总热量</div><div class="value">1800k</div></div>
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

          <div class="tip-card">
            <svg class="icon"><use href="#i-spark"/></svg>
            <div>
              <b>推荐补充</b>
              <p>今日蛋白质摄入略低，晚餐可增加一份鸡胸肉、鸡蛋或豆制品，帮助肌肉修复与饱腹感提升。</p>
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
            <button class="btn-primary" data-toast="已开始记录运动，加油！">
              <svg class="icon"><use href="#i-play"/></svg>开始运动
            </button>
          </div>

          <!-- 今日 / 本周 数据切换 -->
          <div class="tabs" id="sportTabs">
            <button class="active" data-tab="today">今日运动</button>
            <button data-tab="week">本周统计</button>
          </div>

          <div class="ex-stats">
            <div class="ex-stat">
              <div class="ico ico-flame"><svg class="icon"><use href="#i-flame"/></svg></div>
              <div class="value"><span id="exKcal">320</span> <span class="unit">kcal</span></div>
              <div class="label">已消耗</div>
            </div>
            <div class="ex-stat">
              <div class="ico ico-step"><svg class="icon"><use href="#i-footprints"/></svg></div>
              <div class="value"><span id="exSteps">6,540</span> <span class="unit">步</span></div>
              <div class="label">今日步数</div>
            </div>
            <div class="ex-stat">
              <div class="ico ico-clock"><svg class="icon"><use href="#i-clock"/></svg></div>
              <div class="value"><span id="exMinutes">45</span> <span class="unit">分钟</span></div>
              <div class="label">活动时长</div>
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

          <!-- 心理情绪记录 -->
          <div class="mood">
            <div class="mood-title">
              <svg class="icon"><use href="#i-smile"/></svg>心理情绪记录
            </div>
            <textarea placeholder="今天心情怎么样？记录一下吧..."></textarea>
          </div>
        </div>
      </div>
    </section>

    <!-- ====================================================
         页面四：女生健康
         ==================================================== -->
    <section class="page" id="page-female">
      <div class="female-wrap">

        <!-- 女性视图：生理期管理 -->
        <div id="femaleView">
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
                <div class="tip-pink">科学建议：注意保暖，避免剧烈运动，可适量饮用热饮。</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 男性视图：记录母亲 / 爱人的健康情况 -->
        <div id="maleView" hidden>
          <div class="family-card">
            <div class="female-head">
              <div class="female-title family-title">
                <svg class="icon"><use href="#i-heart"/></svg>家人健康档案
              </div>
              <button class="btn-soft" id="openFamilyRecord">添加记录</button>
            </div>

            <div class="family-grid">
              <div class="person-card">
                <div class="person-head">
                  <div class="person-avatar">母</div>
                  <div><span class="person-name">母亲</span><span class="person-age">58岁</span></div>
                </div>
                <div class="family-line">最近体检 <b id="motherExam">2026年9月12日</b></div>
                <div class="family-line">用药提醒 <b>每日降压药</b></div>
                <div class="family-line">下次复诊 <b>12月12日</b></div>
              </div>

              <div class="person-card">
                <div class="person-head">
                  <div class="person-avatar">爱</div>
                  <div><span class="person-name">爱人</span><span class="person-age">28岁</span></div>
                </div>
                <div class="family-line">最近经期 <b id="partnerLastPeriod">10月11日</b></div>
                <div class="family-line">周期长度 <b>28 天</b></div>
                <div class="family-line">排卵日预测 <b>10月25日</b></div>
              </div>
            </div>

            <div class="status-card">
              <div class="status-title">
                <svg class="icon"><use href="#i-heart"/></svg>家人状态记录
              </div>
              <div class="tags" id="maleTags">
                <button class="tag add" id="maleAddTag" type="button">+ 添加标签</button>
              </div>
              <div class="tag-menu" id="maleTagMenu">
                <h4>选择家人状态（可多选）</h4>
                <div class="tag-options" id="maleTagOptions"></div>
                <div class="tag-menu-foot">
                  <button class="btn-mini" type="button" data-close-tag>确定</button>
                </div>
              </div>
              <div class="tip-blue">关怀建议：定期提醒母亲测量血压、按时服药；爱人经期前后注意保暖，避免生冷饮食。</div>
            </div>

            <div class="family-records">
              <h4>最近记录</h4>
              <div id="familyRecordList">
                <div class="record-empty" id="recordEmpty">暂无记录，点击右上角「添加记录」为家人建立档案。</div>
              </div>
            </div>
          </div>
        </div>

      </div>
    </section>

    <!-- ====================================================
         页面五：睡眠
         ==================================================== -->
    <section class="page" id="page-sleep">
      <div class="sleep-wrap">
        <div class="sleep-card">
          <div class="sleep-icon"><svg class="icon"><use href="#i-moon"/></svg></div>
          <h2>优质睡眠，恢复活力</h2>
          <p>连接你的智能手表或手动记录，分析睡眠周期与质量。</p>
          <button class="btn-sleep" data-toast="已开始记录睡眠，请保持设备佩戴">开始记录睡眠</button>
        </div>
      </div>
    </section>

    <!-- ====================================================
         页面六：科普资讯
         ==================================================== -->
    <section class="page" id="page-news">
      <div class="news-grid">
        <article class="news-card">
          <div class="news-img green"><svg class="icon"><use href="#i-fork"/></svg></div>
          <div class="news-body">
            <div class="news-cat green">饮食营养</div>
            <div class="news-title">如何科学搭配三餐饮食？</div>
            <p class="news-desc">合理的饮食搭配不仅能提供充足的能量，还能帮助预防慢性疾病，让身体保持良好状态。</p>
          </div>
        </article>

        <article class="news-card">
          <div class="news-img blue"><svg class="icon"><use href="#i-dumbbell"/></svg></div>
          <div class="news-body">
            <div class="news-cat blue">运动指南</div>
            <div class="news-title">久坐族的5分钟拉伸指南</div>
            <p class="news-desc">长时间面对电脑工作，肩颈酸痛？这几个动作帮你缓解疲劳，恢复身体活力。</p>
          </div>
        </article>

        <article class="news-card">
          <div class="news-img purple"><svg class="icon"><use href="#i-moon"/></svg></div>
          <div class="news-body">
            <div class="news-cat purple">睡眠健康</div>
            <div class="news-title">为什么你总是睡不够？</div>
            <p class="news-desc">了解深度睡眠的重要性，以及如何通过改善卧室环境提升睡眠质量，找回好状态。</p>
          </div>
        </article>
      </div>
    </section>

  </div>
</main>

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
  <div class="modal">
    <div class="modal-head">
      <svg class="icon"><use href="#i-calendar"/></svg>记录生理期
      <button class="modal-close" id="periodClose" aria-label="关闭">
        <svg class="icon"><use href="#i-close"/></svg>
      </button>
    </div>

    <div class="modal-body">
      <div class="field-row">
        <div class="field">
          <label for="periodStart">开始日期</label>
          <input id="periodStart" type="date" value="2026-10-11">
        </div>
        <div class="field">
          <label for="periodEnd">结束日期</label>
          <input id="periodEnd" type="date" value="2026-10-15">
        </div>
      </div>
      <div class="field">
        <label for="cycleDaysInput">周期长度</label>
        <select id="cycleDaysInput"></select>
      </div>
      <p class="form-hint">选择本次经期的开始与结束日期后，经期长度和排卵日会自动更新。</p>
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

  // 根据性别切换「女生健康 / 家人健康」视图
  currentGender = gender;
  applyGenderView();

  closeProfile();
  showToast(gender === '男' ? '个人信息已保存，已切换至家人健康' : '个人信息已保存');
});

/* ==========================================================
   四、饮食记录：输入框回车即可记录
   ========================================================== */
document.querySelectorAll('.meal input').forEach(function (input) {
  input.addEventListener('keydown', function (event) {
    if (event.key !== 'Enter') return;
    const value = input.value.trim();
    if (!value) return;
    showToast('已记录' + input.dataset.meal + '：' + value);
    input.value = '';
  });
});

/* ==========================================================
   五、运动页：今日 / 本周 数据切换
   ========================================================== */
const exerciseData = {
  today: { kcal: '320', steps: '6,540', minutes: '45', percent: 65 },
  week:  { kcal: '2,240', steps: '45,870', minutes: '315', percent: 72 }
};

// 小圆环半径 18，周长 = 2πr ≈ 113.1
const gaugeLength = 2 * Math.PI * 18;

function renderExercise(key) {
  const data = exerciseData[key];
  document.getElementById('exKcal').textContent = data.kcal;
  document.getElementById('exSteps').textContent = data.steps;
  document.getElementById('exMinutes').textContent = data.minutes;
  document.getElementById('exPercent').textContent = data.percent + '%';

  const arc = document.getElementById('exGaugeArc');
  // 通过虚线偏移量控制圆弧长度
  arc.setAttribute('stroke-dashoffset', (gaugeLength * (1 - data.percent / 100)).toFixed(1));
}

document.querySelectorAll('#sportTabs button').forEach(function (btn) {
  btn.addEventListener('click', function () {
    document.querySelectorAll('#sportTabs button').forEach(function (b) {
      b.classList.toggle('active', b === btn);
    });
    renderExercise(btn.dataset.tab);
  });
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

  // 女性显示生理期档案，男性显示家人健康档案
  document.getElementById('femaleView').hidden = !isFemale;
  document.getElementById('maleView').hidden = isFemale;

  // 导航文案同步变化
  document.getElementById('navFemale').textContent = isFemale ? '女生健康' : '家人健康';
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

document.getElementById('openPeriod').addEventListener('click', function () {
  document.getElementById('periodStart').value = toISODate(lastPeriodStart);
  document.getElementById('periodEnd').value = toISODate(addDays(lastPeriodStart, periodDays - 1));
  cycleDaysInput.value = String(cycleDays);
  openMask(periodMask);
});

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
const maleTagValues = ['血压平稳', '血压偏高', '睡眠不佳', '情绪平稳', '血糖偏高', '经期不适', '体检正常'];

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

createTagEditor({
  tagsId: 'maleTags',
  addBtnId: 'maleAddTag',
  menuId: 'maleTagMenu',
  optionsId: 'maleTagOptions',
  values: maleTagValues,
  initial: ['情绪平稳', '血压平稳']
});

// 点击标签面板以外的地方时收起面板
document.addEventListener('click', function (event) {
  if (!event.target.closest('.tag-menu') && !event.target.closest('.tag.add')) {
    closeTagMenus();
  }
});

// ---------- 家人记录弹窗（男性视图） ----------
const familyMask = document.getElementById('familyMask');
const familyPersonSelect = document.getElementById('familyPerson');
const familyTypeSelect = document.getElementById('familyType');

// 母亲没有生理期记录，爱人可以记录生理期
const familyTypeMap = {
  '母亲': ['体检', '用药', '其他'],
  '爱人': ['体检', '用药', '生理期', '其他']
};

function renderFamilyTypes() {
  const person = familyPersonSelect.value;
  const previous = familyTypeSelect.value;

  familyTypeSelect.innerHTML = '';
  familyTypeMap[person].forEach(function (type) {
    const option = document.createElement('option');
    option.value = type;
    option.textContent = type;
    familyTypeSelect.appendChild(option);
  });

  if (familyTypeMap[person].indexOf(previous) !== -1) {
    familyTypeSelect.value = previous;
  }
}

familyPersonSelect.addEventListener('change', renderFamilyTypes);

document.getElementById('openFamilyRecord').addEventListener('click', function () {
  renderFamilyTypes();
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
  const person = document.getElementById('familyPerson').value;
  const type = document.getElementById('familyType').value;
  const date = parseISODate(document.getElementById('familyDate').value);
  const content = document.getElementById('familyContent').value.trim();

  if (!date) {
    showToast('请选择记录日期');
    return;
  }

  // 首次添加时移除空状态提示
  const empty = document.getElementById('recordEmpty');
  if (empty) empty.remove();

  // 生成一条记录
  const item = document.createElement('div');
  item.className = 'record-item';

  const dateEl = document.createElement('span');
  dateEl.className = 'date';
  dateEl.textContent = formatYMD(date);

  const textEl = document.createElement('span');
  textEl.textContent = person + ' · ' + type + (content ? ' · ' + content : '');

  item.appendChild(dateEl);
  item.appendChild(textEl);
  document.getElementById('familyRecordList').appendChild(item);

  // 同步更新上方卡片
  if (person === '母亲' && type === '体检') {
    document.getElementById('motherExam').textContent = formatYMD(date);
  }
  if (person === '爱人' && type === '生理期') {
    document.getElementById('partnerLastPeriod').textContent = formatMD(date);
  }

  document.getElementById('familyContent').value = '';
  closeMask(familyMask);
  showToast('已为' + person + '添加' + type + '记录');
});

// 初始化页面状态
renderCycle();
applyGenderView();

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

    def do_GET(self):
        # 去掉查询参数，例如 /?x=1 → /
        path = self.path.split("?")[0]

        if path in ("/", "/index.html"):
            body = PAGE_HTML.encode("utf-8")
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
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("8000-8100 端口均被占用，请手动修改端口范围")


def main():
    port = find_free_port()
    url = "http://127.0.0.1:%d/" % port

    # 服务启动后 0.8 秒自动打开浏览器
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    server = ThreadingHTTPServer(("127.0.0.1", port), HealthPageHandler)
    print("=" * 50)
    print("健康管理系统已启动：", url)
    print("按 Ctrl + C 停止服务")
    print("=" * 50)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
