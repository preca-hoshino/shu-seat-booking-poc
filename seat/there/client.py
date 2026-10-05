"""there 移动预约客户端：页面引导 → 九个实测业务 API。

HTTP 200 不等于业务成功；所有返回保留原始 envelope 与服务器最终时间。
请求 Cookie 由 requests.Session 按 domain/path 管理，API 头只用于 there 请求。
创建不自动重试；每次已发起尝试（含拒绝、网络失败）参与本进程十秒节流。
"""

from __future__ import annotations

from copy import deepcopy
import math
import threading
import time
from urllib.parse import quote, urlsplit

import requests

from . import config
from .models import (build_payload, parse_bootstrap, parse_day, parse_datetime,
                     parse_query_time, profile_data)

__all__ = ["SeatClient", "SeatError", "SessionExpired", "BusinessError",
           "ProtocolError", "SubmissionThrottled"]


class SeatError(RuntimeError):
    """可给 CLI 展示的错误，不包含原始 Cookie、HTML 或授权跳转 URL。"""

    def __init__(self, message: str, *, http_status: int | None = None):
        super().__init__(message)
        self.http_status = http_status


class SessionExpired(SeatError):
    """登录页面、401 或匿名 profile。"""


class ProtocolError(SeatError):
    """响应结构与明确来源不符，停止而非猜测成功。"""


class BusinessError(SeatError):
    """HTTP 可成功而 JSON.code 拒绝。完整响应只保存在对象属性。"""

    def __init__(self, response: dict, *, http_status: int = 200):
        self.response = response
        self.code = response.get("code")
        message = response.get("warnMessage") or response.get("message") or response.get("noticeMessage")
        super().__init__(str(message or f"业务拒绝，JSON.code={self.code}"), http_status=http_status)


class SubmissionThrottled(SeatError):
    """客户端节流；并不声明服务器窗口/幂等算法已验证。"""

    def __init__(self, retry_after: float):
        self.retry_after = retry_after
        super().__init__(f"距上次创建尝试不足 10 秒，请至少等待 {math.ceil(retry_after)} 秒")


def _segment(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("路径 ID 不能为空")
    return quote(value, safe="")


class SeatClient:
    """一个客户端实例绑定一个入口与资源类型；切换类型应重新引导页面。"""

    def __init__(self, session=None, room_type: str = config.DEFAULT_ROOM_TYPE,
                 base: str = config.THERE_BASE, timeout: float = 30.0,
                 verify: bool = True, clock=None):
        if room_type not in config.SYSTEMS:
            raise ValueError(f"未捕获的资源类型：{room_type}，可用 {', '.join(config.SYSTEMS)}")
        parsed = urlsplit(base)
        if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError("base 必须是无用户名密码的 HTTP(S) 根地址")
        if parsed.query or parsed.fragment or parsed.path not in ("", "/"):
            raise ValueError("base 必须是站点根地址，不能含路径、query 或 fragment")
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout 必须是正数")
        self.session = session if session is not None else requests.Session()
        self.sess = self.session
        self.room_type, self.base = room_type, base.rstrip("/")
        self.timeout, self.verify = timeout, verify
        self._clock = clock or time.monotonic
        self._last_submit = None
        self._submit_lock = threading.Lock()
        self._bootstrap = None

    @property
    def session_id(self) -> str:
        return (self._bootstrap or {}).get("sessionId", "")

    def _request(self, method: str, path: str, *, headers=None, params=None, payload=None):
        # SSO 与业务共用 CookieJar，但 SSO 的全局头不能流入移动页面/API。
        # requests 用 None 删除 Session 的默认头；Cookie 仍按域和路径生成。
        request_headers = {name: None for name in (
            "Authorization", "Cookie", "Origin", "Referer", "Content-Type",
            "x-hys-session", "x-room-type", "x-hys-platform", "x-lang",
            "X-Requested-With",
        )}
        request_headers.update(headers or {})
        kwargs = {"headers": request_headers, "timeout": self.timeout,
                  "verify": self.verify, "allow_redirects": False}
        if params is not None:
            kwargs["params"] = params
        if payload is not None:
            kwargs["json"] = payload
        try:
            response = self.session.request(method, self.base + path, **kwargs)
        except requests.RequestException as exc:
            # requests 异常可能含 URL/查询串，CLI 不直接输出原始异常。
            raise SeatError(f"请求失败（{type(exc).__name__}）；未自动重试") from exc
        if response.status_code in (301, 302, 303, 307, 308, 401):
            raise SessionExpired("会话需要登录，请重新运行 python login.py", http_status=response.status_code)
        if response.status_code >= 400:
            raise SeatError(f"上游 HTTP {response.status_code}", http_status=response.status_code)
        return response

    def bootstrap(self) -> dict:
        """每次登录/载入凭据从当前移动 HTML 重新取得会话，不读取历史 sessionId。"""
        response = self._request("GET", config.SYSTEMS[self.room_type]["path"],
                                 headers={"X-Requested-With": "com.tencent.wework"})
        try:
            result = parse_bootstrap(response.text)
        except ValueError as exc:
            raise SessionExpired(str(exc), http_status=response.status_code) from exc
        self._bootstrap = result
        return deepcopy(result)

    def _headers(self, method: str) -> dict:
        if self._bootstrap is None:
            self.bootstrap()
        headers = {
            "x-hys-session": self.session_id,
            "x-room-type": self.room_type,
            "x-hys-platform": self._bootstrap.get("platform") or "UNDEFINE",
            "x-lang": self._bootstrap.get("lang") or "zh",
            "Content-Type": "application/json",
            "X-Requested-With": "com.tencent.wework",
            "Referer": self.base + config.SYSTEMS[self.room_type]["path"],
        }
        if method in ("POST", "PUT", "DELETE"):
            headers["Origin"] = self.base
        return headers

    def _api(self, method: str, path: str, *, params=None, payload=None,
             check_business: bool = True) -> dict:
        response = self._request(method, path, headers=self._headers(method), params=params, payload=payload)
        try:
            result = response.json()
        except ValueError as exc:
            raise ProtocolError("API 没有返回 JSON；请用 login.py --check 核对会话", http_status=response.status_code) from exc
        if not isinstance(result, dict) or "code" not in result:
            raise ProtocolError("API 响应缺少 JSON.code，无法判断结果", http_status=response.status_code)
        if isinstance(result["code"], bool) or not isinstance(result["code"], int):
            raise ProtocolError("API JSON.code 不是捕获的整数类型", http_status=response.status_code)
        if check_business and result["code"] != 0:
            raise BusinessError(result, http_status=response.status_code)
        return result

    def profile(self) -> dict:
        result = self._api("GET", config.PROFILE_PATH)
        try:
            profile_data(result)
        except ValueError as exc:
            raise SessionExpired("profile 未确认非匿名身份，请重新登录") from exc
        return result

    def recent(self) -> dict:
        return self._api("GET", config.RECENT_PATH)

    def overview(self, day: str) -> dict:
        return self._api("GET", config.OVERVIEW_PATH, params={"day": parse_day(day)})

    def areas(self, begin: str, end: str) -> dict:
        return self._api("GET", config.AREAS_PATH,
                         params={"begin": parse_query_time(begin), "end": parse_query_time(end)})

    def area(self, area_id: str, begin: str, end: str) -> dict:
        return self._api("GET", config.AREAS_PATH + "/" + _segment(area_id),
                         params={"begin": parse_query_time(begin), "end": parse_query_time(end)})

    def detail(self, booking_id: str, show_checks: bool | None = None) -> dict:
        show = config.SYSTEMS[self.room_type]["show_checks"] if show_checks is None else show_checks
        params = {"showChecks": "true"} if show else None
        return self._api("GET", config.BOOKINGS_PATH + "/" + _segment(booking_id), params=params)

    def prepare_booking(self, area_id: str, room_id: str, start: str, end: str,
                        profile: dict | None = None) -> dict:
        """只查用户与最新区间座位，产出完整请求体；dry-run 使用此方法，不提交。"""
        begin, finish = parse_datetime(start), parse_datetime(end)
        if finish <= begin:
            raise ValueError("结束时间必须晚于开始时间")
        user = profile if profile is not None else self.profile()
        result = self.area(area_id, start, end)
        area = result.get("data")
        if not isinstance(area, dict) or not isinstance(area.get("rooms"), list):
            raise ProtocolError("区域详情缺少 rooms 数组")
        room = next((r for r in area["rooms"] if isinstance(r, dict) and r.get("id") == room_id), None)
        if room is None:
            raise ValueError("所选 roomId 不在当前区间的区域 rooms[] 中")
        if room.get("officeAreaId") != area_id:
            raise ProtocolError("座位 officeAreaId 与查询区域不一致")
        rules = area.get("bookingTimes") or {}
        if rules.get("supportAcrossDayBooking") is False and begin.date() != finish.date():
            raise ValueError("选中区域配置不支持跨日预约")
        # 日期列表、bookingLimitDays、overview 规则与服务端准入不等价，不用其猜截止。
        return build_payload(room, start, end, user)

    def submit(self, payload: dict) -> dict:
        """一次创建尝试，不重试。节流基于本实例；另一个进程仍以服务端为准。"""
        if not isinstance(payload, dict) or set(("rooms", "times", "subject", "meetingMembers")) - payload.keys():
            raise ValueError("创建体缺少捕获的四个顶层字段")
        if not isinstance(payload["rooms"], list) or len(payload["rooms"]) != 1:
            raise ValueError("本 POC 只实现一座位预约")
        if not isinstance(payload["times"], list) or len(payload["times"]) != 1:
            raise ValueError("本 POC 只实现单时段预约")
        # 页面读取失败不计为创建；发起 POST 前记账，业务拒绝和超时也计入。
        self._headers("POST")
        with self._submit_lock:
            now = self._clock()
            if self._last_submit is not None and now - self._last_submit < config.SUBMIT_INTERVAL:
                raise SubmissionThrottled(config.SUBMIT_INTERVAL - (now - self._last_submit))
            self._last_submit = now
        result = self._api("POST", config.BOOKINGS_PATH, payload=deepcopy(payload))
        data = result.get("data")
        if not isinstance(data, list) or not data or not isinstance(data[0], dict) or not data[0].get("id"):
            raise ProtocolError("创建响应 code=0 但没有 data[0].id；请查 recent 核对结果，勿直接重试")
        return result

    def create(self, room: dict, start: str, end: str, profile: dict | None = None) -> dict:
        if not isinstance(room, dict) or not room.get("id") or not room.get("officeAreaId"):
            raise ValueError("room 必须有 id 与 officeAreaId")
        payload = self.prepare_booking(room["officeAreaId"], room["id"], start, end, profile=profile)
        return self.submit(payload)

    def _action(self, booking_id: str, ability: str, method: str, suffix: str) -> dict:
        detail = self.detail(booking_id).get("data")
        if not isinstance(detail, dict) or ability not in detail.get("abilities", []):
            raise ValueError(f"当前预约详情没有 {ability} 操作能力")
        return self._api(method, config.BOOKINGS_PATH + "/" + _segment(booking_id) + suffix)

    def cancel(self, booking_id: str) -> dict:
        return self._action(booking_id, "cancel", "DELETE", "/cancel")

    def finish(self, booking_id: str) -> dict:
        return self._action(booking_id, "close", "PUT", "/finish")

    def check_in(self, booking_id: str, experimental: bool = False) -> dict:
        """仅图书馆 JS 调用证据；返回体结构与签到成功语义均未验证。"""
        if not experimental:
            raise ValueError("checkInUse 仅有脚本引用；执行时必须显式加 --experimental")
        if self.room_type != "LIB_SEAT":
            raise ValueError("只在 LIB_SEAT 脚本发现 checkInUse，其他资源类型不执行")
        response = self._request(
            "POST", config.BOOKINGS_PATH + "/" + _segment(booking_id) + "/checkInUse",
            headers=self._headers("POST"),
        )
        try:
            result = response.json()
        except ValueError as exc:
            raise ProtocolError("实验签到响应不是 JSON，未判断签到结果",
                                http_status=response.status_code) from exc
        return {"http_status": response.status_code, "response": result,
                "schema_verified": False, "evidence_level": "javascript_reference"}

    def close(self) -> None:
        self.session.close()
