"""预约凭据（`.credentials.json`）：保留 Cookie 的域、路径与有效期。"""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime
from http.cookiejar import Cookie
from pathlib import Path

import requests
from .config import LOCAL_TZ

# 文件在 seat/there/ 下，项目根要再上两级。
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_PATH = PROJECT_ROOT / ".credentials.json"
THERE_BASE = "https://there.shu.edu.cn"
THERE_HOST = "there.shu.edu.cn"
MOBILE_PATHS = {
    "LIB_SEAT": "/mobile/libseat", "STATION": "/mobile/seat2021",
    "SEAT": "/mobile/seat-mgr", "CS_SEAT": "/mobile/csseat",
}
_PAYLOAD_FIELDS = {
    "version", "created_at", "username", "display_name", "room_type",
    "there", "profile", "cookies", "source",
}
_COOKIE_NAME_RE = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")


class CredentialsError(RuntimeError):
    """凭据缺失、损坏或 Cookie 域不适用于 there。"""


def _path(path: str | Path | None = None) -> Path:
    return Path(path or os.getenv("SHU_SEAT_CREDENTIALS") or DEFAULT_PATH).expanduser()


def _there_cookie(domain: str, name: str = "") -> bool:
    # 同名 Cookie 不能把 SSO 和 there 扁平合并。父域 Cookie 也不导出到本 POC。
    return domain.lower().lstrip(".") == THERE_HOST and name.lower() != "shu_oauth2"


def _cookie_record(c: Cookie) -> dict:
    return {
        "version": c.version, "name": c.name, "value": c.value,
        "domain": c.domain, "domain_specified": c.domain_specified,
        "domain_initial_dot": c.domain_initial_dot,
        "path": c.path, "path_specified": c.path_specified,
        "secure": c.secure, "expires": c.expires, "discard": c.discard,
        "port": c.port, "port_specified": c.port_specified,
        "comment": c.comment, "comment_url": c.comment_url,
        "rfc2109": c.rfc2109, "rest": dict(c._rest),
    }


def build(session: requests.Session, room_type: str, profile: dict,
          username: str = "") -> dict:
    """成功验证后导出目标站凭据；原始 profile 与 HTML/sessionId 不落盘。"""
    if room_type not in MOBILE_PATHS:
        raise CredentialsError("不支持的预约类型")
    data = profile.get("data") if isinstance(profile, dict) else None
    if (not isinstance(profile, dict) or type(profile.get("code")) is not int
            or profile.get("code") != 0 or not isinstance(data, dict)
            or not str(data.get("id") or "").strip()
            or not str(data.get("name") or "").strip()
            or data.get("anonymous") is True or data.get("isAnonymous") is not False):
        raise CredentialsError("profile 未确认非匿名用户，拒绝生成凭据")
    cookies = [_cookie_record(c) for c in session.cookies
               if _there_cookie(c.domain or "", c.name)]
    if not cookies:
        raise CredentialsError("会话中没有 there 域的 Cookie，拒绝生成凭据")
    return {
        "version": 1,
        "created_at": datetime.now(LOCAL_TZ).isoformat(),
        "username": username or "", "display_name": str(data["name"]),
        "room_type": room_type,
        "there": {"base": THERE_BASE, "room_type": room_type,
                  "mobile_path": MOBILE_PATHS[room_type]},
        # 仅私有凭据保留最小身份字段；trace / captures 会整项清除。
        "profile": {"id": str(data["id"]), "name": str(data["name"])},
        "cookies": cookies,
    }


def restore_session(creds: dict) -> requests.Session:
    """恢复 CookieJar；不把过期 Cookie 人为变为 session Cookie。"""
    records = creds.get("cookies") if isinstance(creds, dict) else None
    if not isinstance(records, list) or not records:
        raise CredentialsError("凭据需要非空 Cookie records 列表；请重新运行 login.py")
    sess = requests.Session()
    try:
        for record in records:
            if not isinstance(record, dict):
                raise CredentialsError("Cookie record 格式不正确")
            name, value = record.get("name"), record.get("value")
            domain, path = record.get("domain"), record.get("path")
            if (not isinstance(name, str) or not _COOKIE_NAME_RE.fullmatch(name)
                    or not isinstance(value, str) or "\r" in value or "\n" in value
                    or not isinstance(domain, str) or not _there_cookie(domain, name)
                    or not isinstance(path, str) or not path.startswith("/")):
                raise CredentialsError("Cookie record 的名称、域或路径无效；拒绝混入 SSO Cookie")
            expires = record.get("expires")
            if expires is not None and (not isinstance(expires, int) or isinstance(expires, bool)):
                raise CredentialsError("Cookie expires 必须为 Unix 秒数或 null")
            rest = record.get("rest", {})
            if not isinstance(rest, dict):
                raise CredentialsError("Cookie rest 必须为对象")
            sess.cookies.set_cookie(Cookie(
                version=record.get("version", 0), name=name, value=value,
                port=record.get("port"), port_specified=bool(record.get("port_specified", False)),
                domain=domain, domain_specified=bool(record.get("domain_specified", True)),
                domain_initial_dot=bool(record.get("domain_initial_dot", domain.startswith("."))),
                path=path, path_specified=bool(record.get("path_specified", True)),
                secure=bool(record.get("secure", False)), expires=expires,
                discard=bool(record.get("discard", expires is None)),
                comment=record.get("comment"), comment_url=record.get("comment_url"),
                rest=rest, rfc2109=bool(record.get("rfc2109", False)),
            ))
    except CredentialsError:
        sess.close()
        raise
    except Exception as exc:
        sess.close()
        raise CredentialsError("Cookie records 无法恢复") from exc
    return sess


def manual_session(cookie_header: str) -> requests.Session:
    """手工 Cookie 只灌入 there 域，不作为 SSO Cookie 发往 newsso。"""
    if not cookie_header.strip() or "\r" in cookie_header or "\n" in cookie_header:
        raise CredentialsError("手工 Cookie 为空或含换行")
    sess = requests.Session()
    seen: set[str] = set()
    try:
        for item in cookie_header.split(";"):
            if not item.strip():
                continue
            name, separator, value = item.strip().partition("=")
            name, value = name.strip(), value.strip()
            if (not separator or not _COOKIE_NAME_RE.fullmatch(name)
                    or name.lower() == "shu_oauth2" or name in seen):
                raise CredentialsError("请提供 there 的 Cookie 请求头；不接受 SSO Cookie 或同名重复项")
            seen.add(name)
            sess.cookies.set(name, value, domain=THERE_HOST, path="/", secure=True)
        if not seen:
            raise CredentialsError("手工 Cookie 没有可用项目")
        return sess
    except Exception:
        sess.close()
        raise


def load(path: str | Path | None = None) -> dict:
    """路径优先级：显式参数 → SHU_SEAT_CREDENTIALS → 项目根默认文件。"""
    p = _path(path)
    if not p.is_file():
        raise CredentialsError(f"未找到凭据文件：{p}\n  请先运行 python login.py")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        raise CredentialsError(f"凭据文件不是合法 JSON：{p}") from exc
    _validate_metadata(data)
    sess = restore_session(data)
    sess.close()
    data["_path"] = str(p)
    return data


def write_private_json(path: str | Path, payload: dict) -> Path:
    """先以 0600 创建临时文件，再原子替换；Windows chmod 不等同 ACL。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{p.name}.", suffix=".tmp", dir=p.parent)
    try:
        os.chmod(temporary, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, p)
        os.chmod(p, 0o600)
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    return p.resolve()


def save(data: dict, path: str | Path | None = None) -> Path:
    """仅写凭据结构；密码、验证码、SSO 会话和追踪信息不进入此文件。"""
    if not isinstance(data, dict):
        raise CredentialsError("凭据应为 JSON 对象")
    unexpected = set(data) - _PAYLOAD_FIELDS - {"_path"}
    if unexpected or data.get("version") != 1:
        raise CredentialsError("凭据含不支持的字段或版本")
    _validate_metadata(data)
    sess = restore_session(data)
    sess.close()
    payload = {k: v for k, v in data.items() if k in _PAYLOAD_FIELDS}
    return write_private_json(_path(path), payload)


def _validate_metadata(data: dict) -> None:
    if not isinstance(data, dict) or type(data.get("version")) is not int or data.get("version") != 1:
        raise CredentialsError("凭据格式或版本不正确；请重新运行 login.py")
    room_type, there = data.get("room_type"), data.get("there")
    if (room_type not in MOBILE_PATHS or not isinstance(there, dict)
            or there.get("base") != THERE_BASE or there.get("room_type") != room_type
            or there.get("mobile_path") != MOBILE_PATHS[room_type]):
        raise CredentialsError("凭据的 there 地址或移动入口配置无效")


def describe(creds: dict | None, path: str | Path | None = None) -> str:
    """打印非敏感摘要；短 Cookie 同样不显示首尾片段。"""
    data = creds or {}
    records = data.get("cookies") or []
    room_type = data.get("room_type") or (data.get("there") or {}).get("room_type")
    if room_type not in MOBILE_PATHS:
        room_type = "(未指定)"
    p = Path(path or data.get("_path") or _path())
    return f"文件 {p} ｜ 类型 {room_type} ｜ there Cookie {len(records)} 项"


__all__ = ["CredentialsError", "DEFAULT_PATH", "build", "load", "save",
           "restore_session", "manual_session", "describe", "write_private_json"]
