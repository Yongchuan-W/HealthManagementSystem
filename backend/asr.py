"""阿里云智能语音交互：把浏览器录到的短语音转成文字。

只使用标准库：
  - 先调用 CreateToken 接口换取临时 Token（有效期 24 小时，进程内缓存）；
  - 再把 16k / 16bit / 单声道 WAV 音频 POST 给一句话识别接口。

未配置密钥时 is_configured() 返回 False，前端会自动退回浏览器自带识别。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import urllib.parse
import urllib.request
import uuid

from . import ai

DEFAULT_REGION = "cn-shanghai"
TOKEN_API = "https://nls-meta.{region}.aliyuncs.com/"
GATEWAY = "https://nls-gateway-{region}.aliyuncs.com/stream/v1/asr"


class AsrError(Exception):
    """语音识别失败（未配置、鉴权、网络、无结果等）。"""


_TOKEN = {"id": "", "expire": 0.0}


def _env(name, default=""):
    return os.environ.get(name, default).strip()


def config():
    """读取语音识别配置；缺少任意一项时返回 None。"""
    ai._load_local_env()
    appkey = _env("HM_ASR_APPKEY")
    ak_id = _env("HM_ASR_AK_ID")
    ak_secret = _env("HM_ASR_AK_SECRET")
    if not appkey or not ak_id or not ak_secret:
        return None
    return {
        "appkey": appkey,
        "ak_id": ak_id,
        "ak_secret": ak_secret,
        "region": _env("HM_ASR_REGION", DEFAULT_REGION) or DEFAULT_REGION,
    }


def is_configured():
    return config() is not None


def _percent_encode(value):
    return urllib.parse.quote(str(value), safe="~").replace("+", "%20").replace("*", "%2A")


def _signature(params, secret):
    query = "&".join(
        "%s=%s" % (_percent_encode(key), _percent_encode(params[key]))
        for key in sorted(params)
    )
    string_to_sign = "GET&%2F&" + _percent_encode(query)
    digest = hmac.new((secret + "&").encode("utf-8"),
                      string_to_sign.encode("utf-8"), hashlib.sha1).digest()
    return base64.b64encode(digest).decode("ascii")


def _create_token(settings):
    params = {
        "AccessKeyId": settings["ak_id"],
        "Action": "CreateToken",
        "Format": "JSON",
        "RegionId": settings["region"],
        "SignatureMethod": "HMAC-SHA1",
        "SignatureNonce": uuid.uuid4().hex,
        "SignatureVersion": "1.0",
        "Timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "Version": "2019-02-28",
    }
    params["Signature"] = _signature(params, settings["ak_secret"])
    url = TOKEN_API.format(region=settings["region"]) + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as error:
        raise AsrError("获取语音服务令牌失败：%s" % error)

    token = data.get("Token") or {}
    token_id = token.get("Id") or token.get("id")
    expire = token.get("ExpireTime") or token.get("expireTime") or 0
    if not token_id:
        message = data.get("Message") or data.get("message") or "未知错误"
        raise AsrError("获取语音服务令牌失败：%s" % message)
    _TOKEN["id"] = token_id
    _TOKEN["expire"] = float(expire) - 60
    return token_id


def _token(settings):
    if _TOKEN["id"] and time.time() < _TOKEN["expire"]:
        return _TOKEN["id"]
    return _create_token(settings)


def recognize(audio_bytes, sample_rate=16000):
    """识别一段 WAV/PCM 音频，返回识别出的文字。"""
    if not audio_bytes:
        raise AsrError("录音内容为空")
    if len(audio_bytes) > 4 * 1024 * 1024:
        raise AsrError("录音太长，请控制在 20 秒内")

    settings = config()
    if settings is None:
        raise AsrError("未配置语音识别密钥")

    token = _token(settings)
    url = GATEWAY.format(region=settings["region"]) + "?" + urllib.parse.urlencode({
        "appkey": settings["appkey"],
        "format": "wav",
        "sample_rate": sample_rate,
        "enable_punctuation_prediction": "true",
        "enable_inverse_text_normalization": "true",
    })
    request = urllib.request.Request(
        url,
        data=audio_bytes,
        headers={
            "X-NLS-Token": token,
            "Content-Type": "application/octet-stream",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as error:
        raise AsrError("语音识别请求失败：%s" % error)

    status = data.get("status")
    if status != 200:
        raise AsrError(data.get("message") or "语音识别失败")
    text = (data.get("result") or "").strip()
    if not text:
        raise AsrError("没有听清，请靠近麦克风再说一次")
    return text
