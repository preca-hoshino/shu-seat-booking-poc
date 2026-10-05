"""业务终端输出：保持参考 POC 的中文表格与分隔线，不输出会话值。"""

from __future__ import annotations

import json
import re
import unicodedata

from . import config

_PRIVATE_FIELDS = re.compile(
    r"^(?:subject|meetingMembers|owner.*|bookingUser.*|loginName|mobile|phone|cardNo|jobNumber|namePinyin|headImgUrl)$", re.I)
_SECRETS = {"cookie", "cookies", "setcookie", "cookieheader", "password", "sessionid",
            "xhyssession", "utoken", "authenticitytoken", "shuoauth2", "sphyssession",
            "authjump", "state", "params", "checkintoken", "authcode", "authorizationcode",
            "authorization", "accesstoken", "refreshtoken", "token", "privatekey"}
_JWT_RE = re.compile(r"\b[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")


def safe_output(value, *, profile: bool = False):
    """终端保留可操作的 bookingId/roomId；会话、二维码令牌与个人字段隐藏。"""
    if profile and isinstance(value, dict):
        value = dict(value)
        data = value.get("data")
        if isinstance(data, dict):
            value["data"] = {k: "<redacted>" if k in ("id", "name", "nickName", "depts", "deptIds") else v
                             for k, v in data.items()}
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
            if (normalized in _SECRETS or _PRIVATE_FIELDS.match(str(key))
                    or (normalized == "code" and isinstance(item, str))):
                result[key] = "<redacted>"
            elif normalized == "qrcodevalue":
                result[key] = "<redacted-checkin-url>"
            else:
                result[key] = safe_output(item)
        return result
    if isinstance(value, list):
        return [safe_output(v) for v in value]
    if isinstance(value, str):
        value = _JWT_RE.sub("<redacted>", value)
        value = re.sub(r"(/m/b/[^/?\s]+/c/)[^?\s]+", r"\1<redacted>", value)
        value = re.sub(r"([?&](?:code|auth_code|authJump|state|utoken)=)[^&#\s]+", r"\1<redacted>", value, flags=re.I)
    return value


def _width(text: str) -> int:
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in text)


def table(headers, rows) -> str:
    """终端按中英文实际显示宽度对齐。"""
    vals = [[str(x) for x in row] for row in [headers] + list(rows)]
    widths = [max(_width(row[i]) for row in vals) for i in range(len(headers))]
    lines = ["  ".join(v + " " * (widths[i] - _width(v)) for i, v in enumerate(row)) for row in vals]
    lines.insert(1, "  ".join("─" * w for w in widths))
    return "\n".join(lines)


def banner(room_type: str, credentials_path: str) -> str:
    return "\n".join(["=" * 62, " SHU Seat Booking POC — 四入口统一预约", "=" * 62,
                      f" 系统 : {config.SYSTEMS[room_type]['name']} ({room_type})",
                      f" 凭据 : {credentials_path}", "=" * 62])


def render(result: dict, command: str) -> str:
    data = result.get("data")
    if command == "recent" and isinstance(data, list):
        return table(["预约 ID", "座位", "开始", "结束", "状态", "可用操作"],
                     [(b.get("id", ""), b.get("roomName", ""), b.get("beginTime", ""),
                       b.get("endTime", ""), b.get("status", ""), ",".join(b.get("abilities", [])))
                      for b in data if isinstance(b, dict)])
    if command == "areas" and isinstance(data, list):
        return table(["区域 ID", "名称", "父区域", "类型"],
                     [(a.get("id", ""), a.get("name", ""), a.get("parentName", ""),
                       ",".join(a.get("supportRoomTypes", []))) for a in data if isinstance(a, dict)])
    if command == "rooms" and isinstance(data, dict) and isinstance(data.get("rooms"), list):
        heading = f"区域 {data.get('name', '')} ｜ {len(data['rooms'])} 个座位（当前查询快照）"
        rows = [(r.get("id", ""), r.get("name", ""), str(r.get("disabled", "")),
                 str(r.get("isBusy", "")), str(r.get("isBooked", "")), ",".join(r.get("abilities", [])))
                for r in data["rooms"] if isinstance(r, dict)]
        return heading + "\n" + table(["roomId", "座位", "禁用", "忙碌", "已约", "可用操作"], rows)
    return json.dumps(safe_output(result, profile=command == "profile"), ensure_ascii=False, indent=2)
