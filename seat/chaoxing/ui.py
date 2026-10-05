"""超星系统终端输出：分隔线与表格风格与 there 侧一致，不输出会话值。

脱敏约定：uid / sno 一律替换为占位符；JWT 形状字符串整项替换。
预约/房间 ID 保留（是后续 cancel 的必要操作数）。
"""

from __future__ import annotations

import json
import re
from datetime import datetime

from seat.there.config import LOCAL_TZ
from seat.there.ui import table
from . import config

_PRIVATE_KEYS = {"uid", "sno"}
_JWT_RE = re.compile(r"\b[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")
# 仅实录两种状态（HAR/浏览器）；未知值原样显示数字，不臆造枚举。
STATUS_TEXT = {0: "进行中", 7: "已结束"}


def safe_output(value):
    """终端可操作 ID 保留；个人标识与会话形状整项隐藏。"""
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
            if normalized in _PRIVATE_KEYS:
                result[key] = "<redacted>"
            else:
                result[key] = safe_output(item)
        return result
    if isinstance(value, list):
        return [safe_output(item) for item in value]
    if isinstance(value, str):
        return _JWT_RE.sub("<redacted>", value)
    return value


def banner(credentials_path: str) -> str:
    return "\n".join(["=" * 62, " SHU Seat Booking POC — 超星(学习通)图书馆座位", "=" * 62,
                      f" 机构 : 上海大学图书馆 (dept {config.DEPT_ID})",
                      f" 凭据 : {credentials_path}", "=" * 62])


def _hhmm(ms) -> str:
    try:
        return datetime.fromtimestamp(int(ms) / 1000, LOCAL_TZ).strftime("%H:%M")
    except (TypeError, ValueError, OSError):
        return ""


def _daytime(ms) -> str:
    try:
        return datetime.fromtimestamp(int(ms) / 1000, LOCAL_TZ).strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError, OSError):
        return ""


def _reserve_rows(items):
    for item in items:
        if not isinstance(item, dict):
            continue
        yield (item.get("id", ""), item.get("seatNum", ""),
               f"{item.get('secondLevelName', '')}/{item.get('thirdLevelName', '')}",
               item.get("today", ""),
               f"{_hhmm(item.get('startTime'))}-{_hhmm(item.get('endTime'))}",
               STATUS_TEXT.get(item.get("status"), item.get("status", "")))


def _render_reserves(title: str, items) -> str:
    rows = list(_reserve_rows(items))
    if not rows:
        return f"{title}：无"
    return title + "\n" + table(["预约 ID", "座位", "馆/区域", "日期", "时段", "状态"], rows)


def _render_overview(result: dict) -> str:
    user = result.get("user") or {}
    lines = [f"当前用户：{user.get('uname') or '(未知)'}（uid 已脱敏）" if user else "当前用户：(未验证)",
             ""]
    lines.append(_render_reserves("当前预约", result.get("current") or []))
    lines.append("")
    lines.append(_render_reserves("最近预约", result.get("near") or []))
    return "\n".join(lines)


def _pick(mapping: dict, key: str, default="-"):
    value = mapping.get(key)
    return default if value in (None, "") else value


def _render_config(result: dict) -> str:
    seat = ((result.get("data") or {}).get("seatConfig")) or {}
    time_cfg = seat.get("commonTimeConfig") or {}
    lines = [
        "超星座位规则（服务端响应为准）",
        f"  开放时段   {_pick(time_cfg, 'monStartTime')}-{_pick(time_cfg, 'monEndTime')}（每天）",
        f"  当天开放预约 {_pick(seat, 'reserveBeforeTime')}（reserveBeforeTime）",
        f"  单次时长   最短 {_pick(seat, 'minReserveDuration')} 小时 ｜ 粒度 {_pick(seat, 'timeUnit')} 分钟",
        f"  同时在约   {_pick(seat, 'reserveNumLimit')} 个",
        f"  签到窗口   ±{_pick(seat, 'signDuration')} 分钟（preSign {_pick(seat, 'preSignDuration')}）",
        f"  暂离       {_pick(seat, 'leaveDuration')} 分钟（餐时 "
        f"{_pick(seat, 'lunchMealLeaveDuration')}/{_pick(seat, 'dinnerMealLeaveDuration')}）",
        f"  违约       每周 {_pick(seat, 'violateTimes')} 次暂停 "
        f"（{_pick(seat, 'violationLimitDay')} 天窗口 / 暂停 {_pick(seat, 'violationLimitDuration')} 天）",
        f"  续约       {'允许 ' + str(_pick(seat, 'renewalDuration')) + ' 分钟' if seat.get('renewal') else '关闭'}",
        f"  座位监督   监督 {_pick(seat, 'superviseDuration')} 分钟未回记违约",
    ]
    return "\n".join(lines)


def _render_rooms(result: dict) -> str:
    rooms = ((result.get("data") or {}).get("seatRoomList")) or []
    rows = [(room.get("id", ""), room.get("firstLevelName", ""),
             room.get("secondLevelName", ""), room.get("thirdLevelName", ""),
             room.get("capacity", ""), room.get("startSeatNum", ""))
            for room in rooms if isinstance(room, dict)]
    if not rows:
        return "房间列表为空"
    return (f"{len(rows)} 个房间（当日可预约列表）\n"
            + table(["roomId", "类型", "分馆", "区域", "座位数", "起始号"], rows))


def _render_available(result: dict) -> str:
    room = result.get("room") or {}
    preview = result.get("available") or []
    shown = " ".join(preview[:40]) + ("…" if len(preview) > 40 else "")
    lines = [
        f"房间 {result.get('roomId')} ｜ {room.get('secondLevelName', '')} "
        f"{room.get('thirdLevelName', '')} ｜ {result.get('day')} "
        f"{result.get('begin')}-{result.get('end')}",
        f"容量 {result.get('total')} ｜ 已占 {len(result.get('used') or [])} ｜ "
        f"空闲 {result.get('available_count')}",
        "（派生值：容量区间减服务端已占；创建时仍以服务端校验为准）",
    ]
    if shown:
        lines.append(f"座位示例：{shown}")
    return "\n".join(lines)


def render(result: dict, command: str) -> str:
    data = result.get("data")
    if command == "systems":
        return _render_overview(result)
    if command == "profile" and isinstance(result.get("user"), dict):
        user = result["user"]
        return f"当前用户：{user.get('uname') or '(未知)'}\n（uid / sno 已脱敏，完整身份见私有凭据）"
    if command == "recent":
        return (_render_reserves("当前预约", result.get("current") or [])
                + "\n\n" + _render_reserves("最近预约", result.get("near") or []))
    if command == "config":
        return _render_config(result)
    if command == "rooms":
        return _render_rooms(result)
    if command == "available":
        return _render_available(result)
    return json.dumps(result, ensure_ascii=False, indent=2)


__all__ = ["banner", "render", "safe_output"]
