# -*- coding: utf-8 -*-
"""异地家庭慢病健康管理系统 · 预实验自动化评测脚本（零第三方依赖）。

用法：
    python eval/run_pilot_eval.py

输出：
    1. 终端打印三组对照实验的真实指标汇总；
    2. 自动生成 eval/pilot_report.md，可直接用于大创申报书「十二、已有基础」与答辩材料。
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend import ai, guidelines, validator  # noqa: E402

SAMPLE_PATH = os.path.join(ROOT, "eval", "sample_cases.json")
REPORT_PATH = os.path.join(ROOT, "eval", "pilot_report.md")


def legacy_detect_action(message):
    """v1.0 基线：旧版纯关键词规则（无问句屏蔽、无慢病血压口语解析）。"""
    text = str(message or "").strip()
    if not text or len(text) > 500:
        return None
    sport = next((name for name in ai.SPORT_KEYWORDS if name in text), None)
    if sport and any(hint in text for hint in ai.SPORT_HINTS):
        return {"type": "sport_start", "sport": sport}
    if (any(word in text for word in ("吃", "喝", "早餐", "午餐", "晚餐", "加餐", "夜宵"))
            and any(hint in text for hint in ai.MEAL_HINTS)):
        return {"type": "meal_add"}
    return None


def eval_intents(cases):
    base_ok = 0
    new_ok = 0
    base_fp = 0
    new_fp = 0
    base_bp_hit = 0
    new_bp_hit = 0
    bp_total = 0
    bad_cases = []

    for c in cases:
        exp = c["expected_type"]
        if exp == "bp_record":
            bp_total += 1
        b = legacy_detect_action(c["text"])
        n = ai.detect_action(c["text"])
        b_type = b["type"] if b else None
        n_type = n["type"] if n else None

        if b_type == exp:
            base_ok += 1
        if n_type == exp:
            new_ok += 1
        else:
            bad_cases.append((c["id"], c["text"], exp, n_type))

        if exp is None and b_type is not None:
            base_fp += 1
        if exp is None and n_type is not None:
            new_fp += 1

        if exp == "bp_record":
            if b_type == "bp_record":
                base_bp_hit += 1
            if n_type == "bp_record":
                new_bp_hit += 1

    neg_total = sum(1 for c in cases if c["expected_type"] is None)
    return {
        "total": len(cases),
        "base_acc": base_ok / len(cases),
        "new_acc": new_ok / len(cases),
        "base_bp_recall": base_bp_hit / max(1, bp_total),
        "new_bp_recall": new_bp_hit / max(1, bp_total),
        "base_fp_rate": base_fp / max(1, neg_total),
        "new_fp_rate": new_fp / max(1, neg_total),
        "bad_cases": bad_cases,
    }


def eval_safety(cases):
    """对比「无校验直写 Baseline」与「生理边界 + 基线一致性 + 质量门控 + 餐食钳制」。"""
    anomalies = [c for c in cases if c["expect_guarded"]]
    normals = [c for c in cases if not c["expect_guarded"]]

    tp = 0
    fp = 0
    fn = 0
    tn = 0
    false_writes_base = len(anomalies)  # 无校验直写全部异常都会直接落库
    false_writes_new = 0
    details = []

    for c in cases:
        if c["kind"] == "bp":
            res = validator.validate_bp(
                c["systolic"],
                c["diastolic"],
                pulse=c.get("pulse"),
                recent_readings=c.get("recent"),
                image_quality=c.get("image_quality"),
                confidence=c.get("confidence"),
            )
            guarded = bool(res["blocked"] or res["requiresDoubleConfirm"])
        else:
            res = validator.clamp_meal_items(c.get("items") or [])
            guarded = bool(res["droppedCount"] > 0 or res["clampedCount"] > 0)

        exp = c["expect_guarded"]
        if exp and guarded:
            tp += 1
        elif exp and not guarded:
            fn += 1
            false_writes_new += 1
            details.append((c["id"], c["desc"], "漏拦"))
        elif not exp and guarded:
            fp += 1
            details.append((c["id"], c["desc"], "误拦"))
        else:
            tn += 1

    precision = tp / max(1, tp + fp)
    recall = tp / max(1, tp + fn)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "total": len(cases),
        "anomaly_total": len(anomalies),
        "normal_total": len(normals),
        "base_false_write_rate": false_writes_base / max(1, len(anomalies)),
        "new_false_write_rate": false_writes_new / max(1, len(anomalies)),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "fp": fp,
        "fn": fn,
        "details": details,
    }


def eval_guidelines(cases):
    hit = 0
    urgent_total = 0
    urgent_hit = 0
    traceable = 0
    misses = []

    fake_refs = [{"refId": "R-FAM-1", "date": "2026-11-27", "label": "爸爸 · 血压：146/92 mmHg"}]

    for c in cases:
        matched = guidelines.retrieve_guidelines(c["query"], "高血压家庭监测", top_k=3)
        matched_ids = {m["id"] for m in matched}
        expected = set(c["expected_ids"])
        if matched_ids & expected:
            hit += 1
        else:
            misses.append((c["id"], c["query"], sorted(expected), sorted(matched_ids)))

        if c.get("urgent"):
            urgent_total += 1
            if "G-HTN-04" in matched_ids and "G-SAFE-01" in matched_ids:
                urgent_hit += 1

        # 验证降级规则回复是否同时包含个人记录编号与指南编号（可溯源率）
        reply = ai._degraded_grounded_reply(c["query"], matched, fake_refs)
        if "[R-FAM-1]" in reply and any("[%s]" % m["id"] in reply for m in matched):
            traceable += 1

    return {
        "total": len(cases),
        "recall_at_3": hit / max(1, len(cases)),
        "urgent_safety_rate": urgent_hit / max(1, urgent_total),
        "traceable_rate": traceable / max(1, len(cases)),
        "misses": misses,
    }


def pct(value):
    return "%.1f%%" % (value * 100.0)


def main():
    started = time.time()
    data = json.load(open(SAMPLE_PATH, "r", encoding="utf-8"))

    intent_res = eval_intents(data["intent_cases"])
    safety_res = eval_safety(data["safety_cases"])
    guide_res = eval_guidelines(data["guideline_cases"])
    elapsed_ms = (time.time() - started) * 1000.0

    total_n = intent_res["total"] + safety_res["total"] + guide_res["total"]
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if intent_res["bad_cases"]:
        bad_lines = ["预实验中暴露的典型规则边界 Bad Case（直接对应立项后「规则+语义混合意图识别」研究任务）："]
        for cid, txt, exp, got in intent_res["bad_cases"]:
            bad_lines.append("- `%s`「%s」：期望 `%s`，规则输出 `%s`（需语义补足模块处理中文口语数字/隐式餐次表述）。" % (cid, txt, exp, got))
        bad_case_md = "\n".join(bad_lines)
    else:
        bad_case_md = "当前离线预实验样本均命中预期，后续将引入更复杂口语及多轮指代难例进一步压测。"

    report = f"""# 异地家庭慢病健康管理系统 · 预实验基线评测报告

- **评测时间**：{now_str}
- **评测集版本**：`{data["meta"]["version"]}`（总样本量 **N = {total_n}**，零第三方依赖确定性离线复现）
- **脚本耗时**：{elapsed_ms:.1f} ms（命令：`python eval/run_pilot_eval.py`）

## 一、核心对照实验结果汇总

| 评测维度 | 样本量 | v1.0 基线方案（改造前） | v1.1 改进方案（申报前原型） | 关键提升 |
| --- | ---: | ---: | ---: | --- |
| 1. 口语意图识别整体准确率 | {intent_res["total"]} | {pct(intent_res["base_acc"])} | **{pct(intent_res["new_acc"])}** | +{(intent_res["new_acc"] - intent_res["base_acc"]) * 100:.1f} 个百分点 |
| 2. 慢病血压口语录入召回率 | 6 | {pct(intent_res["base_bp_recall"])} | **{pct(intent_res["new_bp_recall"])}** | 支持成员/时段/服药状态结构化抽取 |
| 3. 咨询问句误触发率（越低越好） | 8 | {pct(intent_res["base_fp_rate"])} | **{pct(intent_res["new_fp_rate"])}** | 屏蔽咨询类问句，防止误建记录 |
| 4. 异常/对抗样本误写库率（越低越好） | {safety_res["anomaly_total"]} | {pct(safety_res["base_false_write_rate"])} | **{pct(safety_res["new_false_write_rate"])}** | 生理边界 + 7 天基线 + 质量门控拦截 |
| 5. 写前安全校验 F1（含正常样本防误拦） | {safety_res["total"]} | — | **{pct(safety_res["f1"])}**（P={pct(safety_res["precision"])}, R={pct(safety_res["recall"])}） | 正常平稳样本误拦数：{safety_res["fp"]}/{safety_res["normal_total"]} |
| 6. 权威慢病指南 Top-3 召回命中率 | {guide_res["total"]} | 0.0%（无指南库） | **{pct(guide_res["recall_at_3"])}** | 覆盖 2024 高血压/膳食/血糖/BMI 指南 |
| 7. 急症警戒红线与非诊断声明强制命中率 | 2 | 0.0% | **{pct(guide_res["urgent_safety_rate"])}** | 命中 ≥180/110 或胸痛强制就医提示 |
| 8. 降级模式建议可溯源率（记录+指南双引用） | {guide_res["total"]} | 0.0% | **{pct(guide_res["traceable_rate"])}** | 外部模型不可用时仍保持双源可核查 |

## 二、指标定义（与大创申报书对齐）

1. **意图识别准确率**：正确识别动作类型（`bp_record` / `meal_add` / `sport_start` / `None`）的样本占总样本比例。
2. **误写库率（False Write Rate）**：包含生理越界、高低压颠倒、历史基线突变、低置信度反光读数或非法餐食热量的异常样本中，未经拦截或二次确认即直接写入数据库的比例。
3. **建议可溯源率**：系统输出建议中同时附带可核查的个人/家人历史记录编号（`[R-*]`）与权威公开指南条文编号（`[G-*]`）的比例。

## 三、典型 Bad Case 与立项后改进方向（驱动后续科研工作）

{bad_case_md}

本预实验已完成确定性文本解析、写前安全校验与指南溯源链路基线验证；`eval/sample_cases.json` 中已预置 `vision_annotation_template` 字段，立项后将扩充至 **200–300 张**真实拍摄的电子血压计屏幕与医院纸质体检单照片（按清晰、倾斜、反光、多栏、模糊五类难例分层），进一步开展“纯多模态大模型直出 vs 预处理 + 质量门控 + 基线约束”的字段级 Precision/Recall/F1 消融实验。
"""

    with open(REPORT_PATH, "w", encoding="utf-8") as handle:
        handle.write(report)

    print("=== Pilot Evaluation Summary (N=%d) ===" % total_n)
    print("Intent Accuracy : baseline %s -> upgraded %s" % (pct(intent_res["base_acc"]), pct(intent_res["new_acc"])))
    print("BP Recall       : baseline %s -> upgraded %s" % (pct(intent_res["base_bp_recall"]), pct(intent_res["new_bp_recall"])))
    print("Safety FalseWr  : baseline %s -> upgraded %s (F1=%s, FP=%d, FN=%d)" % (
        pct(safety_res["base_false_write_rate"]), pct(safety_res["new_false_write_rate"]),
        pct(safety_res["f1"]), safety_res["fp"], safety_res["fn"],
    ))
    print("Guideline Top-3 : %s | Urgent Safety: %s | Traceable: %s" % (
        pct(guide_res["recall_at_3"]), pct(guide_res["urgent_safety_rate"]), pct(guide_res["traceable_rate"]),
    ))
    if intent_res["bad_cases"]:
        print("Intent bad cases:", intent_res["bad_cases"])
    if safety_res["details"]:
        print("Safety details:", safety_res["details"])
    if guide_res["misses"]:
        print("Guideline misses:", guide_res["misses"])
    print("Report written to:", REPORT_PATH)


if __name__ == "__main__":
    main()
