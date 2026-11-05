"""AI 健康助手：调用 OpenAI 兼容的对话接口，默认接入 DeepSeek。

配置优先级：环境变量 > 项目根目录 ai_local.env（该文件已被 .gitignore 忽略）。
换成豆包方舟或其它兼容服务时，只需改 HM_AI_API_BASE 与 HM_AI_MODEL。

未配置密钥或调用失败时返回兜底文本（degraded=True），前端据此提示为规则建议。
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request

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


def _build_messages(message, history, context):
    system = SYSTEM_PROMPT
    if context:
        system += "\n\n用户健康数据摘要（仅供参考）：\n" + str(context).strip()

    messages = [{"role": "system", "content": system}]
    for item in (history or [])[-MAX_HISTORY:]:
        role = item.get("role")
        content = (item.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})
    return messages


def _post(settings, payload, timeout=TIMEOUT, not_found_hint=""):
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


def generate_reply(message, history=None, context=None):
    """调用大模型，返回 (回复文本, 元信息)。

    元信息：configured（是否配置了密钥）、degraded（是否走了兜底）、
            model、provider、error（失败原因）。
    """
    settings = config()
    if settings is None:
        return PLACEHOLDER_REPLY, {
            "configured": False, "degraded": True,
            "model": None, "provider": None, "error": "未配置 HM_AI_API_KEY",
        }

    try:
        text = _request_model(settings, _build_messages(message, history, context))
    except AiError as error:
        return FALLBACK_REPLY.format(reason=error), {
            "configured": True, "degraded": True,
            "model": settings["model"], "provider": provider_name(settings),
            "error": str(error),
        }

    return text, {
        "configured": True, "degraded": False,
        "model": settings["model"], "provider": provider_name(settings), "error": None,
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
        not_found_hint="当前模型不支持图片识别，请确认 HM_AI_MODEL 为多模态模型")

    return parse_json_object(_message_text(body)), {
        "configured": True,
        "model": settings["model"],
        "provider": provider_name(settings),
    }
