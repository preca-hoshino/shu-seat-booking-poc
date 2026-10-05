#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""离线自测：只用合成夹具，不联网、不提交真实预约。

运行: python tests/test_offline.py
所有 requests 请求都在 Session.send 边界被接管；额外封锁 socket 连接。
"""

from __future__ import annotations

import copy
import json
import socket
import sys
import tempfile
import threading
import unittest
from collections import deque
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import requests  # noqa: E402

from seat.client import (  # noqa: E402
    BusinessError, ProtocolError, SeatClient, SeatError,
    SessionExpired, SubmissionThrottled,
)

BASE = "https://there.shu.edu.cn"
START = "2030-06-01 10:00"
END = "2030-06-01 11:00"
PAGES = {
    "LIB_SEAT": "/mobile/libseat",
    "STATION": "/mobile/seat2021",
    "SEAT": "/mobile/seat-mgr",
    "CS_SEAT": "/mobile/csseat",
}
PROFILE = {
    "code": 0,
    "data": {"id": "fixture-user", "name": "测试用户", "lang": "zh",
             "isAnonymous": False, "disableBooking": False},
}
ROOM = {
    "id": "fixture-room", "name": "TEST-001", "officeAreaId": "fixture-area",
    "disabled": False, "showOrder": 1, "isBusy": False, "isBooked": False,
    "abilities": ["booking"],
}


def page_html(session_id: str = "fixture-html-session") -> str:
    """四入口已有证据的变量形状；内容全部为合成测试值。"""
    return ("<!DOCTYPE html><html><body><script>\n"
            f"var loginUser = {json.dumps(PROFILE['data'], ensure_ascii=False)};\n"
            f"var sessionId = {json.dumps(session_id)};\n"
            'var apiServiceHost = "https://there.shu.edu.cn/api/v3";\n'
            'var platform = "UNDEFINE"; var apiPlatform = "WXCP";\n'
            'var onlyShowAreaId = "all";\n'
            "</script></body></html>")


def area_envelope(room: dict | None = None) -> dict:
    return {
        "code": 0,
        "data": {
            "id": "fixture-area", "name": "测试区域",
            "rooms": [copy.deepcopy(ROOM if room is None else room)],
            "bookingTimes": {
                "supportAcrossDayBooking": False, "needCheckin": True,
                "startHour": 0, "endHour": 24, "meetingInterval": 30,
                "minDuration": 30, "maxDuration": 480,
                "bookingLimitDays": 1,
            },
            "bookingDays": ["2030-06-01"],
        },
    }


def response(request, body, *, status: int = 200, headers: dict | None = None):
    result = requests.Response()
    result.status_code = status
    result.url = request.url
    result.request = request
    result.headers.update(headers or {})
    if isinstance(body, (dict, list)):
        result._content = json.dumps(body, ensure_ascii=False).encode("utf-8")
        result.headers.setdefault("Content-Type", "application/json; charset=utf-8")
    else:
        result._content = str(body).encode("utf-8")
        result.headers.setdefault("Content-Type", "text/html; charset=utf-8")
    result.encoding = "utf-8"
    return result


class Wire:
    """接收真实 PreparedRequest。未安排的任何请求直接失败，永不访问网络。"""

    def __init__(self):
        self.expected = deque()
        self.calls = []
        self.lock = threading.Lock()

    def add(self, method, path, body, *, status=200, headers=None, inspect=None):
        self.expected.append((method.upper(), path, body, status, headers, inspect))
        return self

    def send(self, session, request, **kwargs):
        with self.lock:
            self.calls.append((request, kwargs))
            if not self.expected:
                raise AssertionError(f"未安排请求: {request.method} {urlsplit(request.url).path}")
            method, path, body, status, headers, inspect = self.expected.popleft()
        actual_path = urlsplit(request.url).path
        if (request.method, actual_path) != (method, path):
            raise AssertionError(f"请求顺序错误: {(request.method, actual_path)!r} != {(method, path)!r}")
        if inspect:
            inspect(request, kwargs)
        if isinstance(body, BaseException):
            raise body
        if callable(body):
            body = body(request)
        return response(request, body, status=status, headers=headers)


class OfflineCase(unittest.TestCase):
    def setUp(self):
        self.wire = Wire()
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(
            requests.Session, "send",
            lambda session, request, **kwargs: self.wire.send(session, request, **kwargs),
        ))
        self.stack.enter_context(patch.object(
            socket.socket, "connect", side_effect=AssertionError("测试禁止网络连接"),
        ))
        self.stack.enter_context(patch.object(
            socket, "create_connection", side_effect=AssertionError("测试禁止网络连接"),
        ))

    def tearDown(self):
        self.assertFalse(self.wire.expected, "安排的 mock 请求未完成")

    def client(self, room_type="LIB_SEAT", *, clock=None):
        session = requests.Session()
        session.trust_env = False
        session.cookies.set("SPHYS_SESSION", "fixture-cookie-utoken-different", domain="there.shu.edu.cn", path="/")
        session.cookies.set("authenticityToken", "fixture-csrf", domain="there.shu.edu.cn", path="/")
        session.cookies.set("HYS_LANG", "zh", domain="there.shu.edu.cn", path="/")
        session.cookies.set("SHU_OAUTH2", "fixture-sso-secret", domain="newsso.shu.edu.cn", path="/")
        client = SeatClient(session=session, room_type=room_type, clock=clock)
        self.wire.add("GET", PAGES[room_type], page_html())
        client.bootstrap()
        return client

    def assert_body(self, request, expected):
        body = request.body.decode("utf-8") if isinstance(request.body, bytes) else request.body
        self.assertEqual(json.loads(body), expected)


class ClientContractTests(OfflineCase):
    def test_four_mobile_entrypoints_and_current_header_source(self):
        for room_type, path in PAGES.items():
            with self.subTest(room_type=room_type):
                client = self.client(room_type)
                self.wire.add("GET", "/api/v3/my/profile", PROFILE)
                self.assertEqual(client.profile(), PROFILE)
                request, _ = self.wire.calls[-1]
                self.assertEqual(request.headers["x-room-type"], room_type)
                self.assertEqual(request.headers["x-hys-session"], "fixture-html-session")
                self.assertEqual(request.headers["x-hys-platform"], "UNDEFINE")
                self.assertEqual(request.headers["x-lang"], "zh")
                self.assertEqual(request.headers["X-Requested-With"], "com.tencent.wework")
                self.assertEqual(request.headers["Referer"], BASE + path)
                self.assertIn("SPHYS_SESSION=fixture-cookie-utoken-different", request.headers["Cookie"])
                self.assertNotIn("SHU_OAUTH2", request.headers["Cookie"])
                self.assertNotIn("Authorization", request.headers)

    def test_sso_default_headers_do_not_leak_to_business_requests(self):
        session = requests.Session()
        session.headers.update({"Origin": "https://newsso.shu.edu.cn",
                                "Referer": "https://newsso.shu.edu.cn/",
                                "Authorization": "fixture-wrong-bearer",
                                "Cookie": "SHU_OAUTH2=fixture-wrong-cookie"})
        session.cookies.set("SPHYS_SESSION", "fixture-there-cookie", domain="there.shu.edu.cn", path="/")
        client = SeatClient(session=session)
        self.wire.add("GET", PAGES["LIB_SEAT"], page_html())
        client.bootstrap()
        page_request = self.wire.calls[-1][0]
        self.assertNotIn("Origin", page_request.headers)
        self.assertNotIn("Referer", page_request.headers)
        self.wire.add("GET", "/api/v3/my/profile", PROFILE)
        client.profile()
        api_request = self.wire.calls[-1][0]
        self.assertEqual(api_request.headers["Referer"], BASE + PAGES["LIB_SEAT"])
        self.assertNotIn("Origin", api_request.headers)
        for request in (page_request, api_request):
            self.assertNotIn("Authorization", request.headers)
            self.assertEqual(request.headers["Cookie"], "SPHYS_SESSION=fixture-there-cookie")

    def test_bootstrap_rejects_missing_or_empty_session(self):
        for html in ("<html>登录</html>", page_html("")):
            with self.subTest(html=html):
                client = SeatClient(session=requests.Session())
                self.wire.add("GET", PAGES["LIB_SEAT"], html)
                with self.assertRaises(SeatError):
                    client.bootstrap()

    def test_business_code_is_not_http_status(self):
        client = self.client()
        self.wire.add("GET", "/api/v3/my/bookings/recent", {"code": 200, "warnMessage": "业务拒绝"})
        with self.assertRaises(BusinessError) as caught:
            client.recent()
        self.assertIn("业务拒绝", str(caught.exception))

    def test_unauthorized_response_is_session_expired(self):
        client = self.client()
        self.wire.add("GET", "/api/v3/my/profile", "需要登录", status=401)
        with self.assertRaises(SessionExpired):
            client.profile()

    def test_json_shape_errors_are_not_false_success(self):
        client = self.client()
        for body in ("<html>登录页面</html>", [], {"data": {}}, {"code": "0", "data": {}}):
            with self.subTest(body=body):
                self.wire.add("GET", "/api/v3/my/profile", body)
                with self.assertRaises(SeatError):
                    client.profile()

    def test_datetime_queries_are_url_encoded_once(self):
        client = self.client()
        self.wire.add("GET", "/api/v3/booking-status/areas", {"code": 0, "data": []})
        client.areas(START, END)
        request, _ = self.wire.calls[-1]
        self.assertEqual(parse_qs(urlsplit(request.url).query), {"begin": [START], "end": [END]})
        self.assertNotIn(" ", request.url)
        self.assertNotIn("%25", request.url)
        self.wire.add("GET", "/api/v3/booking-status/areas/fixture-area", area_envelope())
        client.area("fixture-area", START, END)
        request, _ = self.wire.calls[-1]
        self.assertEqual(parse_qs(urlsplit(request.url).query), {"begin": [START], "end": [END]})

    def test_overview_day_is_distinct_from_area_interval(self):
        client = self.client()
        self.wire.add("GET", "/api/v3/booking-status/overview", {"code": 0, "data": {}})
        client.overview("2030-06-01")
        self.assertEqual(parse_qs(urlsplit(self.wire.calls[-1][0].url).query), {"day": ["2030-06-01"]})

    def test_detail_retains_server_final_times_and_optional_checks(self):
        client = self.client("STATION")
        detail = {"code": 0, "data": {"id": "fixture-booking", "beginAt": "2030-06-01 10:03", "endAt": END,
                                         "duration": 57, "status": "OPEN", "abilities": ["close"], "checkins": []}}
        self.wire.add("GET", "/api/v3/bookings/fixture-booking", detail)
        self.assertEqual(client.detail("fixture-booking", show_checks=True), detail)
        self.assertEqual(parse_qs(urlsplit(self.wire.calls[-1][0].url).query).get("showChecks"), ["true"])

    def test_create_refreshes_room_and_keeps_complete_object(self):
        client = self.client()
        stale = copy.deepcopy(ROOM)
        stale["showOrder"] = 99
        fresh = copy.deepcopy(ROOM)
        fresh["fixtureMarker"] = "fresh-room-object"
        expected = {"rooms": [fresh], "times": [{"startDate": "2030-06-01", "startTime": "10:00",
                      "endDate": "2030-06-01", "endTime": "11:00"}],
                    "subject": PROFILE["data"]["name"], "meetingMembers": [PROFILE["data"]["id"]]}
        self.wire.add("GET", "/api/v3/my/profile", PROFILE)
        self.wire.add("GET", "/api/v3/booking-status/areas/fixture-area", area_envelope(fresh))
        created = {"code": 0, "data": [{"id": "fixture-booking", "beginAt": START, "endAt": END}]}
        self.wire.add("POST", "/api/v3/bookings", created,
                      inspect=lambda request, _: self.assert_body(request, expected))
        self.assertEqual(client.create(stale, START, END), created)
        self.assertEqual(stale["showOrder"], 99, "不能原地改写调用者快照")

    def test_prepare_booking_does_not_submit(self):
        client = self.client()
        self.wire.add("GET", "/api/v3/my/profile", PROFILE)
        self.wire.add("GET", "/api/v3/booking-status/areas/fixture-area", area_envelope())
        payload = client.prepare_booking("fixture-area", "fixture-room", START, END)
        self.assertEqual(payload["rooms"], [ROOM])
        self.assertEqual(payload["meetingMembers"], ["fixture-user"])
        self.assertFalse(any(request.method == "POST" for request, _ in self.wire.calls))

    def test_anonymous_profile_cannot_supply_booking_identity(self):
        client = self.client()
        anonymous = copy.deepcopy(PROFILE)
        anonymous["data"]["isAnonymous"] = True
        self.wire.add("GET", "/api/v3/my/profile", anonymous)
        with self.assertRaises(SeatError):
            client.prepare_booking("fixture-area", "fixture-room", START, END)
        self.assertFalse(any(request.method == "POST" for request, _ in self.wire.calls))

    def test_seat_that_became_busy_is_not_submitted(self):
        client = self.client()
        busy = copy.deepcopy(ROOM)
        busy["isBusy"] = True
        busy["abilities"] = []
        self.wire.add("GET", "/api/v3/my/profile", PROFILE)
        self.wire.add("GET", "/api/v3/booking-status/areas/fixture-area", area_envelope(busy))
        with self.assertRaises((SeatError, ValueError)):
            client.create(ROOM, START, END)
        self.assertFalse(any(request.method == "POST" for request, _ in self.wire.calls))

    def test_room_type_never_uses_other_config_only_types(self):
        for unsupported in ("ROOM", "SEAT2", "STATION2", "UNKNOWN"):
            with self.subTest(room_type=unsupported):
                with self.assertRaises((SeatError, ValueError)):
                    SeatClient(session=requests.Session(), room_type=unsupported)

    def test_submit_throttle_includes_business_failures(self):
        now = [100.0]
        client = self.client(clock=lambda: now[0])
        payload = {"rooms": [copy.deepcopy(ROOM)], "times": [{"startDate": "2030-06-01", "startTime": "10:00",
                   "endDate": "2030-06-01", "endTime": "11:00"}], "subject": "测试用户", "meetingMembers": ["fixture-user"]}
        self.wire.add("POST", "/api/v3/bookings", {"code": 200, "warnMessage": "超过服务端限制"})
        with self.assertRaises(BusinessError):
            client.submit(payload)
        now[0] = 109.0
        with self.assertRaises(SubmissionThrottled):
            client.submit(payload)
        now[0] = 111.0
        self.wire.add("POST", "/api/v3/bookings", {"code": 0, "data": [{"id": "fixture-booking"}]})
        self.assertEqual(client.submit(payload)["data"][0]["id"], "fixture-booking")
        self.assertEqual(sum(request.method == "POST" for request, _ in self.wire.calls), 2)

    def test_create_timeout_does_not_retry_and_still_throttles(self):
        now = [100.0]
        client = self.client(clock=lambda: now[0])
        payload = {"rooms": [copy.deepcopy(ROOM)], "times": [{"startDate": "2030-06-01", "startTime": "10:00",
                   "endDate": "2030-06-01", "endTime": "11:00"}], "subject": "测试用户", "meetingMembers": ["fixture-user"]}
        self.wire.add("POST", "/api/v3/bookings", requests.Timeout("fixture network timeout"))
        with self.assertRaises(SeatError):
            client.submit(payload)
        with self.assertRaises(SubmissionThrottled):
            client.submit(payload)
        self.assertEqual(sum(request.method == "POST" for request, _ in self.wire.calls), 1)

    def test_concurrent_submit_sends_at_most_once(self):
        client = self.client(clock=lambda: 100.0)
        payload = {"rooms": [copy.deepcopy(ROOM)], "times": [{"startDate": "2030-06-01", "startTime": "10:00",
                   "endDate": "2030-06-01", "endTime": "11:00"}], "subject": "测试用户", "meetingMembers": ["fixture-user"]}
        self.wire.add("POST", "/api/v3/bookings", {"code": 0, "data": [{"id": "fixture-booking"}]})
        barrier = threading.Barrier(2)
        outcomes = []
        def run():
            barrier.wait(timeout=5)
            try:
                outcomes.append(client.submit(copy.deepcopy(payload)))
            except Exception as exc:
                outcomes.append(exc)
        workers = [threading.Thread(target=run) for _ in range(2)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=5)
            self.assertFalse(worker.is_alive(), "提交锁不能死锁")
        self.assertEqual(sum(isinstance(value, SubmissionThrottled) for value in outcomes), 1)
        self.assertEqual(sum(isinstance(value, dict) for value in outcomes), 1)
        self.assertEqual(sum(request.method == "POST" for request, _ in self.wire.calls), 1)

    def test_mutations_follow_current_detail_abilities(self):
        client = self.client()
        self.wire.add("GET", "/api/v3/bookings/fixture-booking", {"code": 0, "data": {"id": "fixture-booking", "abilities": ["waitOpen"]}})
        with self.assertRaises((SeatError, ValueError)):
            client.cancel("fixture-booking")
        self.wire.add("GET", "/api/v3/bookings/fixture-booking", {"code": 0, "data": {"id": "fixture-booking", "abilities": ["cancel"]}})
        with self.assertRaises((SeatError, ValueError)):
            client.finish("fixture-booking")
        self.assertFalse(any(request.method in ("DELETE", "PUT") for request, _ in self.wire.calls))

    def test_checkin_is_opt_in_and_unknown_body_cannot_be_success(self):
        client = self.client()
        with self.assertRaises((SeatError, ValueError)):
            client.check_in("fixture-booking")
        self.wire.add("POST", "/api/v3/bookings/fixture-booking/checkInUse", {})
        result = client.check_in("fixture-booking", experimental=True)
        self.assertEqual(result["response"], {})
        self.assertFalse(result["schema_verified"])
        self.assertNotIn("ok", result)
        request, _ = self.wire.calls[-1]
        self.assertTrue(request.body in (None, b"", ""), "JS 没有已知签到 body，不应添加位置等猜测字段")


class CredentialsAndEvidenceTests(OfflineCase):
    def test_credentials_preserve_cookie_domain_path_and_flags(self):
        from seat import credentials
        session = requests.Session()
        session.cookies.set("SPHYS_SESSION", "fixture-there-session-secret",
                            domain="there.shu.edu.cn", path="/", secure=True,
                            expires=2200000000, rest={"HttpOnly": None})
        session.cookies.set("authenticityToken", "fixture-csrf-secret",
                            domain="there.shu.edu.cn", path="/api", secure=True)
        session.cookies.set("SHU_OAUTH2", "fixture-newsso-session-secret",
                            domain="newsso.shu.edu.cn", path="/", secure=True)
        creds = credentials.build(session, "LIB_SEAT", copy.deepcopy(PROFILE), username="fixture-username")
        self.assertEqual({item["name"] for item in creds["cookies"]}, {"SPHYS_SESSION", "authenticityToken"})
        restored = credentials.restore_session(json.loads(json.dumps(creds)))
        original = {(c.name, c.domain, c.path): c for c in session.cookies if c.domain == "there.shu.edu.cn"}
        for cookie in restored.cookies:
            source = original[(cookie.name, cookie.domain, cookie.path)]
            for field in ("value", "domain_specified", "domain_initial_dot", "path_specified",
                          "secure", "expires", "discard"):
                self.assertEqual(getattr(cookie, field), getattr(source, field))
            self.assertEqual(cookie._rest, source._rest)
        api_request = restored.prepare_request(requests.Request("GET", BASE + "/api/v3/my/profile"))
        mobile_request = restored.prepare_request(requests.Request("GET", BASE + "/mobile/libseat"))
        sso_request = restored.prepare_request(requests.Request("GET", "https://newsso.shu.edu.cn/oauth/authorize"))
        self.assertIn("authenticityToken=fixture-csrf-secret", api_request.headers["Cookie"])
        self.assertNotIn("authenticityToken", mobile_request.headers.get("Cookie", ""))
        self.assertNotIn("SHU_OAUTH2", api_request.headers["Cookie"])
        self.assertNotIn("Cookie", sso_request.headers)
        with tempfile.TemporaryDirectory(prefix="seat-test-") as directory:
            path = Path(directory) / "credentials.json"
            credentials.save(creds, path)
            self.assertEqual(credentials.load(path)["cookies"], creds["cookies"])
        summary = credentials.describe(creds)
        for secret in ("fixture-there-session-secret", "fixture-csrf-secret",
                       "fixture-newsso-session-secret", "fixture-username", "测试用户"):
            self.assertNotIn(secret, summary)

    def test_credentials_reject_ssocookie_in_restored_there_jar(self):
        from seat import credentials
        session = credentials.manual_session("SPHYS_SESSION=fixture-cookie; authenticityToken=fixture-csrf")
        creds = credentials.build(session, "LIB_SEAT", PROFILE)
        for mutation in ({"domain": "newsso.shu.edu.cn"}, {"domain": "shu.edu.cn"},
                         {"name": "SHU_OAUTH2"}, {"path": "bad-path"}, {"value": "bad\r\nheader"}):
            with self.subTest(mutation=mutation):
                changed = copy.deepcopy(creds)
                changed["cookies"][0].update(mutation)
                with self.assertRaises(credentials.CredentialsError):
                    credentials.restore_session(changed)
        with self.assertRaises(credentials.CredentialsError):
            credentials.manual_session("SHU_OAUTH2=fixture-sso")

    def test_expired_cookies_are_not_renewed_during_restore(self):
        from seat import credentials
        session = requests.Session()
        session.cookies.set("SPHYS_SESSION", "fixture-expired", domain="there.shu.edu.cn", path="/", expires=1)
        creds = credentials.build(session, "LIB_SEAT", PROFILE)
        restored = credentials.restore_session(creds)
        self.assertEqual(next(iter(restored.cookies)).expires, 1)
        prepared = restored.prepare_request(requests.Request("GET", BASE + "/api/v3/my/profile"))
        self.assertNotIn("Cookie", prepared.headers)

    def test_evidence_recursively_redacts_auth_and_booking_secrets(self):
        from sso.utils import redact
        payload = {
            "password": "fixture-password", "username": "fixture-username",
            "Cookie": "SPHYS_SESSION=fixture-cookie", "sessionId": "fixture-header-session",
            "profile": {"id": "fixture-user", "name": "fixture-person"},
            "trace": [{"url": "https://there.shu.edu.cn/login-oauth2?code=fixture-oauth-code&state=fixture-state"},
                      {"auth_code": "fixture-wecom-code", "authJump": "fixture-authjump"},
                      {"qrCodeValue": "https://there.shu.edu.cn/m/b/fixture-booking/c/fixture-checkin-token?corpAppId=test"}],
            "http_status": 200, "room_type": "LIB_SEAT",
        }
        safe = redact(payload)
        serialized = json.dumps(safe, ensure_ascii=False)
        for secret in ("fixture-password", "fixture-username", "fixture-cookie", "fixture-header-session",
                       "fixture-person", "fixture-oauth-code", "fixture-state", "fixture-wecom-code", "fixture-authjump",
                       "fixture-checkin-token"):
            self.assertNotIn(secret, serialized)
        self.assertEqual(safe["http_status"], 200)
        self.assertEqual(safe["room_type"], "LIB_SEAT")
        self.assertEqual(redact({"code": 200, "data": {"code": "fixture-oauth-secret"}}),
                         {"code": 200, "data": {"code": "***REDACTED***"}})
        from seat.ui import safe_output
        terminal = safe_output({"code": 0, "response": {"code": "fixture-auth-code",
                              "Authorization": "fixture-bearer", "accessToken": "fixture-access",
                              "qrCodeValue": "fixture-checkin", "ownerId": "fixture-owner"}})
        self.assertEqual(terminal["code"], 0)
        self.assertNotIn("fixture-", json.dumps(terminal))

    def test_sso_trace_never_contains_raw_response_context(self):
        from sso.client import ShuSSO
        client = ShuSSO()
        client.record("callback", {"http_status": 200, "body_preview": "fixture-html-secret",
                      "cookie": "fixture-cookie-secret", "profile": {"name": "fixture-person-secret"},
                      "location": "https://there.shu.edu.cn/login-oauth2?code=fixture-code-secret"})
        serialized = json.dumps(client.trace)
        self.assertIn("http_status", serialized)
        for secret in ("fixture-html-secret", "fixture-cookie-secret", "fixture-person-secret", "fixture-code-secret"):
            self.assertNotIn(secret, serialized)


if __name__ == "__main__":
    unittest.main(verbosity=2)
