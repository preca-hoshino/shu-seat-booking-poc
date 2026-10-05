"""页面引导与预约时间解析。所有解析函数都是离线纯函数。"""

from __future__ import annotations

import ast
from copy import deepcopy
from datetime import datetime
import json
import re


def _js_string(literal: str) -> str:
    """解析引号包围的字符串，不执行 JavaScript。"""
    try:
        value = json.loads(literal) if literal.startswith('"') else ast.literal_eval(literal)
    except (ValueError, SyntaxError) as exc:
        raise ValueError("页面会话字符串格式无法解析") from exc
    if not isinstance(value, str):
        raise ValueError("页面会话值不是字符串")
    return value


def parse_bootstrap(text: str) -> dict:
    """读取 HAR 所见 loginUser / sessionId；不把 Cookie.utoken 当作 API 会话。"""
    login_user = {}
    for match in re.finditer(r"\bloginUser\s*=\s*", text):
        try:
            obj, _end = json.JSONDecoder().raw_decode(text[match.end():].lstrip())
        except ValueError:
            continue
        if isinstance(obj, dict):
            login_user = obj
            break
    match = re.search(r'''\bsessionId\s*=\s*("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')''', text)
    session_id = _js_string(match.group(1)) if match else login_user.get("sessionId", "")
    if not isinstance(session_id, str) or not session_id.strip():
        # 部分部署把 sessionId 放在 JSON 引导对象中，仍只读字符串。
        match = re.search(r'''["']sessionId["']\s*:\s*("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')''', text)
        session_id = _js_string(match.group(1)) if match else ""
    if not session_id or "\r" in session_id or "\n" in session_id:
        raise ValueError("移动页面没有可用 sessionId，请重新运行 python login.py")
    if login_user.get("isAnonymous") is True:
        raise ValueError("移动页面仍处于匿名状态")
    return {"sessionId": session_id, "loginUser": login_user,
            "platform": login_user.get("platform") or "UNDEFINE",
            "lang": login_user.get("lang") or "zh"}


def parse_day(value: str) -> str:
    """只接受捕获格式 YYYY-MM-DD。"""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value or ""):
        raise ValueError("日期格式应为 YYYY-MM-DD")
    datetime.strptime(value, "%Y-%m-%d")
    return value


def parse_datetime(value: str) -> datetime:
    """预约使用上海当地时间 YYYY-MM-DD HH:mm；不做服务器取整推算。"""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", value or ""):
        raise ValueError("时间格式应为 YYYY-MM-DD HH:mm")
    return datetime.strptime(value, "%Y-%m-%d %H:%M")


def parse_query_time(value: str) -> str:
    """区域查询既捕获日期，也捕获完整 datetime。"""
    parse_day(value) if len(value or "") == 10 else parse_datetime(value)
    return value


def time_selection(start: str, end: str) -> dict:
    begin, finish = parse_datetime(start), parse_datetime(end)
    if finish <= begin:
        raise ValueError("结束时间必须晚于开始时间")
    return {"startDate": begin.strftime("%Y-%m-%d"), "startTime": begin.strftime("%H:%M"),
            "endDate": finish.strftime("%Y-%m-%d"), "endTime": finish.strftime("%H:%M")}


def profile_data(profile: dict) -> dict:
    """接受 API envelope 或已取出的 data，仍验证当前非匿名身份。"""
    if not isinstance(profile, dict):
        raise ValueError("profile 返回结构不是对象")
    if "code" in profile:
        if profile["code"] != 0:
            raise ValueError("profile 业务结果不是成功")
        profile = profile.get("data")
    if not isinstance(profile, dict) or profile.get("isAnonymous") is not False:
        raise ValueError("profile 没有非匿名用户")
    if not profile.get("id") or not profile.get("name"):
        raise ValueError("profile 缺少用户 id/name，不能组装预约")
    return profile


def build_payload(room: dict, start: str, end: str, profile: dict) -> dict:
    """保留最新查询所得的完整座位对象；仅实现样本覆盖的一座位一时段。"""
    if not isinstance(room, dict) or not room.get("id") or not room.get("officeAreaId"):
        raise ValueError("座位必须来自区域详情 rooms[]，包含 id 和 officeAreaId")
    user = profile_data(profile)
    if user.get("disableBooking") is True:
        raise ValueError("当前用户配置为禁止预约")
    if room.get("disabled") or room.get("isBusy") or room.get("isBooked"):
        raise ValueError("最新查询显示该座位不可预约")
    if "booking" not in room.get("abilities", []):
        raise ValueError("最新查询未给该座位 booking 能力")
    return {"rooms": [deepcopy(room)], "times": [time_selection(start, end)],
            "subject": user["name"], "meetingMembers": [user["id"]]}
