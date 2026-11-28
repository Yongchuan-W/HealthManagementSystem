"""权威慢病与家庭健康指南知识库（轻量可溯源检索，零第三方依赖）。

所有条文均标注公开权威出处，用于在 AI 对话、体检解读与降级规则建议中提供可核查的依据编号，
降低大模型幻觉风险，并严格界定“健康科普与监测辅助，不构成医疗诊断”的安全边界。
"""

from __future__ import annotations

GUIDELINES = [
    {
        "id": "G-HTN-01",
        "source": "《中国高血压防治指南（2024年修订版）》",
        "title": "家庭自测血压诊断与控制目标",
        "keywords": ["血压", "高血压", "135", "85", "140", "90", "自测", "家庭血压", "达标", "偏高"],
        "summary": "家庭自测血压平均值 ≥135/85 mmHg 可提示高血压（对应诊室 ≥140/90 mmHg）；一般高血压患者家庭血压目标通常低于 135/85 mmHg，高龄老人可遵医嘱适当放宽。",
    },
    {
        "id": "G-HTN-02",
        "source": "《中国高血压防治指南（2024年修订版）》",
        "title": "规范家庭血压测量方法",
        "keywords": ["测血压", "测量", "晨起", "静坐", "姿势", "复测", "血压计", "不准", "波动"],
        "summary": "测量前安静休息 5 分钟，避免吸烟、饮茶/咖啡及排尿憋胀；采用上臂式电子血压计，袖带与心脏齐平；早晚各测 2–3 次取均值，并记录时段与服药状态。",
    },
    {
        "id": "G-HTN-03",
        "source": "《中国高血压防治指南（2024年修订版）》",
        "title": "降压药物依从性与漏服处理原则",
        "keywords": ["降压药", "服药", "漏服", "忘吃", "氨氯地平", "停药", "吃药", "用药"],
        "summary": "血压平稳后切勿自行停药或减量，以免引起血压反跳；若偶尔漏服，应参照药品说明书或咨询医生/药师，切忌擅自加倍补服。",
    },
    {
        "id": "G-HTN-04",
        "source": "《中国高血压防治指南（2024年修订版）》",
        "title": "血压急症警戒红线与就医指征",
        "keywords": ["180", "110", "头晕", "头痛", "胸闷", "胸痛", "心慌", "视物模糊", "急症", "就医", "偏低"],
        "summary": "若血压持续 ≥180/110 mmHg，或虽未达该值但伴明显头痛、胸痛、呼吸困难、肢体麻木、视物模糊或晕厥，须立即前往医院急诊，切勿在家观望。",
    },
    {
        "id": "G-HTN-05",
        "source": "《中国高血压防治指南（2024年修订版）》",
        "title": "高血压生活方式干预：限盐与限酒",
        "keywords": ["控盐", "吃盐", "限盐", "咸", "钠", "饮食", "高血压", "喝酒", "饮酒", "爸爸", "父母"],
        "summary": "推荐每日食盐摄入量逐步降至 <5 克，减少腌制食品、酱油及隐形盐摄入，适当增加新鲜蔬果与富钾食物（肾功能不全者遵医嘱）；限制饮酒并戒烟。",
    },
    {
        "id": "G-HTN-06",
        "source": "《中国高血压防治指南（2024年修订版）》",
        "title": "晨峰血压与连续趋势监测",
        "keywords": ["晨起", "早上", "晨峰", "连续", "趋势", "爸爸", "妈妈", "异地", "复诊"],
        "summary": "清晨起床后 1 小时内、服药前测得的血压最能反映降压方案覆盖情况；连续 7 天记录家庭血压并在复诊时提供趋势表，有助于医生调整方案。",
    },
    {
        "id": "G-DIET-01",
        "source": "《中国居民膳食指南（2022）》",
        "title": "食物多样与合理搭配",
        "keywords": ["饮食", "食物", "营养", "蔬菜", "蛋白质", "三餐", "早餐", "午餐", "晚餐", "食谱"],
        "summary": "平均每天摄入 12 种以上食物、每周 25 种以上；餐餐有蔬菜、天天吃水果，保证适量鱼禽蛋瘦肉与豆制品，主食注意全谷物和杂豆搭配。",
    },
    {
        "id": "G-DIET-02",
        "source": "《中国居民膳食指南（2022）》",
        "title": "少盐少油与控糖标准",
        "keywords": ["控盐", "油", "糖", "热量", "清淡", "外卖", "减脂", "减肥"],
        "summary": "成人每天食盐不超过 5g，烹调油 25–30g，添加糖控制在 25g 以下；减重期宜制造温和热量缺口（300–500 kcal/天），避免极端节食。",
    },
    {
        "id": "G-SPORT-01",
        "source": "《全民健身指南》/ WHO 身体活动指南",
        "title": "成人与慢病人群规律有氧运动建议",
        "keywords": ["运动", "跑步", "快走", "散步", "锻炼", "步数", "心率", "久坐", "力量"],
        "summary": "成人每周建议累计至少 150 分钟中等强度有氧运动（如快走、太极、骑行），搭配 2 次抗阻/拉伸；血压控制不稳定（≥160/100）时应先稳定血压再逐步恢复运动。",
    },
    {
        "id": "G-BMI-01",
        "source": "《成人体重判定》（WS/T 428-2013）",
        "title": "中国成人 BMI 与超重肥胖标准",
        "keywords": ["bmi", "体重", "肥胖", "超重", "偏瘦", "减肥", "体脂"],
        "summary": "中国成人健康体重 BMI 区间为 18.5–23.9 kg/m²，24.0–27.9 为超重，≥28.0 为肥胖；超重高血压患者每减重 5%–10% 通常有助于改善血压水平。",
    },
    {
        "id": "G-GLU-01",
        "source": "《中国2型糖尿病防治指南（2020年版）》",
        "title": "空腹血糖参考区间与监测建议",
        "keywords": ["血糖", "空腹血糖", "糖尿病", "低血糖", "妈妈", "甜食", "体检"],
        "summary": "正常空腹血糖参考范围为 3.9–6.1 mmol/L；空腹血糖 6.1–6.9 mmol/L 提示空腹血糖受损，≥7.0 mmol/L 建议尽快到内分泌科复核；低于 3.9 mmol/L 伴心慌出汗需及时补糖。",
    },
    {
        "id": "G-SLEEP-01",
        "source": "《健康中国行动（2019—2030年）》",
        "title": "成人规律睡眠与夜间血压关系",
        "keywords": ["睡眠", "失眠", "熬夜", "早醒", "睡不够", "入睡"],
        "summary": "倡导成人每日平均睡眠 7–8 小时；长期睡眠不足或夜间打鼾憋气与血压昼夜节律异常相关，建议固定作息并在持续失眠时就医评估。",
    },
    {
        "id": "G-REPORT-01",
        "source": "《体检报告健康管理应用规范》",
        "title": "体检异常指标分层随访原则",
        "keywords": ["体检", "报告", "异常", "复查", "尿酸", "血脂", "脂肪肝"],
        "summary": "单次体检轻度异常需结合生活方式调整并在 1–3 个月内复查趋势；多项关键指标显著异常或出现危急值时应携原始报告单至对应专科就诊。",
    },
    {
        "id": "G-SAFE-01",
        "source": "系统医疗安全合规边界",
        "title": "非医疗诊断与处方禁区声明",
        "keywords": ["药", "诊断", "治病", "剂量", "处方", "胸痛", "晕厥", "急诊"],
        "summary": "本系统所有 AI 分析与建议仅用于家庭健康监测与科普参考，不构成医疗诊断，不推荐具体处方药或调整用药剂量；症状明显或指标危急请及时线下就医。",
    },
]

URGENT_TRIGGERS = ("180", "110", "胸痛", "呼吸困难", "晕厥", "肢体麻木", "视物模糊", "剧烈头痛", "急诊")


def retrieve_guidelines(query, summary_text="", top_k=3):
    """按查询文本与健康档案摘要检索最相关的权威指南条文。"""
    q = str(query or "").lower()
    ctx = str(summary_text or "").lower()

    scored = []
    for item in GUIDELINES:
        score = 0
        for kw in item["keywords"]:
            k = kw.lower()
            if k in q:
                score += 5
            elif k in ctx:
                score += 1
        # 高血压/慢病场景适当优先
        if item["id"].startswith("G-HTN") and any(w in q for w in ("血压", "爸爸", "妈妈", "父母", "降压", "慢病")):
            score += 3
        if score > 0:
            scored.append((score, item))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    selected = [pair[1] for pair in scored[:top_k]]

    # 急症词命中时强制补充急症红线与安全声明
    if any(w in q or w in ctx for w in URGENT_TRIGGERS):
        ids = {item["id"] for item in selected}
        for must_id in ("G-HTN-04", "G-SAFE-01"):
            if must_id not in ids:
                found = next((g for g in GUIDELINES if g["id"] == must_id), None)
                if found:
                    selected.append(found)
                    ids.add(must_id)

    if not selected:
        selected = [GUIDELINES[0], GUIDELINES[6], GUIDELINES[-1]][:top_k]

    return selected


def format_guidelines_for_prompt(items):
    lines = []
    for item in (items or []):
        lines.append("[%s] %s《%s》：%s" % (
            item["id"], item["source"], item["title"], item["summary"]
        ))
    return "\n".join(lines)


def collect_record_refs(conn, uid, limit=6):
    """从数据库提取带可溯源编号的近期个人/家庭真实记录。"""
    refs = []
    # 1. 家庭成员慢病记录（优先血压与用药）
    fam_rows = conn.execute(
        "SELECT r.id, r.date, r.type, r.content, m.relation, m.name "
        "FROM family_records r LEFT JOIN family_members m ON r.member_id = m.id AND r.user_id = m.user_id "
        "WHERE r.user_id = ? ORDER BY r.date DESC, r.created_at DESC LIMIT 4",
        (uid,),
    ).fetchall()
    for row in fam_rows:
        who = row["relation"] or row["name"] or "家人"
        refs.append({
            "refId": "R-FAM-%s" % str(row["id"])[:6],
            "date": row["date"],
            "label": "%s · %s：%s" % (who, row["type"], row["content"] or ""),
        })

    # 2. 本人血压/血糖记录
    vital_rows = conn.execute(
        "SELECT id, type, date, text FROM vital_records "
        "WHERE user_id = ? AND type IN ('bp', 'glucose') ORDER BY date DESC, id DESC LIMIT 3",
        (uid,),
    ).fetchall()
    type_names = {"bp": "血压", "glucose": "空腹血糖"}
    for row in vital_rows:
        refs.append({
            "refId": "R-VIT-%s" % row["id"],
            "date": str(row["date"] or "")[:10],
            "label": "本人 · %s：%s" % (type_names.get(row["type"], row["type"]), row["text"] or ""),
        })

    # 3. 最近体重
    w_row = conn.execute(
        "SELECT id, date, weight FROM weight_records WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT 1",
        (uid,),
    ).fetchone()
    if w_row:
        refs.append({
            "refId": "R-WT-%s" % w_row["id"],
            "date": w_row["date"],
            "label": "本人 · 体重：%.1f kg" % w_row["weight"],
        })

    return refs[:limit]
