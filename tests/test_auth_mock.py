#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""真实 requests 准备请求 + 合成服务端：SSO 换会话与 CLI 离线集成。

密码加密调用用占位密文替代，扫码响应均为合成值；禁止任何 socket 连接。
运行：python tests/test_auth_mock.py
"""

from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import copy
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_offline import (BASE, END, PAGES, PROFILE, START, OfflineCase,
                          area_envelope, page_html)
from seat.there import credentials
from sso import config
from sso.client import ShuSSO
from sso.runner import login_all_systems, session_params
import login
import poc


class AuthIntegrationTests(OfflineCase):
    def setUp(self):
        super().setUp()
        self.temp = tempfile.TemporaryDirectory(prefix="seat-auth-test-")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "credentials.json"
        self.stack.enter_context(patch.object(config, "CAPTURE_DIR", Path(self.temp.name) / "captures"))

    def args(self, room_type="LIB_SEAT"):
        # 登录流程单测聚焦 there：显式固定 --system there（默认 both 会连带走超星换会话）。
        return login.build_parser().parse_args(
            ["--out", str(self.path), "--room-type", room_type, "--system", "there"])

    def plan_exchange(self, client, room_type="LIB_SEAT", callback_status=302,
                      callback_location="/web/index", profile=None):
        def prewarm(request):
            self.assertEqual(urlsplit(request.url).hostname, "there.shu.edu.cn")
            self.assertNotIn("SHU_OAUTH2", request.headers.get("Cookie", ""))
            client.sess.cookies.set("SPHYS_SESSION", "fixture-there-cookie", domain="there.shu.edu.cn", path="/", secure=True)
            return ""
        self.wire.add("GET", "/login", prewarm, status=302,
                      headers={"Location": "https://newsso.shu.edu.cn/oauth/authorize?state=fixture-state"})
        def inspect_authorize(request, kwargs):
            query = parse_qs(urlsplit(request.url).query)
            self.assertEqual(urlsplit(request.url).hostname, "newsso.shu.edu.cn")
            self.assertEqual(query["client_id"], [config.SYSTEMS["there"]["client_id"]])
            self.assertEqual(query["redirect_uri"], [BASE + "/login-oauth2"])
            self.assertEqual(query["state"], ["fixture-state"])
            self.assertIn("SHU_OAUTH2=fixture-newsso-cookie", request.headers.get("Cookie", ""))
            self.assertNotIn("SPHYS_SESSION", request.headers.get("Cookie", ""))
            self.assertTrue(kwargs["verify"])
            self.assertFalse(kwargs["allow_redirects"])
        self.wire.add("GET", "/oauth/authorize", "", status=302,
                      headers={"Location": BASE + "/login-oauth2?code=fixture-oauth-code&state=fixture-state"},
                      inspect=inspect_authorize)
        self.wire.add("GET", "/login-oauth2", "", status=callback_status,
                      headers={"Location": callback_location} if callback_location else {})
        if callback_status == 302 and callback_location.startswith("/web"):
            self.wire.add("GET", "/web/index", "<html>合成业务落地页</html>")
            self.wire.add("GET", PAGES[room_type], page_html())
            def inspect_profile(request, kwargs):
                self.assertNotIn("Origin", request.headers)
                self.assertEqual(request.headers["Referer"], BASE + PAGES[room_type])
                self.assertEqual(request.headers["x-hys-session"], "fixture-html-session")
                self.assertEqual(request.headers["x-room-type"], room_type)
                self.assertNotIn("SHU_OAUTH2", request.headers.get("Cookie", ""))
            self.wire.add("GET", "/api/v3/my/profile", PROFILE if profile is None else profile,
                          inspect=inspect_profile)

    def client(self):
        client = ShuSSO()
        client.sess.cookies.set("SHU_OAUTH2", "fixture-newsso-cookie", domain="newsso.shu.edu.cn", path="/", secure=True)
        self.addCleanup(client.sess.close)
        return client

    def test_oauth_callback_and_mobile_verification_for_four_types(self):
        for room_type in PAGES:
            with self.subTest(room_type=room_type):
                client = self.client()
                self.plan_exchange(client, room_type)
                with redirect_stdout(StringIO()):
                    result = login_all_systems(client, room_type=room_type)["there"]
                self.assertTrue(result["logged_in"])
                saved = credentials.build(client.sess, room_type, result["profile"])
                self.assertEqual([c["name"] for c in saved["cookies"]], ["SPHYS_SESSION"])
                self.assertNotIn("fixture-oauth-code", json.dumps(client.trace))

    def test_empty_200_callback_does_not_overwrite_existing_credentials(self):
        client = self.client()
        self.path.write_text("existing-file-marker", encoding="utf-8")
        self.plan_exchange(client, callback_status=200, callback_location="")
        with redirect_stdout(StringIO()):
            status = login.finalize(client, self.args())
        self.assertEqual(status, 5)
        self.assertEqual(self.path.read_text(encoding="utf-8"), "existing-file-marker")
        self.assertNotIn("fixture-oauth-code", (Path(self.temp.name) / "captures" / "login-result.json").read_text(encoding="utf-8"))

    def test_external_callback_redirect_is_not_followed(self):
        client = self.client()
        self.plan_exchange(client, callback_location="https://other.example/web/index")
        with redirect_stdout(StringIO()):
            result = login_all_systems(client)["there"]
        self.assertFalse(result["logged_in"])
        self.assertEqual(result["reason"], "unsafe_callback_redirect")
        self.assertEqual(len(self.wire.calls), 3)

    def test_http_callback_redirect_is_upgraded_to_https(self):
        """实测：/login-oauth2 成功后 302 到 http://there.shu.edu.cn/web?authJump=…（同站 http）。
        跟随前必须升级为 https（不向明文地址发请求），域与路径校验不变。"""
        client = self.client()
        self.plan_exchange(client,
                           callback_location="http://there.shu.edu.cn/web?authJump=fixture-jump")

        def inspect_upgrade(request, kwargs):
            self.assertTrue(request.url.startswith("https://there.shu.edu.cn/web"))
            self.assertIn("authJump=fixture-jump", request.url)

        self.wire.add("GET", "/web", "<html>合成业务落地页</html>", inspect=inspect_upgrade)
        self.wire.add("GET", PAGES["LIB_SEAT"], page_html())
        self.wire.add("GET", "/api/v3/my/profile", PROFILE)
        with redirect_stdout(StringIO()):
            result = login_all_systems(client)["there"]
        self.assertTrue(result["logged_in"])
        self.assertTrue(all(request.url.startswith("https://")
                            for request, _ in self.wire.calls))

    def test_main_landing_variant_is_followed(self):
        """实测（带 state 的项目流程）：回调 302 到 http://there.shu.edu.cn/main?authJump=…，
        再 302 到 /web 落地；两跳都必须升 https 且依次跟随。"""
        client = self.client()
        self.plan_exchange(client,
                           callback_location="http://there.shu.edu.cn/main?authJump=fixture-jump")

        def inspect_main(request, kwargs):
            self.assertTrue(request.url.startswith("https://there.shu.edu.cn/main"))

        def inspect_web(request, kwargs):
            self.assertEqual(request.url, "https://there.shu.edu.cn/web")

        self.wire.add("GET", "/main", "", status=302,
                      headers={"Location": "https://there.shu.edu.cn/web"}, inspect=inspect_main)
        self.wire.add("GET", "/web", "<html>合成业务落地页</html>", inspect=inspect_web)
        self.wire.add("GET", PAGES["LIB_SEAT"], page_html())
        self.wire.add("GET", "/api/v3/my/profile", PROFILE)
        with redirect_stdout(StringIO()):
            result = login_all_systems(client)["there"]
        self.assertTrue(result["logged_in"])
        self.assertTrue(all(request.url.startswith("https://")
                            for request, _ in self.wire.calls))

    def test_anonymous_profile_cannot_generate_credentials(self):
        client = self.client()
        profile = copy.deepcopy(PROFILE)
        profile["data"]["isAnonymous"] = True
        self.plan_exchange(client, profile=profile)
        with redirect_stdout(StringIO()):
            self.assertEqual(login.finalize(client, self.args()), 5)
        self.assertFalse(self.path.exists())

    def test_password_sms_2fa_then_private_credentials(self):
        client = self.client()
        self.wire.add("POST", "/oauth/userLogin", {"message": "success", "twoStepRequired": True, "twoStepMethods": {"sms": True}})
        self.wire.add("POST", "/oauth/twoStep/send", {"message": "success"})
        self.wire.add("POST", "/oauth/twoStep/verify", {"message": "success"})
        self.plan_exchange(client)
        args = self.args()
        args.method = "sms"
        output = StringIO()
        with patch.object(login, "ShuSSO", return_value=client), \
                patch("builtins.input", side_effect=["fixture-student", "fixture-sms-code"]), \
                patch.object(login.getpass, "getpass", return_value="fixture-password"), \
                patch("src.client.rsa_encrypt_password", return_value="fixture-encrypted-password"), \
                patch.object(login, "rsa_encrypt_password", return_value="fixture-encrypted-password"), \
                redirect_stdout(output):
            self.assertEqual(login.password_flow(args), 0)
        login_body = json.loads(self.wire.calls[0][0].body)
        verify_body = json.loads(self.wire.calls[2][0].body)
        self.assertEqual(login_body["password"], "fixture-encrypted-password")
        self.assertEqual(login_body["params"], session_params())
        self.assertEqual(verify_body["code"], "fixture-sms-code")
        self.assertEqual(verify_body["method"], "sms")
        saved = credentials.load(self.path)
        self.assertEqual(saved["room_type"], "LIB_SEAT")
        text = self.path.read_text(encoding="utf-8") + output.getvalue()
        for value in ("fixture-password", "fixture-sms-code", "fixture-newsso-cookie", "fixture-oauth-code"):
            self.assertNotIn(value, text)

    def test_wecom_scan_then_same_exchange(self):
        client = self.client()
        wecom = config.WECOM
        self.wire.add("GET", urlsplit(wecom["qrcode_base"]).path, '<img src="qrImg?key=aabbccdd">')
        self.wire.add("GET", urlsplit(wecom["longpoll"]).path,
                      'jsonpCallback({"status":"QRCODE_SCAN_SUCC","auth_code":"fixture-scan-code"})')
        self.wire.add("GET", urlsplit(wecom["redirect_uri"]).path, "", status=302,
                      headers={"Location": "https://newsso.shu.edu.cn/"})
        self.plan_exchange(client, "STATION")
        args = self.args("STATION")
        args.no_qr = True
        output = StringIO()
        with patch.object(login, "ShuSSO", return_value=client), redirect_stdout(output), \
                patch.object(output, "isatty", return_value=True):
            self.assertEqual(login.wecom_scan_flow(args), 0)
        self.assertNotIn("fixture-scan-code", output.getvalue())
        self.assertEqual(credentials.load(self.path)["room_type"], "STATION")
        captures = "".join(p.read_text(encoding="utf-8") for p in (Path(self.temp.name) / "captures").glob("*.json"))
        for value in ("aabbccdd", "fixture-scan-code", "fixture-newsso-cookie", "fixture-oauth-code"):
            self.assertNotIn(value, captures)


class CliIntegrationTests(OfflineCase):
    def setUp(self):
        super().setUp()
        self.temp = tempfile.TemporaryDirectory(prefix="seat-cli-test-")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "credentials.json"
        session = credentials.manual_session("SPHYS_SESSION=fixture-cookie")
        credentials.save(credentials.build(session, "LIB_SEAT", PROFILE), self.path)
        session.close()

    def test_default_cli_reads_all_four_systems_without_mutation(self):
        for room_type in PAGES:
            self.wire.add("GET", PAGES[room_type], page_html())
            self.wire.add("GET", "/api/v3/my/profile", PROFILE)
            self.wire.add("GET", "/api/v3/my/bookings/recent", {"code": 0, "data": []})
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(poc.main(["--credentials", str(self.path), "--json"]), 0)
        parsed = json.loads(output.getvalue())
        self.assertTrue(parsed["read_only"])
        self.assertEqual(len(parsed["systems"]), 4)
        self.assertTrue(all(request.method == "GET" for request, _ in self.wire.calls))

    def test_cli_dry_run_builds_body_without_post_or_identity_output(self):
        self.wire.add("GET", PAGES["LIB_SEAT"], page_html())
        self.wire.add("GET", "/api/v3/my/profile", PROFILE)
        self.wire.add("GET", "/api/v3/booking-status/areas/fixture-area", area_envelope())
        output = StringIO()
        with redirect_stdout(output):
            status = poc.main(["book", "--credentials", str(self.path), "--json", "--area", "fixture-area",
                               "--room", "fixture-room", "--begin", START, "--end", END, "--dry-run"])
        self.assertEqual(status, 0)
        parsed = json.loads(output.getvalue())
        self.assertTrue(parsed["dry_run"])
        self.assertFalse(parsed["submitted"])
        self.assertEqual(parsed["request"]["rooms"][0]["id"], "fixture-room")
        self.assertNotIn("fixture-user", output.getvalue())
        self.assertNotIn("测试用户", output.getvalue())
        self.assertTrue(all(request.method == "GET" for request, _ in self.wire.calls))

    def test_check_does_not_change_credentials_when_session_fails(self):
        before = self.path.read_bytes()
        self.wire.add("GET", PAGES["LIB_SEAT"], "", status=302,
                      headers={"Location": "https://newsso.shu.edu.cn/oauth2/login/"})
        args = login.build_parser().parse_args(["--check", "--out", str(self.path),
                                                "--system", "there"])
        with redirect_stdout(StringIO()):
            self.assertEqual(login.check_flow(args), 6)
        self.assertEqual(self.path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
