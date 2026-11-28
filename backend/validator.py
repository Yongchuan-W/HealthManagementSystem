"""写前安全校验、历史基线一致性比对与口语慢病信息解析（零第三方依赖）。

核心职责：
1. 血压生理边界钳制与历史基线突变检测，防止 OCR/视觉/语音误识别直接污染健康档案；
2. 餐食识别结果白名单裁剪、数值区间钳制与营养合计重算；
3. 从自然语言句子中抽取血压、脉搏、时段、服药状态及归属家庭成员，用于生成可编辑草稿。
"""

from __future__ import annotations

import re

BP_SYSTOLIC_MIN = 60
BP_SYSTOLIC_MAX = 260
BP_DIASTOLIC_MIN = 30
BP_DIASTOLIC_MAX = 160
BP_PULSE_MIN = 35
BP_PULSE_MAX = 200

BASELINE_DELTA_SYS = 25.0
BASELINE_DELTA_DIA = 15.0

MEAL_MAX_ITEMS = 12
MEAL_MAX_ITEM_KCAL = 3000.0
MEAL_MAX_TOTAL_KCAL = 5000.0
MEAL_MAX_MACRO = 500.0
MEAL_MAX_FIBER = 200.0


def _to_float(value):
    if value is None or value == "":
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if num != num:  # NaN
        return None
    return num


def classify_bp(systolic, diastolic):
    """参照《中国高血压防治指南（2024年修订版）》分级（含家庭自测阈值）。"""
    if systolic >= 180 or diastolic >= 110:
        return "急症警戒（≥180/110）", True, True
    if systolic >= 140 or diastolic >= 90:
        return "高血压范围（≥140/90）", True, False
    if systolic >= 135 or diastolic >= 85:
        return "家庭自测偏高（≥135/85）", True, False
    if systolic < 90 or diastolic < 60:
        return "偏低（<90/60）", True, False
    if systolic >= 120 or diastolic >= 80:
        return "正常高值（120-139/80-89）", False, False
    return "正常（<120/80）", False, False


def _extract_bp_pairs(recent_readings):
    pairs = []
    for item in (recent_readings or []):
        if isinstance(item, dict):
            s = _to_float(item.get("systolic"))
            d = _to_float(item.get("diastolic"))
            if s is None or d is None:
                text = str(item.get("text") or item.get("content") or "")
                m = re.search(r"(\d{2,3})\s*/\s*(\d{2,3})", text)
                if m:
                    s, d = float(m.group(1)), float(m.group(2))
            if s is not None and d is not None:
                if BP_SYSTOLIC_MIN <= s <= BP_SYSTOLIC_MAX and BP_DIASTOLIC_MIN <= d <= BP_DIASTOLIC_MAX and s > d:
                    pairs.append((s, d))
        elif isinstance(item, (tuple, list)) and len(item) >= 2:
            s, d = _to_float(item[0]), _to_float(item[1])
            if s is not None and d is not None and s > d:
                pairs.append((s, d))
    return pairs


def validate_bp(systolic, diastolic, pulse=None, recent_readings=None,
                image_quality=None, confidence=None):
    """对血压录入值进行生理边界校验、图像质量门控与历史基线一致性校验。"""
    s = _to_float(systolic)
    d = _to_float(diastolic)
    p = _to_float(pulse)
    conf = _to_float(confidence)

    errors = []
    warnings = []
    requires_double_confirm = False

    if s is None or d is None:
        errors.append("缺少有效的收缩压或舒张压数值")
    else:
        if not (BP_SYSTOLIC_MIN <= s <= BP_SYSTOLIC_MAX):
            errors.append("收缩压 %.0f 超出合理生理范围（%d–%d mmHg）"
                          % (s, BP_SYSTOLIC_MIN, BP_SYSTOLIC_MAX))
        if not (BP_DIASTOLIC_MIN <= d <= BP_DIASTOLIC_MAX):
            errors.append("舒张压 %.0f 超出合理生理范围（%d–%d mmHg）"
                          % (d, BP_DIASTOLIC_MIN, BP_DIASTOLIC_MAX))
        if s <= d:
            errors.append("收缩压（%.0f）必须大于舒张压（%.0f），疑似读数颠倒" % (s, d))
        elif (s - d) < 15:
            warnings.append("脉压差过小（%.0f mmHg），请确认读数是否准确" % (s - d))
            requires_double_confirm = True

    if p is not None and not (BP_PULSE_MIN <= p <= BP_PULSE_MAX):
        errors.append("心率 %.0f 超出合理范围（%d–%d 次/分）" % (p, BP_PULSE_MIN, BP_PULSE_MAX))

    if errors:
        return {
            "valid": False,
            "blocked": True,
            "abnormal": False,
            "urgent": False,
            "level": "非法数值（已拦截）",
            "requiresDoubleConfirm": True,
            "shouldCreateCollabTask": False,
            "errors": errors,
            "warnings": warnings,
            "baseline": None,
        }

    level, abnormal, urgent = classify_bp(s, d)
    if urgent:
        warnings.append("血压达到 ≥180/110 mmHg 警戒线，如伴头痛、胸闷、视物模糊请立即就医。")
        requires_double_confirm = True
    elif abnormal:
        warnings.append("当前读数处于「%s」，建议静坐 5 分钟后复测并核对今日服药情况。" % level)

    # 图像质量与置信度门控
    quality_text = str(image_quality or "").strip()
    if quality_text and any(k in quality_text for k in ("重拍", "模糊", "反光", "倾斜", "看不清")):
        warnings.append("图像质量提示「%s」，请人工核对屏幕数字后再确认写入。" % quality_text)
        requires_double_confirm = True
    if conf is not None and conf < 0.75:
        warnings.append("模型识别置信度偏低（%.0f%%），请务必核对后再保存。" % (conf * 100))
        requires_double_confirm = True

    # 历史基线一致性校验（取最近 7 条有效记录）
    pairs = _extract_bp_pairs(recent_readings)[-7:]
    baseline = None
    if pairs:
        mean_s = sum(item[0] for item in pairs) / len(pairs)
        mean_d = sum(item[1] for item in pairs) / len(pairs)
        delta_s = round(s - mean_s, 1)
        delta_d = round(d - mean_d, 1)
        baseline = {
            "count": len(pairs),
            "meanSystolic": round(mean_s, 1),
            "meanDiastolic": round(mean_d, 1),
            "deltaSystolic": delta_s,
            "deltaDiastolic": delta_d,
            "deviationAlert": False,
        }
        if abs(delta_s) >= BASELINE_DELTA_SYS or abs(delta_d) >= BASELINE_DELTA_DIA:
            baseline["deviationAlert"] = True
            requires_double_confirm = True
            direction = "升高" if delta_s >= 0 else "下降"
            warnings.append(
                "较近 %d 次均值（%.0f/%.0f）%s幅度较大（高压 %+.0f / 低压 %+.0f mmHg），请确认是否误读或存在漏服药/情绪波动。"
                % (len(pairs), mean_s, mean_d, direction, delta_s, delta_d)
            )

    should_collab = bool(abnormal or (baseline and baseline["deviationAlert"]))
    return {
        "valid": True,
        "blocked": False,
        "abnormal": abnormal,
        "urgent": urgent,
        "level": level,
        "requiresDoubleConfirm": requires_double_confirm,
        "shouldCreateCollabTask": should_collab,
        "errors": [],
        "warnings": warnings,
        "baseline": baseline,
    }


def clamp_meal_items(items, max_items=MEAL_MAX_ITEMS):
    """对餐食识别/AI估算结果执行白名单字段裁剪、数值区间钳制与营养合计重算。"""
    cleaned = []
    dropped = 0
    clamped = 0

    for raw in (items or []):
        if not isinstance(raw, dict):
            dropped += 1
            continue
        name = str(raw.get("name") or "").strip()[:30]
        if not name:
            dropped += 1
            continue
        if len(cleaned) >= max_items:
            dropped += 1
            continue

        portion = str(raw.get("portion") or "1 份").strip()[:24]

        def _clamp(val, hi, is_int=False):
            nonlocal clamped
            num = _to_float(val)
            if num is None:
                return 0
            orig = num
            if num < 0:
                num = 0.0
            if num > hi:
                num = hi
            if num != orig:
                clamped += 1
            return int(round(num)) if is_int else round(num, 1)

        cleaned.append({
            "name": name,
            "portion": portion,
            "kcal": _clamp(raw.get("kcal"), MEAL_MAX_ITEM_KCAL, is_int=True),
            "protein": _clamp(raw.get("protein"), MEAL_MAX_MACRO),
            "carb": _clamp(raw.get("carb"), MEAL_MAX_MACRO),
            "fat": _clamp(raw.get("fat"), MEAL_MAX_MACRO),
            "fiber": _clamp(raw.get("fiber"), MEAL_MAX_FIBER),
        })

    total_kcal = min(MEAL_MAX_TOTAL_KCAL, sum(x["kcal"] for x in cleaned))
    total = {
        "kcal": round(total_kcal, 1),
        "protein": round(min(MEAL_MAX_MACRO, sum(x["protein"] for x in cleaned)), 1),
        "carb": round(min(MEAL_MAX_MACRO, sum(x["carb"] for x in cleaned)), 1),
        "fat": round(min(MEAL_MAX_MACRO, sum(x["fat"] for x in cleaned)), 1),
        "fiber": round(min(MEAL_MAX_FIBER, sum(x["fiber"] for x in cleaned)), 1),
    }
    return {
        "foods": cleaned,
        "total": total,
        "droppedCount": dropped,
        "clampedCount": clamped,
    }


MEMBER_PATTERNS = (
    ("爸爸", ("爸爸", "父亲", "老爸", "我爸")),
    ("妈妈", ("妈妈", "母亲", "老妈", "我妈")),
    ("爷爷", ("爷爷", "祖父")),
    ("奶奶", ("奶奶", "祖母")),
    ("外公", ("外公", "姥爷")),
    ("外婆", ("外婆", "姥姥")),
)


def parse_bp_from_text(text):
    """从中文口语中解析血压、心率、时段、服药状态与家庭成员，未命中返回 None。"""
    raw = str(text or "").strip()
    if not raw:
        return None

    systolic = None
    diastolic = None

    # 形态 1：148/92 或 148 / 92
    m = re.search(r"(\d{2,3})\s*[/／]\s*(\d{2,3})", raw)
    if m:
        systolic, diastolic = int(m.group(1)), int(m.group(2))
    else:
        # 形态 2：高压 146 低压 90 / 收缩压 142 舒张压 88
        ms = re.search(r"(?:高压|收缩压)\s*(?:是|为|约|大概)?\s*(\d{2,3})", raw)
        md = re.search(r"(?:低压|舒张压)\s*(?:是|为|约|大概)?\s*(\d{2,3})", raw)
        if ms and md:
            systolic, diastolic = int(ms.group(1)), int(md.group(1))

    if systolic is None or diastolic is None:
        return None

    # 必须包含血压上下文词或明确像血压记录，避免误匹配日期
    bp_hints = ("血压", "高压", "低压", "收缩压", "舒张压", "mmhg", "测了", "刚测", "早上测", "晚上测")
    if not any(k in raw.lower() for k in bp_hints):
        # 排除明显像日期 11/28 的低数值组合
        if systolic < 70 or diastolic < 40:
            return None

    pulse = None
    mp = re.search(r"(?:心率|脉搏)\s*(?:是|为)?\s*(\d{2,3})", raw)
    if mp:
        pulse = int(mp.group(1))

    period = "晨起"
    if any(k in raw for k in ("晚上", "晚间", "睡前", "今晚", "昨晚")):
        period = "晚间"
    elif any(k in raw for k in ("中午", "下午", "午后")):
        period = "午后"
    elif any(k in raw for k in ("早上", "早晨", "晨起", "今早", "昨早", "起床")):
        period = "晨起"

    med_status = "未说明"
    if any(k in raw for k in ("忘吃", "没吃药", "漏服", "未服药", "忘了吃")):
        med_status = "未服药/漏服"
    elif any(k in raw for k in ("吃了药", "已服药", "吃了降压药", "服了", "氨氯地平", "缬沙坦", "硝苯地平", "吃过药")):
        med_status = "已服药"

    member = "本人"
    for canonical, aliases in MEMBER_PATTERNS:
        if any(a in raw for a in aliases):
            member = canonical
            break

    symptom = ""
    symptoms = [w for w in ("头晕", "头痛", "胸闷", "心慌", "乏力", "视物模糊", "耳鸣", "恶心") if w in raw]
    if symptoms:
        symptom = "、".join(symptoms)

    return {
        "systolic": systolic,
        "diastolic": diastolic,
        "pulse": pulse,
        "measuredPeriod": period,
        "medStatus": med_status,
        "member": member,
        "symptom": symptom,
    }
