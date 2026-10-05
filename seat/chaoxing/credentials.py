"""超星座位凭据（`.credentials.chaoxing.json`）：仅保留 chaoxing.com 域 Cookie。

与 `seat.there.credentials` 同模型：Cookie 记录保留域/路径/有效期，仅私有文件
落盘；SSO 会话（SHU_OAUTH2 等）不进入此文件。会话有效期实测约 30 天
（p_auth_token 为 HS256 JWT，exp 30 天；过期后重新运行 login.py）。
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from http.cookiejar import Cookie
from pathlib import Path

import requests

from seat.there.credentials import PROJECT_ROOT, write_private_json  # noqa: F401 - 对外保留原符号
from seat.there.config import LOCAL_TZ
from . import config

DEFAULT_PATH = PROJECT_ROOT / ".credentials.chaoxing.json"
CX_DOMAIN_SUFFIX = "chaoxing.com"
_REQUIRED_COOKIE_NAMES = ("fid",)
_PAYLOAD_FIELDS = {"version", "created_at", "username", "display_name",
                   "chaoxing", "user", "cookies", "source"}
_COOKIE_NAME_RE = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")


class CredentialsError(RuntimeError):
    """凭据缺失、损坏或 Cookie 域不适用于超星站点。"""


def _path(path: str | Path | None = None) -> Path:
    return Path(path or os.getenv("SHU_CHAOXING_CREDENTIALS") or DEFAULT_PATH).expanduser()


def _chaoxing_cookie(domain: str, name: str = "") -> bool:
    # 父域 Cookie 与 SSO Cookie 都不导出到本 POC；同名值不扁平合并。
    return (domain.lower().lstrip(".").endswith(CX_DOMAIN_SUFFIX)
            and name.lower() != "shu_oauth2")


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


def build(session: requests.Session, user: dict, username: str = "",
          login: str = "") -> dict:
    """成功验证后导出 chaoxing.com 域凭据；原始 HTML/会话不进此文件。"""
    if not isinstance(user, dict) or not str(user.get("uid") or "").strip():
        raise CredentialsError("未确认登录用户（uid 缺失），拒绝生成凭据")
    cookies = [_cookie_record(c) for c in session.cookies
               if _chaoxing_cookie(c.domain or "", c.name)]
    names = {record["name"] for record in cookies}
    if not cookies or not set(_REQUIRED_COOKIE_NAMES) <= names:
        raise CredentialsError("会话中没有超星域登录 Cookie（fid 缺失），拒绝生成凭据")
    return {
        "version": 1,
        "created_at": datetime.now(LOCAL_TZ).isoformat(),
        "username": username or str(user.get("sno") or ""),
        "display_name": str(user.get("uname") or ""),
        "chaoxing": {"base": config.CX_BASE, "dept_id": config.DEPT_ID,
                     "dept_enc": config.DEPT_ENC, "login": login or "newsso/5read"},
        # 仅私有凭据保留最小身份字段；trace / captures 会整项清除。
        "user": {"id": str(user["uid"]), "name": str(user.get("uname") or ""),
                 "sno": str(user.get("sno") or "")},
        "cookies": cookies,
    }


def restore_session(creds: dict) -> requests.Session:
    """恢复 CookieJar；不把过期 Cookie 人为变为 session Cookie。"""
    records = creds.get("cookies") if isinstance(creds, dict) else None
    if not isinstance(records, list) or not records:
        raise CredentialsError("凭据需要非空 Cookie records 列表；请重新运行 login.py --system chaoxing")
    sess = requests.Session()
    try:
        for record in records:
            if not isinstance(record, dict):
                raise CredentialsError("Cookie record 格式不正确")
            name, value = record.get("name"), record.get("value")
            domain, path = record.get("domain"), record.get("path")
            if (not isinstance(name, str) or not _COOKIE_NAME_RE.fullmatch(name)
                    or not isinstance(value, str) or "\r" in value or "\n" in value
                    or not isinstance(domain, str) or not _chaoxing_cookie(domain, name)
                    or not isinstance(path, str) or not path.startswith("/")):
                raise CredentialsError("Cookie record 的名称、域或路径无效；拒绝混入非超星 Cookie")
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


def load(path: str | Path | None = None) -> dict:
    """路径优先级：显式参数 → SHU_CHAOXING_CREDENTIALS → 项目根默认文件。"""
    p = _path(path)
    if not p.is_file():
        raise CredentialsError(f"未找到超星凭据文件：{p}\n  请先运行 python login.py --system chaoxing")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        raise CredentialsError(f"凭据文件不是合法 JSON：{p}") from exc
    _validate_metadata(data)
    sess = restore_session(data)
    sess.close()
    data["_path"] = str(p)
    return data


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
        raise CredentialsError("凭据格式或版本不正确；请重新运行 login.py --system chaoxing")
    section, user = data.get("chaoxing"), data.get("user")
    if (not isinstance(section, dict) or section.get("base") != config.CX_BASE
            or section.get("dept_id") != config.DEPT_ID
            or section.get("dept_enc") != config.DEPT_ENC):
        raise CredentialsError("凭据的超星站点或机构配置无效")
    if not isinstance(user, dict) or not str(user.get("id") or "").strip():
        raise CredentialsError("凭据缺少用户信息")


def describe(creds: dict | None, path: str | Path | None = None) -> str:
    """打印非敏感摘要；Cookie 值不显示任何片段。"""
    data = creds or {}
    records = data.get("cookies") or []
    dept = (data.get("chaoxing") or {}).get("dept_id") or config.DEPT_ID
    p = Path(path or data.get("_path") or _path())
    return f"文件 {p} ｜ 机构 {dept} ｜ chaoxing Cookie {len(records)} 项"


__all__ = ["CredentialsError", "DEFAULT_PATH", "build", "load", "save",
           "restore_session", "describe", "write_private_json"]
