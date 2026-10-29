"""AI 健康助手：接口占位，后续接入大模型时只需改这个文件。

规划中的接入方式（豆包 / 方舟等）：
1. 在环境变量里配置 API 地址与密钥，例如
   HM_AI_API_BASE、HM_AI_API_KEY、HM_AI_MODEL；
2. 实现 _request_model(messages)，用标准库 urllib 调用兼容 OpenAI 的 /chat/completions；
3. generate_reply() 里把用户消息 + 健康数据摘要一起发过去，返回模型文本。

当前未配置密钥时，返回固定提示，保证前端功能可用。
"""

from __future__ import annotations

import os

PLACEHOLDER_REPLY = (
    "AI 健康助手接口已经就绪，但目前还没有接入大模型服务。"
    "接入后，这里会根据你的体重、饮食、运动与睡眠数据给出个性化建议。"
)

DEFAULT_MODEL = "doubao-seed-1-6-250615"


def config():
    """读取环境变量配置；未配置时返回 None。"""
    api_key = os.environ.get("HM_AI_API_KEY", "").strip()
    if not api_key:
        return None
    return {
        "api_base": os.environ.get("HM_AI_API_BASE", "https://ark.cn-beijing.volces.com/api/v3").strip(),
        "api_key": api_key,
        "model": os.environ.get("HM_AI_MODEL", DEFAULT_MODEL).strip(),
    }


def is_configured():
    return config() is not None


def generate_reply(message, context=None):
    """返回 (回复文本, 已配置标志)。

    context 预留给健康数据摘要（体重、饮食、运动等），接入时一并拼进提示词。
    """
    settings = config()
    if settings is None:
        return PLACEHOLDER_REPLY, False

    # TODO: 接入时在这里调用大模型，例如：
    # payload = {"model": settings["model"], "messages": [...]}
    # 目前即使配置了密钥也先返回占位文本，避免误发请求。
    return PLACEHOLDER_REPLY, False
