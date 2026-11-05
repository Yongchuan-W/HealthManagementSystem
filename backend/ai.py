"""AI 健康助手：调用 OpenAI 兼容的对话接口，默认接入 DeepSeek。

配置优先级：环境变量 > 项目根目录 ai_local.env（该文件已被 .gitignore 忽略）。
换成豆包方舟或其它兼容服务时，只需改 HM_AI_API_BASE 与 HM_AI_MODEL。

未配置密钥或调用失败时返回兜底文本（degraded=True），前端据此提示为规则建议。
"""

from __future__ import annotations

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


def _request_model(settings, messages):
    payload = {
        "model": settings["model"],
        "messages": messages,
        "temperature": 0.6,
        "max_tokens": MAX_TOKENS,
        "stream": False,
    }
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
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            body = json.loads(response.read().decode("utf-8"))
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
        if error.code == 429:
            raise AiError("调用过于频繁，请稍后再试")
        raise AiError("模型服务返回 %d%s" % (error.code, ("：" + detail) if detail else ""))
    except urllib.error.URLError as error:
        raise AiError("无法连接模型服务：%s" % getattr(error, "reason", error))
    except (ValueError, json.JSONDecodeError):
        raise AiError("模型返回内容无法解析")

    choices = body.get("choices") or []
    if not choices:
        raise AiError("模型没有返回内容")
    text = ((choices[0].get("message") or {}).get("content") or "").strip()
    if not text:
        raise AiError("模型返回内容为空")
    return text


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
