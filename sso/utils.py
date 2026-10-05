"""上游工具薄适配：参数/RSA 复用，证据采用更严的递归脱敏。"""

from __future__ import annotations

import json
import re
from pathlib import Path

from src.utils import b64_params, rsa_encrypt_password  # noqa: F401
from seat.there.credentials import write_private_json  # noqa: F401
from . import config

REDACTED = "***REDACTED***"
_SECRET_KEYS = {
    "password", "code", "authcode", "authorizationcode", "accesstoken",
    "privatekey", "authorization", "cookie", "cookies", "cookieheader",
    "setcookie", "shuoauth2", "sphyssession", "authenticitytoken",
    "utoken", "sessionid", "xhyssession", "authjump", "checkintoken",
    "key", "k", "state", "params", "loginparams", "rawuser", "profile",
    "loginuser", "username", "displayname", "userid", "sub", "aud",
    "body", "bodypreview", "raw", "html", "text", "bootstrap",
    "qrimgurl", "confirmurl", "wxworkscheme", "wecomqrcode",
    "qrcodevalue", "subject", "meetingmembers", "ownerid", "ownername",
    "bookinguserid", "bookingusername", "loginname", "mobile", "phone",
    "cardno", "jobno", "namepinyin", "headimg",
    "token", "refreshtoken",
    # 超星换会话结果里的私有载荷与用户对象：凭证记录、uid/uname/sno 都不进证据。
    "credentials", "user", "verifiedparams", "salt",
}
_QUERY_SECRET_RE = re.compile(
    r"([?&](?:code|auth_?code|authorization_?code|key|k|state|utoken|authJump)=)[^&#\s\"'>]*",
    re.IGNORECASE,
)
_JWT_RE = re.compile(r"\b[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")
_CHECKIN_PATH_RE = re.compile(r"(/m/b/[^/\s?]+/c/)[^/\s?\"'<>]+", re.IGNORECASE)
_TOKEN_LITERAL_RE = re.compile(
    r"((?:x-hys-session|sessionId|utoken|authJump|SPHYS_SESSION|SHU_OAUTH2|authenticityToken)"
    r"\s*[\"']?\s*[:=]\s*[\"']?)[^\s\"'<>;,}]+", re.IGNORECASE,
)


def _key(value) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def redact(obj):
    """HTML/bootstrap、私人 profile、Cookie 与短令牌也整项脱敏。"""
    if isinstance(obj, dict):
        return {k: (redact(v) if _key(k) == "code" and isinstance(v, int)
                    and not isinstance(v, bool) else
                    REDACTED if _key(k) in _SECRET_KEYS else redact(v))
                for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [redact(item) for item in obj]
    if isinstance(obj, str):
        if (re.search(r"<\s*(?:html|script|!doctype)\b", obj, re.I)
                or obj.lower().startswith("wxwork://")):
            return REDACTED
        obj = _QUERY_SECRET_RE.sub(lambda match: match.group(1) + REDACTED, obj)
        obj = _TOKEN_LITERAL_RE.sub(lambda match: match.group(1) + REDACTED, obj)
        obj = _CHECKIN_PATH_RE.sub(lambda match: match.group(1) + REDACTED, obj)
        return _JWT_RE.sub(REDACTED, obj)
    return obj


def save_json(name: str, payload) -> Path:
    """证据写 captures/；不允许文件名逃出该目录。"""
    if Path(name).name != name or name in ("", ".", ".."):
        raise ValueError("证据文件名须为简单文件名")
    config.CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    path = config.CAPTURE_DIR / name
    path.write_text(json.dumps(redact(payload), ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    return path


def log(message: str) -> None:
    print(message, flush=True)


def mask(value: str, keep: int = 4) -> str:
    """认证/会话值整项隐藏；兼容原 POC 的调用签名。"""
    return REDACTED if value else ""


def mask_cookie_header(header: str, keep: int = 6) -> str:
    return "; ".join(f"{item.partition('=')[0].strip()}={REDACTED}"
                     for item in (header or "").split(";") if "=" in item)
