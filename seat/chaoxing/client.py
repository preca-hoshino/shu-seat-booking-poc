"""超星座位预约 HTTP 客户端：会话校验 + 实测端点 + 签名提交。

设计要点（与 `seat.client` 同风格）：

- HTTP 200 不代表业务成功；信封为 ``{"success": true, "data": …}``，
  ``success=false`` 带 ``msg``（如"该时间段已过，不可预约！"）一律按业务错误上抛；
- 提交前重新拉取 select 页取新盐（实测每次载入变化），签名见 `enc.py`；
- 不自动重试提交；本进程 10 秒节流与服务端"同一用户10秒只能提交一次"对齐；
- 会话失效表现为 office 域被 302 到 passport2 登录页 → `SessionExpired`；
- 页面同站重定向严格跟随（仅 office.chaoxing.com、有限跳数），跨站/登录页立即判失效。

只读可用性说明：``availability`` 是"容量区间减服务端已占"的**派生值**，
未逐座位探测；最终以创建时服务端校验为准（HAR 已见座位冲突类业务拒绝）。
"""

from __future__ import annotations

import json
import math
import random
import re
import threading
import time
from copy import deepcopy
from urllib.parse import parse_qs, urljoin, urlsplit

import requests

from . import config
from .enc import build_enc, parse_salt

__all__ = ["ChaoxingClient", "ChaoxingError", "SessionExpired", "ProtocolError",
           "BusinessError", "SubmissionThrottled", "parse_user_info"]

_REDIRECT_STATUSES = {301, 302, 303, 307, 308}
_TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")
_USER_INFO_RE = re.compile(r"userLoginInfo\s*=\s*(\{.*?\})\s*\|\|\s*\{\}", re.S)


class ChaoxingError(RuntimeError):
    """可给 CLI 展示的错误，不包含原始 Cookie 或完整 HTML。"""

    def __init__(self, message: str, *, http_status: int | None = None):
        super().__init__(message)
        self.http_status = http_status


class SessionExpired(ChaoxingError):
    """office 域被重定向到登录页/站外，或页面不再包含 userLoginInfo。"""


class ProtocolError(ChaoxingError):
    """响应结构与实测契约不符，停止而非猜测成功。"""


class BusinessError(ChaoxingError):
    """HTTP 可成功而 success=false。完整响应只保存在对象属性。"""

    def __init__(self, response: dict, *, http_status: int = 200):
        self.response = response
        message = (response.get("msg") or response.get("message")
                   or response.get("errorMsg"))
        super().__init__(str(message or "业务拒绝（success=false）"), http_status=http_status)


class SubmissionThrottled(ChaoxingError):
    """客户端节流；与 SeatClient 相同，业务拒绝与网络失败同样计入。"""

    def __init__(self, retry_after: float):
        self.retry_after = retry_after
        super().__init__(f"距上次提交尝试不足 10 秒，请至少等待 {math.ceil(retry_after)} 秒")


def parse_user_info(html: str) -> dict:
    """从座位首页 HTML 的 ``userLoginInfo`` 解析当前用户（登录态判据）。

    仅保留 uid/uname/sno 三个字段；缺 uid 即视为未登录或结构变化。
    """
    match = _USER_INFO_RE.search(html or "")
    if not match:
        raise ValueError("页面未包含 userLoginInfo（未登录或结构变化）")
    try:
        payload = json.loads(match.group(1))
    except ValueError as exc:
        raise ValueError("userLoginInfo 不是合法 JSON") from exc
    user = payload.get("userInfo") if isinstance(payload, dict) else None
    if not isinstance(user, dict):
        raise ValueError("userLoginInfo 缺少 userInfo 对象")
    uid = str(user.get("uid") or "").strip()
    if not uid:
        raise ValueError("userInfo 缺少 uid")
    return {"uid": uid, "uname": str(user.get("uname") or "").strip(),
            "sno": str(user.get("sno") or "").strip()}


def _error_message_from_url(url: str) -> str:
    """select 页失败会 302 到 /front/apps/reserve/error/code/500?msg=…；取出 msg。"""
    values = parse_qs(urlsplit(url).query).get("msg") or []
    return values[0].strip() if values and values[0].strip() else ""


def _day_value(day: str) -> str:
    if not isinstance(day, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day.strip()):
        raise ValueError("day 需要 YYYY-MM-DD")
    return day.strip()


def _time_value(value: str, label: str) -> str:
    """解析并归一化 HH:MM（接受 9:00，统一输出 09:00）。"""
    match = _TIME_RE.match(str(value).strip()) if isinstance(value, str) else None
    if not match:
        raise ValueError(f"{label} 需要 HH:MM（如 21:00）")
    return f"{int(match.group(1)):02d}:{match.group(2)}"


def _seat_number(seat) -> str:
    """座位号按实测 3 位补零（099/006/135…）；数字纯值统一字符串。"""
    text = str(seat).strip()
    if not text:
        raise ValueError("座位号不能为空")
    if text.isdigit() and len(text) < 3:
        return text.zfill(3)
    return text


class ChaoxingClient:
    """一个实例绑定一个机构（默认上海大学图书馆 35480）。"""

    def __init__(self, session=None, base: str = config.CX_BASE,
                 dept_enc: str = config.DEPT_ENC, dept_id: str = config.DEPT_ID,
                 timeout: float = config.DEFAULT_TIMEOUT, verify: bool = True,
                 clock=None, user_agent: str = config.USER_AGENT):
        parsed = urlsplit(base)
        if (parsed.scheme not in ("http", "https") or not parsed.netloc
                or parsed.username or parsed.password):
            raise ValueError("base 必须是无用户名密码的 HTTP(S) 根地址")
        if parsed.query or parsed.fragment or parsed.path not in ("", "/"):
            raise ValueError("base 必须是站点根地址，不能含路径、query 或 fragment")
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout 必须是正数")
        if not isinstance(dept_enc, str) or not dept_enc.strip() or not isinstance(dept_id, str):
            raise ValueError("dept_enc / dept_id 无效")
        self.session = session if session is not None else requests.Session()
        self.sess = self.session
        self.base = base.rstrip("/")
        self.dept_enc, self.dept_id = dept_enc.strip(), dept_id
        self.timeout, self.verify = timeout, verify
        self.user_agent = user_agent
        self._clock = clock or time.monotonic
        self._last_submit: float | None = None
        self._submit_lock = threading.Lock()
        self._user: dict | None = None

    def close(self) -> None:
        self.session.close()

    # ---- 基础请求 -------------------------------------------------

    def _index_url(self) -> str:
        return f"{self.base}{config.SEAT_INDEX_PATH}?fidEnc={self.dept_enc}"

    def _select_url(self, room_id, day: str) -> str:
        return (f"{self.base}{config.SEAT_SELECT_PATH}?deptIdEnc={self.dept_enc}"
                f"&id={room_id}&day={day}&backLevel=2&fidEnc={self.dept_enc}")

    def _headers(self, method: str, referer: str | None) -> dict:
        # SSO/业务共用 CookieJar，但 SSO 的全局头不能流入 chaoxing 请求。
        # requests 用 None 删除 Session 的默认头；Cookie 仍按域和路径生成。
        headers = {name: None for name in (
            "Authorization", "Cookie", "Origin", "Content-Type",
            "X-Requested-With", "Referer", "Accept",
        )}
        headers.update({
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": referer or self._index_url(),
        })
        if method.upper() == "POST":
            headers["Origin"] = self.base
            headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        return headers

    def _send(self, method: str, url: str, *, params=None, form=None,
              referer: str | None = None):
        kwargs = {"headers": self._headers(method, referer), "timeout": self.timeout,
                  "verify": self.verify, "allow_redirects": False}
        if params is not None:
            kwargs["params"] = params
        if form is not None:
            kwargs["data"] = form
        try:
            return self.session.request(method, url, **kwargs)
        except requests.RequestException as exc:
            # requests 异常可能含完整 URL，CLI 只显示类型。
            raise ChaoxingError(f"请求失败（{type(exc).__name__}）；未自动重试") from exc

    def _follow_local(self, response, *, referer: str | None = None, max_hops: int = 8):
        """手动跟随 office 同站重定向；目标非 office.chaoxing.com 立即判会话失效。"""
        hops = 0
        while response.status_code in _REDIRECT_STATUSES:
            location = (response.headers.get("Location") or "").strip()
            target = urlsplit(urljoin(response.url, location)) if location else None
            if (target is None or target.scheme != "https" or target.hostname != config.CX_HOST
                    or target.username or target.password):
                raise SessionExpired("office 会话未建立（被重定向到登录页或站外）",
                                     http_status=response.status_code)
            hops += 1
            if hops > max_hops:
                raise ProtocolError("office 同站重定向次数超过限制",
                                    http_status=response.status_code)
            response = self._send("GET", target.geturl(), referer=referer)
        return response

    def _request(self, method: str, path: str, *, params=None, form=None,
                 referer: str | None = None, follow: bool = False):
        response = self._send(method, self.base + path, params=params, form=form,
                              referer=referer)
        if follow:
            response = self._follow_local(response, referer=referer)
        if response.status_code in _REDIRECT_STATUSES:
            raise SessionExpired("office 会话未建立（被重定向），请重新登录",
                                 http_status=response.status_code)
        if response.status_code == 401:
            raise SessionExpired("office 会话需要重新登录", http_status=response.status_code)
        if response.status_code >= 400:
            raise ChaoxingError(f"上游 HTTP {response.status_code}",
                                http_status=response.status_code)
        return response

    def _envelope(self, response) -> dict:
        try:
            result = response.json()
        except ValueError as exc:
            raise ProtocolError("API 没有返回 JSON；请重新登录后再试",
                                http_status=response.status_code) from exc
        if not isinstance(result, dict) or "success" not in result:
            raise ProtocolError("API 响应缺少 success 字段，无法判断结果",
                                http_status=response.status_code)
        if result.get("success") is not True:
            raise BusinessError(result, http_status=response.status_code)
        return result

    def _api_get(self, path: str, params: dict, *, referer: str | None = None) -> dict:
        return self._envelope(self._request("GET", path, params=params, referer=referer))

    def _api_post(self, path: str, form: dict, *, referer: str | None = None) -> dict:
        return self._envelope(self._request("POST", path, form=form, referer=referer))

    # ---- 会话校验 -------------------------------------------------

    def bootstrap(self) -> dict:
        """验证 office 会话并解析当前用户；未登录时抛 SessionExpired。"""
        response = self._request("GET", config.SEAT_INDEX_PATH,
                                 params={"fidEnc": self.dept_enc}, follow=True)
        host = (urlsplit(response.url).hostname or "").lower()
        if host != config.CX_HOST:
            raise SessionExpired("office 会话未建立（跳转到站外），请重新登录",
                                 http_status=response.status_code)
        try:
            user = parse_user_info(response.text)
        except ValueError as exc:
            raise SessionExpired(str(exc), http_status=response.status_code) from exc
        self._user = user
        return deepcopy(user)

    @property
    def user(self) -> dict | None:
        return deepcopy(self._user)

    # ---- 只读查询 -------------------------------------------------

    def home(self) -> dict:
        """座位首页数据：seatConfig / curReserves / nearReserves / officeDomain。"""
        return self._api_get(config.HOME_PATH,
                             {"fidEnc": self.dept_enc, "r": f"{random.random() * 100:.15f}"})

    def recent(self) -> dict:
        """当前与最近预约（同一首页端点的切片）。"""
        data = self.home().get("data") or {}
        return {"current": data.get("curReserves") or [],
                "near": data.get("nearReserves") or []}

    def config_data(self) -> dict:
        return self._api_get(config.CONFIG_PATH, {"fidEnc": self.dept_enc})

    def levels(self) -> dict:
        return self._api_get(config.LEVELS_PATH,
                             {"deptIdEnc": self.dept_enc, "type": "0"})

    def rooms(self, day: str) -> dict:
        day = _day_value(day)
        return self._api_get(config.ROOM_LIST_PATH, {
            "time": "", "cpage": "1", "pageSize": "100",
            "firstLevelName": "", "secondLevelName": "", "thirdLevelName": "",
            "day": day, "deptIdEnc": self.dept_enc,
        })

    def window_check(self, room_id, day: str) -> dict:
        day = _day_value(day)
        return self._api_get(config.WINDOW_CHECK_PATH, {
            "roomId": str(room_id), "day": day,
            "deptIdEnc": self.dept_enc, "fidEnc": self.dept_enc,
        })

    def room_info(self, room_id, day: str, query_reserve: bool = True) -> dict:
        day = _day_value(day)
        return self._api_post(config.ROOM_INFO_PATH, {
            "id": str(room_id), "toDay": day, "fidEnc": self.dept_enc,
            "queryReserve": "true" if query_reserve else "false",
        })

    def used_seats(self, room_id, day: str, begin: str, end: str) -> dict:
        day = _day_value(day)
        begin, end = _time_value(begin, "begin"), _time_value(end, "end")
        if end <= begin:
            raise ValueError("结束时间必须晚于开始时间")
        return self._api_post(config.USED_SEATS_PATH, {
            "roomId": str(room_id), "startTime": begin, "endTime": end,
            "day": day, "fidEnc": self.dept_enc,
        })

    def check_exist(self, seat, room_id) -> dict:
        return self._api_get(config.CHECK_EXIST_PATH,
                             {"seatNum": _seat_number(seat), "roomId": str(room_id)})

    def availability(self, room_id, day: str, begin: str, end: str) -> dict:
        """房间在给定时段的可用座位（派生：容量区间减服务端已占座位）。"""
        day = _day_value(day)
        begin, end = _time_value(begin, "begin"), _time_value(end, "end")
        if end <= begin:
            raise ValueError("结束时间必须晚于开始时间")
        info = self.room_info(room_id, day).get("data") or {}
        room = info.get("seatRoom")
        if not isinstance(room, dict) or not room.get("capacity"):
            raise ProtocolError("room/info 缺少 seatRoom.capacity")
        used_result = self.used_seats(room_id, day, begin, end).get("data") or {}
        used = sorted({str(item.get("seatNum") or "").strip()
                       for item in used_result.get("seatReserves") or []
                       if isinstance(item, dict) and str(item.get("seatNum") or "").strip()})
        start = int(room.get("startSeatNum") or 1)
        capacity = int(room["capacity"])
        seat_set = {f"{index:03d}" for index in range(start, start + capacity)}
        used_set = set(used)
        # 已占座位若超出容量区间仍继续展示，但不凭空排除区间内不存在的位置。
        available = sorted(seat_set - used_set)
        return {
            "derived": True,
            "roomId": str(room_id), "day": day, "begin": begin, "end": end,
            "room": {"id": room.get("id"), "firstLevelName": room.get("firstLevelName"),
                     "secondLevelName": room.get("secondLevelName"),
                     "thirdLevelName": room.get("thirdLevelName"),
                     "capacity": capacity, "startSeatNum": start},
            "total": capacity, "used": used,
            "available": available, "available_count": len(available),
        }

    # ---- 提交与取消 -----------------------------------------------

    def fetch_salt(self, room_id, day: str) -> str:
        """拉取 select 页并解析盐；页面被替换为错误页时翻译为业务错误。"""
        day = _day_value(day)
        response = self._request("GET", config.SEAT_SELECT_PATH, params={
            "deptIdEnc": self.dept_enc, "id": str(room_id), "day": day,
            "backLevel": "2", "fidEnc": self.dept_enc,
        }, referer=self._index_url(), follow=True)
        path = urlsplit(response.url).path or ""
        if path.startswith(config.ERROR_PATH_PREFIX):
            message = _error_message_from_url(response.url) or "页面错误"
            raise BusinessError({"success": False, "msg": message},
                                http_status=response.status_code)
        try:
            return parse_salt(response.text)
        except ValueError as exc:
            raise ProtocolError("select 页未包含盐（页面结构变化）",
                                http_status=response.status_code) from exc

    def prepare_submit(self, room_id, day: str, begin: str, end: str, seat,
                       captcha: str = "", wy_token: str = "") -> dict:
        """拉取最新盐并组装提交体（不发送）；`book --dry-run` 使用。"""
        day = _day_value(day)
        begin, end = _time_value(begin, "begin"), _time_value(end, "end")
        if end <= begin:
            raise ValueError("结束时间必须晚于开始时间")
        seat_num = _seat_number(seat)
        salt = self.fetch_salt(room_id, day)
        signature = {"captcha": captcha, "day": day, "deptIdEnc": self.dept_enc,
                     "endTime": end, "roomId": str(room_id), "seatNum": seat_num,
                     "startTime": begin, "wyToken": wy_token}
        form = {"deptIdEnc": self.dept_enc, "roomId": str(room_id), "startTime": begin,
                "endTime": end, "day": day, "seatNum": seat_num, "captcha": captcha,
                "wyToken": wy_token, "enc": build_enc(signature, salt)}
        return {"form": form, "salt": salt}

    def _claim_submit_slot(self) -> None:
        with self._submit_lock:
            now = self._clock()
            if self._last_submit is not None and now - self._last_submit < config.SUBMIT_INTERVAL:
                raise SubmissionThrottled(config.SUBMIT_INTERVAL - (now - self._last_submit))
            self._last_submit = now

    def submit(self, room_id, day: str, begin: str, end: str, seat,
               captcha: str = "", wy_token: str = "") -> dict:
        """一次创建尝试，不重试；节流基于本实例（服务端另有 10 秒限制）。"""
        self._claim_submit_slot()
        prepared = self.prepare_submit(room_id, day, begin, end, seat,
                                       captcha=captcha, wy_token=wy_token)
        result = self._api_post(config.SUBMIT_PATH, prepared["form"],
                                referer=self._select_url(room_id, prepared["form"]["day"]))
        data = result.get("data") or {}
        reserve = data.get("seatReserve")
        if not isinstance(reserve, dict) or not reserve.get("id"):
            raise ProtocolError("创建成功但没有 seatReserve.id；请刷新最近预约核对，勿直接重试")
        return result

    def cancel(self, reserve_id) -> dict:
        text = str(reserve_id).strip()
        if not text.isdigit():
            raise ValueError("reserveId 应为创建响应或最近预约返回的数字 id")
        return self._api_get(config.CANCEL_PATH, {"id": text})
