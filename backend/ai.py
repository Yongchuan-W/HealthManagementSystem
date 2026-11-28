"""AI 健康助手：调用 OpenAI 兼容的对话接口，默认接入 DeepSeek。

配置优先级：环境变量 > 项目根目录 ai_local.env（该文件已被 .gitignore 忽略）。
换成豆包方舟或其它兼容服务时，只需改 HM_AI_API_BASE 与 HM_AI_MODEL。

未配置密钥或调用失败时返回兜底文本（degraded=True），前端据此提示为规则建议。
"""

from __future__ import annotations

import base64
import json
import os
import re
import time
import urllib.error
import urllib.request

from . import guidelines, telemetry, validator

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_ENV_PATH = os.path.join(BASE_DIR, "ai_local.env")

DEFAULT_API_BASE = "https://api.deepseek.com/v1"
DEFAULT_MODEL = "deepseek-flash"

MAX_HISTORY = 8          # 最多带最近 8 条历史消息，控制费用与延迟
TIMEOUT = 20             # 单次请求超时（秒）
MAX_TOKENS = 800

VISION_TIMEOUT = 60      # 图片识别更慢，单独放宽超时
VISION_MAX_TOKENS = 1200

PLACEHOLDER_REPLY = (
    "AI 健康助手接口已经就绪，但目前还没有配置大模型密钥。"
    "配置后，这里会根据你的体重、饮食、运动与睡眠数据给出个性化建议。"
)

FALLBACK_REPLY = (
    "AI 服务暂时不可用（{reason}）。你可以先记录今天的饮食、运动和睡眠，稍后再问我；"
    "如有明显不适，建议及时就医。"
)

SYSTEM_PROMPT = (
    "你是「健康小管家」，面向普通用户的健康生活助手。"
    "回答要求：中文、简洁、分点作答，先给结论再给理由；建议围绕饮食、运动、睡眠和压力管理。"
    "安全边界：不做疾病诊断，不推荐处方药或具体用药剂量；遇到胸痛、呼吸困难、晕厥、持续高热、"
    "孕产异常等紧急情况，必须建议尽快就医。"
    "用户数据仅作参考，不要编造数值；信息不足时先问一个关键问题。"
)

PAGE_GUIDE = (
    "本网站功能说明（用户问「怎么用」时据此回答）：\n"
    "1. 左侧导航依次是健康数据、饮食、运动、家人健康、健康小管家、科普资讯。\n"
    "2. 健康数据：点顶部三条评分或数据卡片可录入血压、血糖、体重等，输入后自动计算 BMI 与正常范围。\n"
    "3. 饮食：在早餐/午餐/晚餐输入框写食物名并回车，系统会查食物库；查不到时由 AI 估算热量，确认份数后保存。\n"
    "4. 运动：先设目标，再点运动类型开始计时，结束自动累计时长和热量；也可点数据卡片手动填写。\n"
    "5. 家人健康：添加家人、记录指标、设置提醒。\n"
    "6. 科普资讯：可搜索关键词、点热门标签、点「刷新」获取新的新闻，点卡片跳浏览器看全文。\n"
    "7. 语音输入：先点一下要填写的输入框，再点左下角「语音输入」按钮说话，识别结果会自动填入；需要 HTTPS 和浏览器支持。\n"
    "8. 健康小管家：可以问健康问题，也可以直接下指令，例如「我要开始跑步，帮我记录一下」"
    "或「我吃了螺蛳粉，帮我记到晚餐」，系统会自动执行。\n"
    "9. 账号：登录页可注册新账号；个人信息弹窗底部可退出登录或注销账号（会删除全部数据）。\n"
)


class AiError(Exception):
    """模型调用失败（网络、鉴权、返回格式等）。"""


def _load_local_env():
    """把 ai_local.env 的键值写入环境变量；已存在的环境变量优先。"""
    if not os.path.isfile(LOCAL_ENV_PATH):
        return
    with open(LOCAL_ENV_PATH, "r", encoding="utf-8-sig") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


_load_local_env()


def config():
    """读取配置；未配置密钥（或仍是模板占位）时返回 None。"""
    api_key = os.environ.get("HM_AI_API_KEY", "").strip()
    if not api_key or api_key == "sk-xxx":
        return None
    return {
        "api_base": (os.environ.get("HM_AI_API_BASE", DEFAULT_API_BASE).strip()
                     or DEFAULT_API_BASE).rstrip("/"),
        "api_key": api_key,
        "model": os.environ.get("HM_AI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
    }


def is_configured():
    return config() is not None


def provider_name(settings=None):
    settings = settings or config()
    if not settings:
        return None
    base = settings["api_base"].lower()
    if "deepseek" in base:
        return "deepseek"
    if "volces" in base or "ark" in base:
        return "doubao"
    return "openai-compatible"


def _build_messages(message, history, context, guideline_items=None, record_refs=None):
    system = SYSTEM_PROMPT + "\n\n" + PAGE_GUIDE
    if context:
        system += "\n用户健康数据摘要（仅供参考，严禁编造未出现的数值）：\n" + str(context).strip()
    if record_refs:
        ref_lines = "\n".join(
            "[%s] %s %s" % (r.get("refId"), r.get("date") or "", r.get("label") or "")
            for r in record_refs[:6]
        )
        system += "\n可溯源的个人/家庭近期记录（回答须优先立足这些真实记录，可引用编号）：\n" + ref_lines
    if guideline_items:
        system += (
            "\n权威参考指南条文（建议须与以下规范保持一致，可引用对应编号如 [G-HTN-01]）：\n"
            + guidelines.format_guidelines_for_prompt(guideline_items)
        )

    messages = [{"role": "system", "content": system}]
    for item in (history or [])[-MAX_HISTORY:]:
        role = item.get("role")
        content = (item.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})
    return messages


def _post(settings, payload, timeout=TIMEOUT, not_found_hint="", kind="chat"):
    """包一层计时与监控，真实请求在 _post_raw 里。"""
    started = time.time()
    try:
        result = _post_raw(settings, payload, timeout, not_found_hint)
    except AiError as error:
        telemetry.record_ai((time.time() - started) * 1000, False,
                            settings.get("model", ""), kind, str(error))
        raise
    telemetry.record_ai((time.time() - started) * 1000, True,
                        settings.get("model", ""), kind)
    return result


def _post_raw(settings, payload, timeout=TIMEOUT, not_found_hint=""):
    """向兼容 OpenAI 的服务发请求，返回解析后的 JSON。"""
    request = urllib.request.Request(
        settings["api_base"] + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + settings["api_key"],
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = ""
        try:
            data = json.loads(error.read().decode("utf-8"))
            detail = (data.get("error") or {}).get("message") or data.get("message") or ""
        except Exception:
            detail = ""
        if error.code == 401:
            raise AiError("密钥无效或已过期")
        if error.code == 402:
            raise AiError("账户余额不足")
        if error.code == 404:
            raise AiError(not_found_hint or "接口不存在，请确认 HM_AI_API_BASE 与 HM_AI_MODEL")
        if error.code == 429:
            raise AiError("调用过于频繁，请稍后再试")
        raise AiError("模型服务返回 %d%s" % (error.code, ("：" + detail) if detail else ""))
    except urllib.error.URLError as error:
        raise AiError("无法连接模型服务：%s" % getattr(error, "reason", error))
    except (ValueError, json.JSONDecodeError):
        raise AiError("模型返回内容无法解析")


def _message_text(body):
    choices = body.get("choices") or []
    if not choices:
        raise AiError("模型没有返回内容")
    text = ((choices[0].get("message") or {}).get("content") or "").strip()
    if not text:
        raise AiError("模型返回内容为空")
    return text


def _request_model(settings, messages):
    return _message_text(_post(settings, {
        "model": settings["model"],
        "messages": messages,
        "temperature": 0.6,
        "max_tokens": MAX_TOKENS,
        "stream": False,
    }))


def _degraded_grounded_reply(message, guideline_items=None, record_refs=None, reason=None):
    """未配置密钥或外部模型不可用时，基于本地指南库与真实记录返回可溯源降级建议。"""
    lines = []
    if reason:
        lines.append("（外部大模型暂时不可用：%s，已自动切换至本地可溯源规则建议）" % reason)
    else:
        lines.append("（当前为本地可溯源规则建议模式）")
    step = 1
    if record_refs:
        latest = record_refs[0]
        lines.append("%d. 结合近期真实记录 [%s]（%s %s）：建议持续观察近 7 天变化趋势并核对服药与作息情况。" % (
            step, latest.get("refId"), latest.get("date") or "", latest.get("label") or ""
        ))
        step += 1
    if guideline_items:
        for item in guideline_items[:2]:
            lines.append("%d. 参考 [%s] %s：%s" % (
                step, item["id"], item["source"], item["summary"]
            ))
            step += 1
    else:
        lines.append(PLACEHOLDER_REPLY)
    lines.append("安全边界：以上内容仅用于健康监测与科普参考，不构成医疗诊断；若伴明显不适或血压 ≥180/110 mmHg 请及时就医。")
    return "\n".join(lines)


def generate_reply(message, history=None, context=None, guideline_items=None, record_refs=None):
    """调用大模型，返回 (回复文本, 元信息)。

    元信息：configured（是否配置了密钥）、degraded（是否走了兜底）、
            model、provider、error（失败原因）。
    """
    settings = config()
    if settings is None:
        return _degraded_grounded_reply(message, guideline_items, record_refs), {
            "configured": False, "degraded": True,
            "model": None, "provider": None, "error": "未配置 HM_AI_API_KEY",
        }

    try:
        text = _request_model(
            settings,
            _build_messages(message, history, context, guideline_items, record_refs),
        )
    except AiError as error:
        return _degraded_grounded_reply(message, guideline_items, record_refs, reason=error), {
            "configured": True, "degraded": True,
            "model": settings["model"], "provider": provider_name(settings),
            "error": str(error),
        }

    return text, {
        "configured": True, "degraded": False,
        "model": settings["model"], "provider": provider_name(settings), "error": None,
    }


# ==========================================================
# 指令识别：让用户一句话就能触发动作（不额外消耗模型额度）
# ==========================================================
SPORT_KEYWORDS = (
    "跑步", "慢跑", "健走", "快走", "户外骑行", "骑行", "徒步", "游泳", "瑜伽",
    "跳绳", "力量训练", "健身操", "篮球", "羽毛球", "足球", "乒乓球", "太极",
    "八段锦", "拉伸", "登山", "爬楼梯", "舞蹈",
)
SPORT_HINTS = ("开始", "记录", "打卡", "帮我记")
MEAL_HINTS = ("记录", "帮我", "填入", "填到", "记一下", "加进", "记入")


QUESTION_HINTS = ("吗", "？", "?", "能不能", "可以吃", "适合", "推荐", "怎么办", "怎么吃", "为什么", "多少")


def detect_action(message):
    """从用户原话中识别可执行动作，返回 dict 或 None。

    - bp_record：解析血压/心率/服药/成员，返回待确认草稿动作（不盲目落库）
    - sport_start：开始一项运动计时
    - meal_add：把饮食描述写入某一餐
    """
    text = str(message or "").strip()
    if not text or len(text) > 500:
        return None

    is_question = any(q in text for q in QUESTION_HINTS)

    bp = validator.parse_bp_from_text(text)
    if bp and (not is_question or any(h in text for h in ("记", "帮我", "刚测", "测了", "录入"))):
        action = {"type": "bp_record"}
        action.update(bp)
        return action

    if is_question:
        return None

    sport = next((name for name in SPORT_KEYWORDS if name in text), None)
    if sport and any(hint in text for hint in SPORT_HINTS):
        return {"type": "sport_start", "sport": sport}

    meal_words = ("早餐", "午餐", "晚餐", "早饭", "午饭", "晚饭", "加餐", "夜宵")
    has_eat = any(word in text for word in ("吃", "喝"))
    has_meal = any(word in text for word in meal_words)
    if (has_eat or has_meal) and (any(hint in text for hint in MEAL_HINTS) or (has_eat and has_meal)):
        meal = "加餐"
        mapping = {
            "早餐": "早餐", "早饭": "早餐",
            "午餐": "午餐", "午饭": "午餐",
            "晚餐": "晚餐", "晚饭": "晚餐", "夜宵": "晚餐",
            "加餐": "加餐",
        }
        for key, target in mapping.items():
            if key in text:
                meal = target
                break
        cleaned = re.sub(r"^(帮我|请|麻烦)?(记录一下|记录|填入|记一下|记入)?", "", text)
        cleaned = cleaned.strip("，,。 ")
        return {"type": "meal_add", "meal": meal, "text": cleaned or text}

    return None


# ==========================================================
# 食物热量估算（纯文本）
# ==========================================================
FOOD_SYSTEM = (
    "你是注册营养师，擅长按常见中式饮食估算热量。"
    "必须严格按要求只输出一个 JSON 对象，不要输出解释、Markdown 或代码块标记。"
)

FOOD_PROMPT = (
    "食物：%s\n"
    "用户可能一次输入多种食物（用逗号、顿号、空格分隔），必须逐个拆开分别估算，"
    "不能合并成一种、不能漏掉任何一项，输出顺序与输入一致；没写分量按常见一人份估算。\n"
    "数值必须参照《中国食物成分表（第6版）》与 USDA FoodData Central 的标准值，"
    "份量固定按常见一人份（如一碗米饭 150g、一个鸡蛋 50g），不要自由发挥。\n"
    "只输出 JSON，不要解释："
    '{"foods":[{"name":"白菜","portion":"半碗约75g","kcal":10,'
    '"protein":1,"carb":2,"fat":0,"fiber":1},'
    '{"name":"红烧肉","portion":"3块约80g","kcal":280,"protein":12,"carb":4,"fat":24,"fiber":0}]}\n'
    "kcal 为千卡，其余为克，全部用数字。1～8 种。"
)


def estimate_food(text):
    """用模型估算任意食物的热量，返回 (JSON dict, 元信息)。"""
    text = (text or "").strip()
    if not text:
        raise AiError("请先输入食物名称")

    settings = config()
    if settings is None:
        raise AiError("未配置 HM_AI_API_KEY")

    body = _post(settings, {
        "model": settings["model"],
        "messages": [
            {"role": "system", "content": FOOD_SYSTEM},
            {"role": "user", "content": FOOD_PROMPT % text},
        ],
        "temperature": 0,
        # 推理类模型会先输出思考过程，额度给小了正文会为空
        "max_tokens": 2000,
        "stream": False,
    }, timeout=30, not_found_hint="当前模型不可用，请确认 HM_AI_MODEL",
        kind="食物热量估算")

    return parse_json_object(_message_text(body)), {
        "model": settings["model"],
        "provider": provider_name(settings),
    }


# ==========================================================
# 图片识别（多模态）
# ==========================================================
VISION_SYSTEM = (
    "你是健康数据识别助手。必须严格按要求只输出一个 JSON 对象，不要输出解释、Markdown 或代码块标记；"
    "看不清或不确定的字段填 null，不要编造。"
)

VISION_PROMPTS = {
    "meal": (
        "识别这张餐食图片里的食物，输出 JSON：\n"
        '{"foods":[{"name":"食物名","portion":"分量描述","kcal":数字}],'
        '"total":{"kcal":数字,"protein":数字,"carb":数字,"fat":数字,"fiber":数字},'
        '"note":"估算说明"}\n'
        "要求：热量单位 kcal、营养素单位克；按常见中式分量估算；最多 12 项；"
        "看不清时在 note 里说明。"
    ),
    "report": (
        "识别这张体检报告图片，输出 JSON：\n"
        '{"date":"YYYY-MM-DD 或 null","weight":数字或null,"fat":数字或null,"bmi":数字或null,'
        '"systolic":数字或null,"diastolic":数字或null,"glucose":数字或null,'
        '"items":[{"name":"指标名","value":"数值","unit":"单位","ref":"参考范围","abnormal":true或false}],'
        '"abnormal":["异常项描述"]}\n'
        "要求：体重单位 kg、体脂率单位 %、血糖单位 mmol/L、血压单位为 mmHg；"
        "报告上没有的字段填 null；最多 60 条指标。"
    ),
    "bp_meter": (
        "识别这张家用电子血压计屏幕照片上的读数，只输出一个 JSON 对象：\n"
        '{"systolic":数字或null,"diastolic":数字或null,"pulse":数字或null,'
        '"measuredPeriod":"晨起|午后|晚间|未知",'
        '"imageQuality":"清晰|轻微模糊|反光或倾斜建议重拍",'
        '"confidence":0.0到1.0之间的数字,"note":"简短说明"}\n'
        "要求：systolic 为高压/收缩压（mmHg），diastolic 为低压/舒张压（mmHg），pulse 为心率/脉搏（次/分）。"
        "若屏幕反光、严重倾斜或数字残缺无法辨认，对应字段必须填 null 并在 imageQuality 中填「反光或倾斜建议重拍」，切勿臆造数字。"
    ),
}


def parse_json_object(text):
    """从模型输出中提取 JSON 对象，容忍 ``` 包裹与前后多余文字。"""
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1] if "\n" in raw else raw
        if raw.rstrip().endswith("```"):
            raw = raw.rstrip()[:-3]
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        raise AiError("模型没有返回可解析的数据")
    try:
        data = json.loads(raw[start:end + 1])
    except ValueError:
        raise AiError("模型返回的数据无法解析")
    if not isinstance(data, dict):
        raise AiError("模型返回的数据格式不正确")
    return data


def vision(image_bytes, mime, task):
    """识别餐食图片或体检报告，返回 (JSON dict, 元信息)。"""
    if task not in VISION_PROMPTS:
        raise AiError("不支持的识别类型")
    if not image_bytes:
        raise AiError("图片内容为空")

    settings = config()
    if settings is None:
        raise AiError("未配置 HM_AI_API_KEY")

    mime = mime if str(mime).startswith("image/") else "image/jpeg"
    data_url = "data:%s;base64,%s" % (mime, base64.b64encode(image_bytes).decode("ascii"))

    messages = [
        {"role": "system", "content": VISION_SYSTEM},
        {"role": "user", "content": [
            {"type": "text", "text": VISION_PROMPTS[task]},
            {"type": "image_url", "image_url": {"url": data_url}},
        ]},
    ]

    body = _post(settings, {
        "model": settings["model"],
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": VISION_MAX_TOKENS,
        "stream": False,
    }, timeout=VISION_TIMEOUT,
        not_found_hint="当前模型不支持图片识别，请确认 HM_AI_MODEL 为多模态模型",
        kind="图片识别")

    return parse_json_object(_message_text(body)), {
        "configured": True,
        "model": settings["model"],
        "provider": provider_name(settings),
    }


# ==========================================================
# 体检报告 AI 解读：Function Calling + 流式输出
# ==========================================================
REPORT_PLAN_SYSTEM = (
    "你是「AI 健康干预教练」，服务对象是拿到体检报告但看不懂的普通人。"
    "你的任务是把报告翻译成可执行的饮食、运动与复查建议。\n"
    "安全边界：不做疾病诊断，不推荐处方药或具体剂量；指标明显异常时提示尽快到相应科室复查。\n"
    "只能输出一个 JSON 对象，不要 Markdown、不要代码块、不要任何解释。字段如下：\n"
    '{"summary":"一句话总结报告与干预方向",'
    '"riskLevel":"低风险|中风险|高风险",'
    '"risks":[{"name":"尿酸偏高","level":"偏高","value":"486 μmol/L","advice":"可执行建议"}],'
    '"diet":{"kcal":1680,"principle":"低嘌呤、控糖、优质蛋白",'
    '"meals":[{"name":"早餐","kcal":420,"items":["食物与分量"],"tip":"小贴士"}],'
    '"avoid":["动物内脏","浓肉汤"]},'
    '"exercise":{"goal":"每周 150 分钟中等强度有氧",'
    '"weekly":[{"day":"周一","type":"快走","duration":"30 分钟","note":"注意事项"}],'
    '"caution":["避免突然剧烈运动"]},'
    '"citations":["《中国居民膳食指南(2022)》","《内科学（第9版）》"],'
    '"disclaimer":"本建议仅用于健康管理，不构成医疗诊断，异常指标请遵医嘱复查。"}\n'
    "要求：risks 1-5 条；meals 3-4 条；weekly 4-5 条；avoid 3-5 条；"
    "所有数值必须来自报告或工具结果，不要编造；语气口语化、具体到食物和分钟。"
)

REPORT_PLAN_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculate_bmi",
            "description": "根据体重（kg）和身高（cm）计算 BMI，并给出体重分级与健康体重区间。",
            "parameters": {
                "type": "object",
                "properties": {
                    "weight": {"type": "number", "description": "体重，单位 kg"},
                    "height": {"type": "number", "description": "身高，单位 cm"},
                },
                "required": ["weight", "height"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_recipe",
            "description": "按每日目标热量生成三餐热量分配，供后续给出中式食谱。",
            "parameters": {
                "type": "object",
                "properties": {
                    "calories": {"type": "number", "description": "每日目标热量，单位 kcal"},
                    "avoid": {"type": "string", "description": "需要避开的食物，例如高嘌呤食物"},
                },
                "required": ["calories"],
            },
        },
    },
]

TOOL_LABELS = {
    "calculate_bmi": "计算 BMI 与体重分级",
    "generate_recipe": "生成每日热量分配",
}


def tool_calculate_bmi(arguments):
    weight = float(arguments.get("weight") or 0)
    height = float(arguments.get("height") or 0)
    if weight <= 0 or height <= 0:
        raise AiError("calculate_bmi 参数不完整")
    height_m = height / 100.0
    bmi = weight / (height_m * height_m)
    if bmi < 18.5:
        level = "偏瘦"
    elif bmi < 24:
        level = "正常"
    elif bmi < 28:
        level = "超重"
    else:
        level = "肥胖"
    low = round(18.5 * height_m * height_m, 1)
    high = round(23.9 * height_m * height_m, 1)
    return {
        "bmi": round(bmi, 1),
        "level": level,
        "healthyWeight": "%s-%s kg" % (low, high),
    }


def tool_generate_recipe(arguments):
    try:
        calories = float(arguments.get("calories") or 1600)
    except (TypeError, ValueError):
        calories = 1600
    calories = max(800, min(4000, calories))
    return {
        "targetKcal": int(round(calories)),
        "split": {
            "早餐": int(round(calories * 0.3)),
            "午餐": int(round(calories * 0.4)),
            "晚餐": int(round(calories * 0.3)),
        },
        "avoid": str(arguments.get("avoid") or "").strip()[:60],
    }


def _run_tool(name, arguments):
    if name == "calculate_bmi":
        return tool_calculate_bmi(arguments)
    if name == "generate_recipe":
        return tool_generate_recipe(arguments)
    raise AiError("未知工具：%s" % name)


def _stream_completion(settings, payload, on_delta, timeout=60, kind="体检解读"):
    """以 stream=true 请求模型，逐段回调增量文本，返回完整内容。"""
    payload = dict(payload)
    payload["stream"] = True
    started = time.time()
    request = urllib.request.Request(
        settings["api_base"] + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + settings["api_key"],
            "Accept": "text/event-stream",
        },
        method="POST",
    )

    chunks = []
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            for raw in response:
                line = raw.decode("utf-8", "ignore").strip()
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    event = json.loads(data)
                except ValueError:
                    continue
                choices = event.get("choices") or []
                if not choices:
                    continue
                delta = (choices[0].get("delta") or {}).get("content") or ""
                if delta:
                    chunks.append(delta)
                    on_delta(delta)
    except urllib.error.HTTPError as error:
        detail = ""
        try:
            data = json.loads(error.read().decode("utf-8"))
            detail = (data.get("error") or {}).get("message") or data.get("message") or ""
        except Exception:
            detail = ""
        telemetry.record_ai((time.time() - started) * 1000, False,
                            settings.get("model", ""), kind, "HTTP %s" % error.code)
        if error.code == 401:
            raise AiError("密钥无效或已过期")
        if error.code == 402:
            raise AiError("账户余额不足")
        if error.code == 429:
            raise AiError("调用过于频繁，请稍后再试")
        raise AiError("模型服务返回 %d%s" % (error.code, ("：" + detail) if detail else ""))
    except urllib.error.URLError as error:
        telemetry.record_ai((time.time() - started) * 1000, False,
                            settings.get("model", ""), kind, "网络错误")
        raise AiError("无法连接模型服务：%s" % getattr(error, "reason", error))

    text = "".join(chunks).strip()
    telemetry.record_ai((time.time() - started) * 1000, bool(text),
                        settings.get("model", ""), kind, None if text else "空内容")
    if not text:
        raise AiError("模型没有返回内容")
    return text


def stream_report_plan(report, profile, emit):
    """体检报告 → 结构化干预方案。

    emit(event, data) 依次推送 stage / tool / delta / plan 事件：
      - stage：当前阶段文案
      - tool：真实执行的 Function Calling 结果
      - delta：模型流式增量文本
      - plan：最终结构化方案
    """
    settings = config()
    if settings is None:
        raise AiError("未配置 HM_AI_API_KEY")

    profile = dict(profile or {})
    height = None
    for key in ("height",):
        try:
            value = float(profile.get(key) or 0)
        except (TypeError, ValueError):
            value = 0
        height = value or None

    metrics = {
        "weight": report.get("weight"),
        "fat": report.get("fat"),
        "bmi": report.get("bmi"),
        "systolic": report.get("systolic"),
        "diastolic": report.get("diastolic"),
        "glucose": report.get("glucose"),
        "abnormal": report.get("abnormal") or [],
        "items": (report.get("items") or [])[:20],
        "height": height,
        "gender": profile.get("gender"),
    }

    messages = [
        {"role": "system", "content": REPORT_PLAN_SYSTEM},
        {"role": "user", "content": "体检报告识别结果与用户基础信息：\n" +
         json.dumps(metrics, ensure_ascii=False)},
    ]

    emit("stage", {"text": "正在读取报告指标，规划干预方案…"})

    # 第一轮：把工具 schema 交给模型，按需触发 Function Calling
    body = _post(settings, {
        "model": settings["model"],
        "messages": messages,
        "tools": REPORT_PLAN_TOOLS,
        "tool_choice": "auto",
        "temperature": 0.2,
        "max_tokens": 800,
        "stream": False,
    }, timeout=45, kind="体检解读工具")

    choice = (body.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    tool_calls = message.get("tool_calls") or []

    if tool_calls:
        messages.append({
            "role": "assistant",
            "content": message.get("content") or "",
            "tool_calls": tool_calls,
        })
        for call in tool_calls:
            function = call.get("function") or {}
            name = function.get("name") or ""
            try:
                arguments = json.loads(function.get("arguments") or "{}")
            except ValueError:
                arguments = {}
            if name in TOOL_LABELS:
                try:
                    result = _run_tool(name, arguments)
                except AiError as error:
                    result = {"error": str(error)}
                emit("tool", {
                    "name": name,
                    "label": TOOL_LABELS[name],
                    "result": result,
                })
            else:
                result = {"error": "不支持的工具"}
            messages.append({
                "role": "tool",
                "tool_call_id": call.get("id") or name,
                "content": json.dumps(result, ensure_ascii=False),
            })
    else:
        # 模型没主动调用工具时，用本地计算补上，保证方案里有可核对的 BMI
        weight = metrics.get("weight")
        if weight and height:
            result = tool_calculate_bmi({"weight": weight, "height": height})
            emit("tool", {
                "name": "calculate_bmi",
                "label": TOOL_LABELS["calculate_bmi"],
                "result": result,
            })
            messages.append({
                "role": "system",
                "content": "工具计算结果（必须使用）：" + json.dumps(result, ensure_ascii=False),
            })

    emit("stage", {"text": "正在生成专属干预方案…"})

    # 第二轮：流式输出最终 JSON，边生成边推给前端
    full = _stream_completion(settings, {
        "model": settings["model"],
        "messages": messages,
        "temperature": 0.4,
        "max_tokens": 2200,
        "stream": True,
    }, lambda text: emit("delta", {"text": text}), timeout=90, kind="体检解读")

    plan = parse_json_object(full)
    plan["_provider"] = provider_name(settings)
    plan["_model"] = settings["model"]
    return plan
