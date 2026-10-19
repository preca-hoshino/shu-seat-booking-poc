#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""超星（学习通）座位系统离线自检：签名向量、会话校验、查询、提交/取消、凭据与换会话。

运行: python tests/test_chaoxing_offline.py
所有请求在 requests.Session.send 边界被接管；禁止 socket 连接。

签名向量的真实值来自 2026-10-05 浏览器动态分析（hook hex_md5 捕获明文 +
服务端 A/B 对照），只用于验证算法实现，不包含任何会话值。
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import requests  # noqa: E402
import poc  # noqa: E402

from test_offline import OfflineCase  # noqa: E402

from seat.chaoxing import credentials as cx_creds  # noqa: E402
from seat.chaoxing import enc  # noqa: E402
from seat.chaoxing import ui as cx_ui  # noqa: E402
from seat.chaoxing.client import (  # noqa: E402
    BusinessError, ChaoxingClient, ProtocolError, SessionExpired, SubmissionThrottled,
    parse_user_info,
)

# ---- 真实捕获向量（2026-10-05 浏览器动态分析）----
REAL_SALT_1 = "31f510e3790a43959f20531c9987e029_404270468"
REAL_ENC_1 = "24c8937106f6bf1f0620508d110c3adc"
REAL_PLAIN_1 = ("[captcha=][day=2026-10-05][deptIdEnc=00bae7f2bdea485a][endTime=22:00]"
                "[roomId=6508][seatNum=135][startTime=21:00][wyToken=]"
                "[31f510e3790a43959f20531c9987e029_404270468]")
REAL_SALT_2 = "79aad9d4f6a94b4993ee95b088459e21_404270468"
REAL_ENC_2 = "8e519b833fe692b2cc2d5c14e03e4e53"

PARAMS_1 = {"captcha": "", "day": "2026-10-05", "deptIdEnc": "00bae7f2bdea485a",
            "endTime": "22:00", "roomId": "6508", "seatNum": "135",
            "startTime": "21:00", "wyToken": ""}
PARAMS_2 = {**PARAMS_1, "seatNum": "099"}

# 续约来自另一个 code 页，签名输入没有 deptIdEnc。以下全是合成数据。
RENEW_SALT = "0123456789abcdef0123456789abcdef_123456"
RENEW_ENC = "ccfa62df68a34fa6a41b89f985ae5112"
RENEW_PARAMS = {"captcha": "", "day": "2030-01-01", "endTime": "11:00",
                "roomId": "6508", "seatNum": "048", "startTime": "10:00", "wyToken": ""}


def seat_page_html() -> str:
    payload = {"userInfo": {"deptId": 35480, "id": 23404308, "mobile": "186****0000",
                            "sno": "25123368", "uid": 404270468, "uname": "测试用户"}}
    return ("<!DOCTYPE html><html><script>\n"
            f"var userLoginInfo = {json.dumps(payload, ensure_ascii=False)}||{{}};\n"
            "</script></html>")


def select_page_html(salt: str = REAL_SALT_1) -> str:
    return ('<html><input type="hidden" id="submit_enc" value="' + salt + '"/></html>')


def form_of(request) -> dict:
    """PreparedRequest.body 可能是 str 或 bytes；统一解析成表单字典（保留空值字段）。"""
    body = request.body
    if isinstance(body, bytes):
        body = body.decode("utf-8")
    return parse_qs(body or "", keep_blank_values=True)


class EncVectorTests(unittest.TestCase):
    def test_real_capture_vectors_reproduce(self):
        self.assertEqual(enc.build_plain(PARAMS_1, REAL_SALT_1), REAL_PLAIN_1)
        self.assertEqual(enc.build_enc(PARAMS_1, REAL_SALT_1), REAL_ENC_1)
        self.assertEqual(enc.build_enc(PARAMS_2, REAL_SALT_2), REAL_ENC_2)

    def test_missing_extra_field_and_empty_salt_are_rejected(self):
        missing = {k: v for k, v in PARAMS_1.items() if k != "captcha"}
        with self.assertRaises(enc.SignatureError):
            enc.build_enc(missing, REAL_SALT_1)
        with self.assertRaises(enc.SignatureError):
            enc.build_enc({**PARAMS_1, "extra": "x"}, REAL_SALT_1)
        with self.assertRaises(enc.SignatureError):
            enc.build_enc(PARAMS_1, "  ")

    def test_renew_signature_has_seven_fields_and_synthetic_vector(self):
        self.assertEqual(enc.build_renew_enc(RENEW_PARAMS, RENEW_SALT), RENEW_ENC)
        with self.assertRaises(enc.SignatureError):
            enc.build_renew_enc({**RENEW_PARAMS, "deptIdEnc": "fixture"}, RENEW_SALT)
        with self.assertRaises(enc.SignatureError):
            enc.build_renew_enc({k: v for k, v in RENEW_PARAMS.items()
                                 if k != "wyToken"}, RENEW_SALT)

    def test_parse_salt_from_select_html(self):
        self.assertEqual(enc.parse_salt(select_page_html()), REAL_SALT_1)
        for bad in ("", "<html></html>", '<input id="submit_enc" value="  "/>'):
            with self.subTest(html=bad):
                with self.assertRaises(ValueError):
                    enc.parse_salt(bad)

    def test_parse_user_info_requires_uid(self):
        user = parse_user_info(seat_page_html())
        self.assertEqual(user, {"uid": "404270468", "uname": "测试用户", "sno": "25123368"})
        for bad in ("<html></html>", "var userLoginInfo = {}||{};",
                    'var userLoginInfo = {"userInfo": {"uname": "x"}}||{};'):
            with self.subTest(html=bad):
                with self.assertRaises(ValueError):
                    parse_user_info(bad)


class ChaoxingCase(OfflineCase):
    def cx_client(self, *, clock=None, session=None):
        session = session or requests.Session()
        session.trust_env = False
        session.cookies.set("fid", "35480", domain="office.chaoxing.com", path="/")
        session.cookies.set("_uid", "404270468", domain="office.chaoxing.com", path="/")
        client = ChaoxingClient(session=session, clock=clock)
        self.addCleanup(client.close)
        return client


class SessionTests(ChaoxingCase):
    def test_bootstrap_parses_user_and_sends_fid_enc(self):
        client = self.cx_client()
        self.wire.add("GET", "/front/third/apps/seat/index", seat_page_html())
        user = client.bootstrap()
        self.assertEqual(user["uid"], "404270468")
        request, _ = self.wire.calls[-1]
        self.assertEqual(parse_qs(urlsplit(request.url).query)["fidEnc"],
                         ["00bae7f2bdea485a"])
        self.assertNotIn("SHU_OAUTH2", request.headers.get("Cookie", ""))

    def test_bootstrap_follows_local_redirect_then_rejects_foreign(self):
        client = self.cx_client()
        self.wire.add("GET", "/front/third/apps/seat/index", "", status=302,
                      headers={"Location": "/front/third/apps/seat/index?fidEnc=00bae7f2bdea485a"})
        self.wire.add("GET", "/front/third/apps/seat/index", seat_page_html())
        self.assertEqual(client.bootstrap()["uid"], "404270468")

    def test_bootstrap_rejects_login_redirect(self):
        client = self.cx_client()
        self.wire.add("GET", "/front/third/apps/seat/index", "", status=302,
                      headers={"Location": "https://passport2.chaoxing.com/login?refer=x"})
        with self.assertRaises(SessionExpired):
            client.bootstrap()

    def test_bootstrap_rejects_page_without_user_info(self):
        client = self.cx_client()
        self.wire.add("GET", "/front/third/apps/seat/index", "<html>登录</html>")
        with self.assertRaises(SessionExpired):
            client.bootstrap()


class QueryTests(ChaoxingCase):
    def test_recent_slices_home_envelope(self):
        client = self.cx_client()
        self.wire.add("GET", "/data/apps/seat/index", {
            "success": True, "data": {"seatConfig": {}, "curReserves": [],
                                      "nearReserves": [{"id": 194166871, "seatNum": "135"}]}})
        recent = client.recent()
        self.assertEqual(recent["current"], [])
        self.assertEqual(recent["near"][0]["id"], 194166871)

    def test_business_failure_carries_server_message(self):
        client = self.cx_client()
        self.wire.add("GET", "/data/apps/seat/index",
                      {"success": False, "msg": "该时间段已过，不可预约！"})
        with self.assertRaises(BusinessError) as caught:
            client.home()
        self.assertIn("该时间段已过", str(caught.exception))
        self.assertEqual(caught.exception.response["msg"], "该时间段已过，不可预约！")

    def test_rooms_validates_day_and_sends_expected_query(self):
        client = self.cx_client()
        with self.assertRaises(ValueError):
            client.rooms("20261005")
        self.wire.add("GET", "/data/apps/seat/room/list",
                      {"success": True, "data": {"seatRoomList": [], "totalRow": 0}})
        client.rooms("2026-10-05")
        query = parse_qs(urlsplit(self.wire.calls[-1][0].url).query)
        self.assertEqual(query["day"], ["2026-10-05"])
        self.assertEqual(query["deptIdEnc"], ["00bae7f2bdea485a"])
        self.assertEqual(query["pageSize"], ["100"])

    def test_availability_is_derived_from_capacity_minus_used(self):
        client = self.cx_client()
        self.wire.add("POST", "/data/apps/seat/room/info", {"success": True, "data": {
            "seatRoom": {"id": 6508, "capacity": 5, "startSeatNum": 1,
                         "firstLevelName": "自修", "secondLevelName": "嘉定联合馆",
                         "thirdLevelName": "一楼自修室"}}})
        self.wire.add("POST", "/data/apps/seat/getusedseatnums", {"success": True, "data": {
            "seatReserves": [{"seatNum": "002", "uid": 999}, {"seatNum": "004", "uid": 998}]}})
        available = client.availability(6508, "2026-10-05", "9:00", "10:00")
        form = form_of(self.wire.calls[-1][0])
        self.assertEqual(form["startTime"], ["09:00"])
        self.assertEqual(form["endTime"], ["10:00"])
        self.assertEqual(available["available"], ["001", "003", "005"])
        self.assertEqual(available["available_count"], 3)
        self.assertTrue(available["derived"])


class FollowupCaptureTests(ChaoxingCase):
    """2026-10-19 续约、签到与暂离流程新见端点；响应均为合成夹具。"""

    def test_reserve_info_supports_captured_get_and_post_forms(self):
        client = self.cx_client()
        detail = {"success": True, "data": {
            "seatConfig": {"preSignDuration": 20}, "scannerBluetooth": False,
            "openDialog": False, "beforeOpenTimeStamp": None,
            "seatReserve": {"id": 12345, "seatNum": "006", "status": 0},
        }}
        self.wire.add("GET", "/data/apps/seat/reserve/info", detail)
        self.wire.add("POST", "/data/apps/seat/reserve/info", detail)
        # reserve/info 的 id 是 roomId；seatReserve.id 才供 sign / leave 使用。
        self.assertEqual(client.reserve_info(6508, "006"), detail)
        self.assertEqual(client.reserve_info(6508, "006", method="POST"), detail)
        get_request, post_request = (call[0] for call in self.wire.calls)
        self.assertEqual(parse_qs(urlsplit(get_request.url).query),
                         {"id": ["6508"], "seatNum": ["6"]})
        self.assertEqual(urlsplit(post_request.url).query, "")
        self.assertEqual(form_of(post_request), {"id": ["6508"], "seatNum": ["6"]})
        for request in (get_request, post_request):
            referer = urlsplit(request.headers["Referer"])
            self.assertEqual(referer.path, "/front/apps/seat/code")
            self.assertEqual(parse_qs(referer.query),
                             {"id": ["6508"], "seatNum": ["6"]})

    def test_used_times_keeps_captured_two_dimensional_timestamp_shape(self):
        client = self.cx_client()
        used = {"success": True, "data": [[1893456000000, 1893459600000]]}
        self.wire.add("POST", "/data/apps/seat/getusedtimes", used)
        self.assertEqual(client.used_times(6508, "006", "2030-01-01"), used)
        self.assertEqual(form_of(self.wire.calls[-1][0]), {
            "roomId": ["6508"], "seatNum": ["006"], "day": ["2030-01-01"],
            "fidEnc": ["00bae7f2bdea485a"],
        })
        # 续约页可内嵌与默认配置不同的 fidEnc；请求需允许传入页面值。
        self.wire.add("POST", "/data/apps/seat/getusedtimes", used)
        self.assertEqual(client.used_times(6508, "006", "2030-01-01",
                                           fid_enc="fixture-page-fid"), used)
        self.assertEqual(form_of(self.wire.calls[-1][0])["fidEnc"],
                         ["fixture-page-fid"])

    def test_room_info_accepts_code_page_form_without_day(self):
        client = self.cx_client()
        info = {"success": True, "data": {"seatRoom": {"id": 6508}}}
        self.wire.add("POST", "/data/apps/seat/room/info", info)
        self.assertEqual(client.room_info(6508, fid_enc="fixture-page-fid"), info)
        self.assertEqual(form_of(self.wire.calls[-1][0]),
                         {"id": ["6508"], "fidEnc": ["fixture-page-fid"]})
        self.wire.add("POST", "/data/apps/seat/room/info", info)
        self.assertEqual(client.room_info(6508, "2030-01-01"), info)
        self.assertEqual(form_of(self.wire.calls[-1][0]), {
            "id": ["6508"], "toDay": ["2030-01-01"],
            "fidEnc": ["00bae7f2bdea485a"], "queryReserve": ["true"],
        })

    def test_sign_and_leave_accept_success_envelopes_without_data(self):
        client = self.cx_client()
        self.wire.add("GET", "/data/apps/seat/sign", {"success": True})
        self.wire.add("POST", "/data/apps/seat/leave", {"success": True})
        self.assertEqual(client.sign(12345), {"success": True})
        self.assertEqual(client.leave(12345), {"success": True})
        sign_request, leave_request = (call[0] for call in self.wire.calls)
        self.assertEqual(parse_qs(urlsplit(sign_request.url).query), {"id": ["12345"]})
        self.assertEqual(form_of(leave_request), {"id": ["12345"]})
        for request in (sign_request, leave_request):
            self.assertEqual(urlsplit(request.headers["Referer"]).path,
                             "/front/apps/seat/code")

    def test_signback_uses_home_get_and_accepts_empty_success_envelope(self):
        client = self.cx_client()
        self.wire.add("GET", "/data/apps/seat/signback", {"success": True})
        self.assertEqual(client.signback(12345), {"success": True})
        request, _ = self.wire.calls[-1]
        self.assertEqual(parse_qs(urlsplit(request.url).query), {"id": ["12345"]})
        self.assertEqual(urlsplit(request.headers["Referer"]).path,
                         "/front/third/apps/seat/index")
        self.assertIsNone(request.body)

    def test_risk_config_and_address_use_captured_parameter_names(self):
        client = self.cx_client()
        risk = {"success": True, "data": {"riskCheckOpen": False,
                                            "riskCheckType": "none"}}
        address = {"success": True, "data": {"addressArr": [
            {"location": "fixture", "offset": 0, "offsetReal": 0}]}}
        self.wire.add("POST", "/data/apps/seat/risk/check/config", risk)
        self.wire.add("GET", "/data/apps/seat/address", address)
        self.assertEqual(client.risk_config("seat", "fixture-app"), risk)
        self.assertEqual(client.address(35480, 6508), address)
        risk_request, address_request = (call[0] for call in self.wire.calls)
        self.assertEqual(form_of(risk_request),
                         {"appType": ["seat"], "appId": ["fixture-app"]})
        self.assertEqual(parse_qs(urlsplit(address_request.url).query),
                         {"deptId": ["35480"], "roomId": ["6508"]})

    def test_domain_rules_and_i18n_have_no_request_parameters(self):
        client = self.cx_client()
        rules = {"success": True, "data": {"rules": []}}
        i18n = {"success": True, "data": {"fixtureKey": "fixture translation"}}
        self.wire.add("GET", "/data/apps/reserve/link/domain/rules", rules)
        self.wire.add("GET", "/data/apps/seat/i18n", i18n)
        self.assertEqual(client.link_domain_rules(), rules)
        self.assertEqual(client.i18n(), i18n)
        self.assertTrue(all(not urlsplit(request.url).query
                            for request, _ in self.wire.calls))

    def test_existing_read_only_wrappers_use_captured_paths_and_queries(self):
        client = self.cx_client()
        fixture = {"success": True, "data": {"fixture": True}}
        fid = "00bae7f2bdea485a"
        cases = (
            ("cur_used", (), "/data/apps/seat/curusedshow", {"fidEnc": [fid]}),
            ("person_role", (), "/data/apps/seat/person/role", {"fidEnc": [fid]}),
            ("entrance_config", ("2",), "/data/apps/seat/entrance/config",
             {"appType": ["2"], "fidEnc": [fid]}),
            ("identity_verify", ("fixture-map",), "/data/apps/seat/identity/verify",
             {"mappId": ["fixture-map"], "fidEnc": [fid]}),
        )
        for method, arguments, path, query in cases:
            with self.subTest(method=method):
                self.wire.add("GET", path, fixture)
                self.assertEqual(getattr(client, method)(*arguments), fixture)
                request, _ = self.wire.calls[-1]
                self.assertEqual(urlsplit(request.url).path, path)
                self.assertEqual(parse_qs(urlsplit(request.url).query), query)


class SubmitTests(ChaoxingCase):
    def test_submit_fetches_fresh_salt_and_signs_form(self):
        client = self.cx_client()
        self.wire.add("GET", "/front/third/apps/seat/select", select_page_html(REAL_SALT_1))
        self.wire.add("POST", "/data/apps/seat/submit", {"success": True, "data": {
            "seatReserve": {"id": 194166871, "seatNum": "135"}, "preSignDuration": 20}})
        result = client.submit(6508, "2026-10-05", "21:00", "22:00", "135")
        self.assertEqual(result["data"]["seatReserve"]["id"], 194166871)
        form = form_of(self.wire.calls[-1][0])
        self.assertEqual(form["enc"], [REAL_ENC_1])
        self.assertEqual(form["seatNum"], ["135"])
        self.assertEqual(form["captcha"], [""])
        paths = [urlsplit(r.url).path for r, _ in self.wire.calls]
        self.assertEqual(paths, ["/front/third/apps/seat/select", "/data/apps/seat/submit"])

    def test_submit_throttle_includes_business_failures_and_refetches_salt(self):
        now = [100.0]
        client = self.cx_client(clock=lambda: now[0])
        self.wire.add("GET", "/front/third/apps/seat/select", select_page_html(REAL_SALT_1))
        self.wire.add("POST", "/data/apps/seat/submit",
                      {"success": False, "msg": "同一用户10秒只能提交一次"})
        with self.assertRaises(BusinessError):
            client.submit(6508, "2026-10-05", "21:00", "22:00", "135")
        now[0] = 105.0
        with self.assertRaises(SubmissionThrottled):
            client.submit(6508, "2026-10-05", "21:00", "22:00", "135")
        now[0] = 111.0
        self.wire.add("GET", "/front/third/apps/seat/select", select_page_html(REAL_SALT_2))
        self.wire.add("POST", "/data/apps/seat/submit",
                      {"success": True, "data": {"seatReserve": {"id": 1}}})
        client.submit(6508, "2026-10-05", "21:00", "22:00", "099")
        selects = [r for r, _ in self.wire.calls
                   if urlsplit(r.url).path.endswith("/seat/select")]
        self.assertEqual(len(selects), 2, "每次提交都要重新拉取 select 页取新盐")

    def test_submit_without_reserve_id_is_protocol_error(self):
        client = self.cx_client()
        self.wire.add("GET", "/front/third/apps/seat/select", select_page_html(REAL_SALT_1))
        self.wire.add("POST", "/data/apps/seat/submit", {"success": True, "data": {}})
        with self.assertRaises(ProtocolError):
            client.submit(6508, "2026-10-05", "21:00", "22:00", "135")

    def test_select_error_page_becomes_business_error(self):
        client = self.cx_client()
        self.wire.add("GET", "/front/third/apps/seat/select", "", status=302,
                      headers={"Location": "/front/apps/reserve/error/code/500"
                                            "?msg=%E5%BD%93%E5%89%8D%E5%8C%BA%E5%9F%9F"
                                            "%E6%9C%AA%E5%88%B0%E5%BC%80%E6%94%BE"
                                            "%E9%A2%84%E7%BA%A6%E6%97%B6%E9%97%B4"})
        self.wire.add("GET", "/front/apps/reserve/error/code/500", "<html>错误</html>")
        with self.assertRaises(BusinessError) as caught:
            client.prepare_submit(6508, "2026-10-06", "21:00", "22:00", "135")
        self.assertIn("未到开放预约时间", str(caught.exception))

    def test_cancel_validates_numeric_id(self):
        client = self.cx_client()
        with self.assertRaises(ValueError):
            client.cancel("BOOKING_LIB")
        self.wire.add("GET", "/data/apps/seat/cancel", {"success": True})
        self.assertEqual(client.cancel(194166871), {"success": True})
        self.assertEqual(parse_qs(urlsplit(self.wire.calls[-1][0].url).query)["id"],
                         ["194166871"])


class RenewTests(ChaoxingCase):
    """code 页的续约提交与选座 select 页是两条不同签名路径。"""

    @staticmethod
    def code_page_html():
        return ("<html><script>var signType = '0', "
                "fidEnc = 'fixture-page-fid', uniqueDomainPath = '';</script>"
                f'<input type="hidden" id="submit_enc" value="{RENEW_SALT}"/></html>')

    def test_prepare_renew_reads_code_page_and_only_prepares_seven_fields(self):
        client = self.cx_client()
        self.wire.add("GET", "/front/apps/seat/code", self.code_page_html())
        prepared = client.prepare_renew(6508, "2030-01-01", "10:00", "11:00", "048")
        request, _ = self.wire.calls[-1]
        self.assertEqual(parse_qs(urlsplit(request.url).query),
                         {"id": ["6508"], "seatNum": ["48"]})
        self.assertEqual(prepared["form"], {**RENEW_PARAMS, "enc": RENEW_ENC})
        self.assertEqual(prepared["fidEnc"], "fixture-page-fid")
        self.assertEqual(len(self.wire.calls), 1, "准备续约时不可提交预约")

    def test_renew_posts_signed_form_without_dept_id_enc(self):
        client = self.cx_client()
        self.wire.add("GET", "/front/apps/seat/code", self.code_page_html())
        success = {"success": True, "data": {"seatReserve": {"id": 12345,
                                                            "seatNum": "048"}}}
        self.wire.add("POST", "/data/apps/seat/submit", success)
        self.assertEqual(client.renew(6508, "2030-01-01", "10:00", "11:00", "048"), success)
        self.assertEqual(form_of(self.wire.calls[-1][0]),
                         {key: [value] for key, value in
                          {**RENEW_PARAMS, "enc": RENEW_ENC}.items()})
        self.assertEqual([urlsplit(request.url).path for request, _ in self.wire.calls],
                         ["/front/apps/seat/code", "/data/apps/seat/submit"])

    def test_prepared_renew_json_hides_salt_and_personal_identifiers(self):
        client = self.cx_client()
        self.wire.add("GET", "/front/apps/seat/code", self.code_page_html())
        prepared = client.prepare_renew(6508, "2030-01-01", "10:00", "11:00", "048")
        printable = cx_ui.safe_output({
            "prepared_renew": prepared,
            "user": {"uid": "fixture-private-uid", "sno": "fixture-private-sno",
                     "uname": "fixture-private-name", "mobile": "fixture-private-phone"},
            "submit_enc": "fixture-hidden-submit-token",
        })
        encoded = json.dumps(printable, ensure_ascii=False)
        for private in (RENEW_SALT, "fixture-private-uid", "fixture-private-sno",
                        "fixture-private-name", "fixture-private-phone",
                        "fixture-hidden-submit-token"):
            self.assertNotIn(private, encoded)
        self.assertEqual(printable["prepared_renew"]["salt"], "<redacted>")
        self.assertEqual(printable["prepared_renew"]["form"]["roomId"], "6508")


class ChaoxingCliTests(unittest.TestCase):
    """仅测参数解析与客户端分发；不加载凭据也不触发网络。"""

    def test_renew_dry_run_dispatches_only_prepare(self):
        args = poc.build_parser().parse_args([
            "--system", "chaoxing", "renew", "--room", "6508", "--day", "2030-01-01",
            "--begin", "10:00", "--end", "11:00", "--seat", "048", "--dry-run",
        ])
        client = Mock()
        client.prepare_renew.return_value = {"form": {**RENEW_PARAMS, "enc": RENEW_ENC},
                                             "salt": RENEW_SALT}
        result = poc.run_cx_command(client, args)
        self.assertEqual(args.system, "chaoxing")
        self.assertTrue(result["dry_run"])
        self.assertFalse(result["submitted"])
        client.prepare_renew.assert_called_once_with(
            "6508", "2030-01-01", "10:00", "11:00", "048")
        client.renew.assert_not_called()

    def test_reserve_info_post_and_seat_actions_dispatch(self):
        client = Mock()
        client.reserve_info.return_value = {"success": True, "data": {}}
        args = poc.build_parser().parse_args([
            "--system", "chaoxing", "reserve-info", "--room", "6508",
            "--seat", "048", "--post",
        ])
        self.assertEqual(poc.run_cx_command(client, args), client.reserve_info.return_value)
        client.reserve_info.assert_called_once_with("6508", "048", method="POST")
        for operation in ("sign", "signback", "leave"):
            with self.subTest(operation=operation):
                client = Mock()
                getattr(client, operation).return_value = {"success": True}
                client.recent.return_value = {"current": []}
                args = poc.build_parser().parse_args([
                    "--system", "chaoxing", operation, "12345",
                ])
                result = poc.run_cx_command(client, args)
                getattr(client, operation).assert_called_once_with("12345")
                self.assertEqual(result["operation"], operation)
                self.assertEqual(result["reserve_id"], "12345")

    def test_existing_read_only_commands_parse_and_dispatch(self):
        cases = (
            ("cur-used", [], "cur_used", ()),
            ("person-role", [], "person_role", ()),
            ("entrance-config", ["--app-type", "2"], "entrance_config", ("2",)),
            ("identity-verify", ["--mapp-id", "fixture-map"], "identity_verify",
             ("fixture-map",)),
        )
        for command, options, method, arguments in cases:
            with self.subTest(command=command):
                args = poc.build_parser().parse_args(
                    ["--system", "chaoxing", command, *options])
                client = Mock()
                getattr(client, method).return_value = {"success": True}
                self.assertEqual(args.system, "chaoxing")
                self.assertEqual(poc.run_cx_command(client, args), {"success": True})
                getattr(client, method).assert_called_once_with(*arguments)


class CredentialsTests(unittest.TestCase):
    def test_build_requires_uid_and_chaoxing_cookies(self):
        session = requests.Session()
        session.cookies.set("SPHYS_SESSION", "x", domain="there.shu.edu.cn", path="/")
        with self.assertRaises(cx_creds.CredentialsError):
            cx_creds.build(session, {"uid": "1", "uname": "n", "sno": "s"})
        with self.assertRaises(cx_creds.CredentialsError):
            cx_creds.build(session, {})
        session.cookies.set("fid", "35480", domain="chaoxing.com", path="/")
        payload = cx_creds.build(session, {"uid": "404270468", "uname": "测试", "sno": "25123368"})
        self.assertEqual(payload["chaoxing"]["dept_id"], "35480")
        self.assertEqual({c["name"] for c in payload["cookies"]}, {"fid"})

    def test_save_load_roundtrip_and_summary_has_no_personal_values(self):
        session = requests.Session()
        session.cookies.set("fid", "35480", domain=".chaoxing.com", path="/")
        payload = cx_creds.build(session, {"uid": "404270468", "uname": "测试用户",
                                           "sno": "25123368"})
        with tempfile.TemporaryDirectory(prefix="cx-test-") as directory:
            path = Path(directory) / "credentials.json"
            cx_creds.save(payload, path)
            loaded = cx_creds.load(path)
            self.assertEqual(loaded["cookies"], payload["cookies"])
            summary = cx_creds.describe(loaded, path)
            for secret in ("404270468", "25123368", "测试用户"):
                self.assertNotIn(secret, summary)

    def test_restore_rejects_foreign_or_sso_cookies(self):
        session = requests.Session()
        session.cookies.set("fid", "35480", domain=".chaoxing.com", path="/")
        payload = cx_creds.build(session, {"uid": "404270468", "uname": "测试", "sno": "25123368"})
        for mutation in ({"domain": "there.shu.edu.cn"}, {"domain": "newsso.shu.edu.cn"},
                         {"name": "SHU_OAUTH2"}, {"path": "bad-path"}, {"value": "bad\r\n"}):
            with self.subTest(mutation=mutation):
                tampered = json.loads(json.dumps(payload))
                tampered["cookies"][0].update(mutation)
                with self.assertRaises(cx_creds.CredentialsError):
                    cx_creds.restore_session(tampered)


class RedeemTests(OfflineCase):
    """换会话已外置到 vendor 子模块（systems/chaoxing.com）；这里验证 sso/runner 的桥接：
    以同一 SSO 会话调 vendor 实现，再把 chaoxing.com 域 Cookie 组装成座位侧凭据。"""

    @staticmethod
    def _client():
        from sso.client import ShuSSO

        client = ShuSSO()
        session = requests.Session()
        session.trust_env = False
        session.cookies.set("fid", "35480", domain="chaoxing.com", path="/")
        session.cookies.set("_uid", "404270468", domain="chaoxing.com", path="/")
        client.sess = session
        return client

    def test_chain_reaches_office_and_builds_credentials(self):
        from sso.runner import chaoxing_redeem

        client = self._client()
        authorize_location = ("https://zhstsg-jx.5read.com/oauthlogin/loginByCodeSchoolid"
                              "?code=fixture-code&schoolid=2434&type=xxt")
        login6_location = ("https://passport2-api.chaoxing.com/api/v2/login6"
                           "?schoolid=35480&name=fixture-sno&pd=4&enc=fixture-enc&oauth=true")
        self.wire.add("GET", "/oauth/authorize", "", status=302,
                      headers={"Location": authorize_location})
        self.wire.add("GET", "/oauthlogin/loginByCodeSchoolid", "", status=302,
                      headers={"Location": login6_location})
        self.wire.add("GET", "/api/v2/login6", "", status=302,
                      headers={"Location": "https://i.mooc.chaoxing.com/space/index"})
        self.wire.add("GET", "/space/index", "<html>landing</html>")
        self.wire.add("GET", "/front/third/apps/seat/index", seat_page_html())

        result = chaoxing_redeem(client, username="25123368")
        self.assertTrue(result["logged_in"], result)
        self.assertEqual(result["user"]["uid"], "404270468")
        self.assertEqual(result["user"]["sno"], "25123368")
        self.assertEqual({c["name"] for c in result["credentials"]["cookies"]},
                         {"fid", "_uid"})
        self.assertEqual(result["cookie_count"], 2)
        paths = [urlsplit(r.url).path for r, _ in self.wire.calls]
        self.assertEqual(paths, ["/oauth/authorize", "/oauthlogin/loginByCodeSchoolid",
                                 "/api/v2/login6", "/space/index",
                                 "/front/third/apps/seat/index"])
        # 座位侧 ShuSSO.record 白名单只保留流程摘要：授权码 / enc 不进入 trace
        self.assertNotIn("fixture-code", json.dumps(client.trace, ensure_ascii=False))
        self.assertNotIn("fixture-enc", json.dumps(client.trace, ensure_ascii=False))

    def test_session_not_reused_stops_before_chain(self):
        from sso.runner import chaoxing_redeem

        client = self._client()
        self.wire.add("GET", "/oauth/authorize", "", status=302,
                      headers={"Location": "https://newsso.shu.edu.cn/oauth2/login/context"})
        result = chaoxing_redeem(client)
        self.assertFalse(result["logged_in"])
        self.assertEqual(result["reason"], "session_not_reused")
        self.assertEqual(len(self.wire.calls), 1)

    def test_chain_failure_is_not_false_success(self):
        from sso.runner import chaoxing_redeem

        client = self._client()
        self.wire.add("GET", "/oauth/authorize", "", status=302,
                      headers={"Location": "https://zhstsg-jx.5read.com/oauthlogin/loginByCodeSchoolid?code=x"})
        self.wire.add("GET", "/oauthlogin/loginByCodeSchoolid", "", status=302,
                      headers={"Location": "https://other.example/landing"})
        self.wire.add("GET", "/landing", "<html>wrong site</html>")
        result = chaoxing_redeem(client)
        self.assertFalse(result["logged_in"])
        self.assertEqual(result["reason"], "chain_failed")

    def test_login_page_without_user_info_is_invalid_session(self):
        from sso.runner import chaoxing_redeem

        client = self._client()
        self.wire.add("GET", "/oauth/authorize", "", status=302,
                      headers={"Location": "https://zhstsg-jx.5read.com/oauthlogin/loginByCodeSchoolid?code=x"})
        self.wire.add("GET", "/oauthlogin/loginByCodeSchoolid", "", status=302,
                      headers={"Location": "https://passport2-api.chaoxing.com/api/v2/login6?x=1"})
        self.wire.add("GET", "/api/v2/login6", "", status=302,
                      headers={"Location": "https://i.mooc.chaoxing.com/space/index"})
        self.wire.add("GET", "/space/index", "<html>landing</html>")
        self.wire.add("GET", "/front/third/apps/seat/index", "<html>请先登录</html>")
        result = chaoxing_redeem(client)
        self.assertFalse(result["logged_in"])
        self.assertEqual(result["reason"], "invalid_session")


if __name__ == "__main__":
    unittest.main(verbosity=2)
