#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统一身份认证 → 座位系统会话 → 验证后写私有凭据（there + 超星/学习通）。

    ① 认证    RSA 密码 + 可选 sms/wecom 二步验证，或企业微信扫码
    ② 换会话  there: /login 预置 Cookie → newsso authorize → /login-oauth2
              超星: newsso authorize → 5read → login6（同一认证会话，两条独立链路）
    ③ 验证    there: 移动入口 sessionId + 非匿名 profile
              超星: office 座位首页 userLoginInfo

`--system` 选择登录范围（默认 both）。两套会话分别写入独立凭据文件，
互不影响；任一系统失败不写该系统的伪成功凭据。

结构沿用 shu-otp-poc / shu-ds-poc。SSO 由固定版本子模块实现；密码、验证码、
扫码 key 和 SSO 会话不落盘。凭据只含目标域 Cookie records，保留域/路径/有效期。
"""

from __future__ import annotations

import argparse
import getpass
import math
import os
import sys

from seat.chaoxing import credentials as cx_creds_mod
from seat.chaoxing.client import ChaoxingClient, ChaoxingError
from seat.there import credentials as creds_mod
from seat.there.client import SeatClient
from sso import config
from sso.client import ShuSSO
from sso.runner import login_all_systems, save_evidence, session_params
from sso.ui import (banner, choose_login_mode, print_error_hint, print_summary,
                    print_wecom_qr)
from sso.utils import log, rsa_encrypt_password, save_json


# ---------------------------------------------------------------------------
# 凭据组装与验证
# ---------------------------------------------------------------------------

def build_credentials(client: ShuSSO, result: dict, args, username: str = "") -> dict:
    return creds_mod.build(client.sess, args.room_type, result.get("profile") or {},
                           username=username)


def write_credentials(args, payload: dict) -> int:
    try:
        path = creds_mod.save(payload, args.out)
    except Exception as exc:
        log(f"\n  ✗ 凭据写入失败（{type(exc).__name__}）")
        return 9
    log("\n" + "=" * 62)
    log(" 凭据已生成")
    log("=" * 62)
    log(f"   {creds_mod.describe(payload, path)}")
    log("   验证范围：本次选定移动入口；其它入口需分别 bootstrap/profile 验证")
    log("=" * 62)
    log("\n 下一步：python poc.py profile\n         python login.py --check")
    return 0


def probe_profile(session, args) -> dict:
    """只读探活；原始 profile 只在内存返回，不打印/写入 captures。"""
    try:
        client = SeatClient(session=session, room_type=args.room_type, base=args.base,
                            timeout=args.timeout, verify=not args.insecure)
        bootstrap = client.bootstrap()
        if not isinstance(bootstrap, dict) or not bootstrap.get("sessionId"):
            return {"ok": False, "reason": "invalid_bootstrap"}
        profile = client.profile()
        creds_mod.build(session, args.room_type, profile)
        return {"ok": True, "profile": profile, "room_type": args.room_type}
    except Exception as exc:
        return {"ok": False, "reason": "profile_verification_failed",
                "error_type": type(exc).__name__}


def _print_probe(probe: dict) -> None:
    if probe.get("ok"):
        log(f"  ✓ {probe.get('room_type')} 移动入口及非匿名 profile 已验证")
    else:
        log(f"  ✗ 验证失败：{probe.get('reason')}（{probe.get('error_type') or '未完成'}）")


def check_flow(args) -> int:
    """只读验证；成功或失败均不修改已有凭据。"""
    systems = _requested_systems(args)
    ok = True
    if "there" in systems:
        try:
            creds = creds_mod.load(args.out)
            session = creds_mod.restore_session(creds)
        except creds_mod.CredentialsError as exc:
            log(f"\n  ✗ {exc}")
            return 9
        log("\n[复探] 用已有 Cookie 验证移动入口及 profile ...")
        log(f"   {creds_mod.describe(creds, args.out)}")
        try:
            probe = probe_profile(session, args)
        finally:
            session.close()
        _print_probe(probe)
        ok = bool(probe.get("ok"))
    if "chaoxing" in systems:
        ok = _check_chaoxing(args) and ok
    return 0 if ok else 6


def _check_chaoxing(args) -> bool:
    """只读验证超星凭据：office 座位首页能解析出当前用户即有效。"""
    try:
        creds = cx_creds_mod.load(getattr(args, "out_chaoxing", None))
        session = cx_creds_mod.restore_session(creds)
    except cx_creds_mod.CredentialsError as exc:
        log(f"\n  ✗ {exc}")
        return False
    log("\n[复探] 用已有超星 Cookie 验证 office 会话及用户信息 ...")
    log(f"   {cx_creds_mod.describe(creds, getattr(args, 'out_chaoxing', None))}")
    try:
        client = ChaoxingClient(session=session, timeout=args.timeout,
                                verify=not args.insecure)
        client.bootstrap()
    except ChaoxingError as exc:
        log(f"  ✗ 超星验证失败：{type(exc).__name__}")
        return False
    finally:
        session.close()
    log("  ✓ 超星 office 会话及用户信息已验证")
    return True


def _requested_systems(args) -> tuple[str, ...]:
    """--system there|chaoxing|both（默认 both）展开为登录范围。"""
    return {"there": ("there",), "chaoxing": ("chaoxing",),
            "both": ("there", "chaoxing")}.get(getattr(args, "system", "both"),
                                               ("there", "chaoxing"))


def _write_cx_credentials(args, payload: dict) -> int:
    try:
        path = cx_creds_mod.save(payload, getattr(args, "out_chaoxing", None))
    except Exception as exc:
        log(f"\n  ✗ 超星凭据写入失败（{type(exc).__name__}）")
        return 9
    log("\n" + "=" * 62)
    log(" 超星（学习通）凭据已生成")
    log("=" * 62)
    log(f"   {cx_creds_mod.describe(payload, path)}")
    log("=" * 62)
    log("\n 下一步：python poc.py --system chaoxing")
    return 0


def finalize(client: ShuSSO, args, username: str = "", **evidence_extra) -> int:
    """换会话并真实验证；失败不写伪成功凭据，不覆盖已有文件。"""
    systems = _requested_systems(args)
    results = login_all_systems(client, username=username, room_type=args.room_type,
                                timeout=args.timeout, verify=not args.insecure,
                                systems=systems)
    print_summary(results)
    save_evidence("login-result.json", client, results, **evidence_extra)
    outcomes: list[bool] = []
    if "there" in systems:
        result = results.get("there") or {}
        if not result.get("logged_in"):
            log("\n  ✗ there 验证失败，未写入凭据；已有凭据保留。")
            outcomes.append(False)
        else:
            try:
                payload = build_credentials(client, result, args, username=username)
            except creds_mod.CredentialsError:
                log("\n  ✗ there 无有效目标 Cookie 或非匿名 profile，未写入凭据。")
                outcomes.append(False)
            else:
                outcomes.append(write_credentials(args, payload) == 0)
    if "chaoxing" in systems:
        result = results.get("chaoxing") or {}
        if not result.get("logged_in") or not isinstance(result.get("credentials"), dict):
            log("\n  ✗ 超星验证失败，未写入凭据；已有凭据保留。")
            outcomes.append(False)
        else:
            outcomes.append(_write_cx_credentials(args, result["credentials"]) == 0)
    return 0 if outcomes and all(outcomes) else 5


# ---------------------------------------------------------------------------
# 入口 ①：账号密码
# ---------------------------------------------------------------------------

def password_flow(args) -> int:
    username = input("学号/工号: ").strip()
    if not username:
        print("错误：学号不能为空")
        return 1
    password = getpass.getpass("密码（输入时不显示）: ")
    if not password:
        print("错误：密码不能为空")
        return 1
    client = ShuSSO(tenant=args.tenant, timeout=args.timeout, verify=not args.insecure)
    login_params = session_params()
    try:
        log("\n[OAuth ②｜用户认证] POST /oauth/userLogin (RSA 加密密码)")
        response = client.login(username, password, login_params)
        if response.get("message") != "success":
            log("  ✗ 认证失败")
            print_error_hint(response.get("message"))
            save_json("login-01-failed.json", {"ok": False, "trace": client.trace})
            return 2
        method = args.method
        if response.get("twoStepRequired"):
            methods = response.get("twoStepMethods") or {}
            if not isinstance(methods, dict) or not methods:
                log("  ✗ 需要两步验证，但未返回可用方式")
                return 3
            available = [item for item in ("wecom", "sms") if item in methods]
            if not method:
                print("\n请选择两步验证方式：")
                print("  [1] 企业微信 (wecom)\n  [2] 手机短信 (sms)")
                method = "sms" if input("输入 1 或 2 [默认 1]: ").strip() == "2" else "wecom"
            if method not in available:
                if not available:
                    log("  ✗ 服务端未提供 sms/wecom 两步验证")
                    return 3
                method = available[0]
                log(f"  → 改用本次可用的两步验证方式：{method}")
            log(f"[OAuth ②｜2FA] POST /oauth/twoStep/send (方式: {method})")
            sent = client.send_2fa_code(method)
            if sent.get("message") != "success":
                log("  ✗ 发码失败")
                save_json("login-02-send-code-failed.json", {"ok": False, "trace": client.trace})
                return 3
            code = input("请输入收到的验证码: ").strip()
            if not code:
                print("错误：验证码不能为空")
                return 3
            log("[OAuth ②｜2FA] POST /oauth/twoStep/verify")
            checked = client.verify_2fa_code({
                "username": username, "password": rsa_encrypt_password(password),
                "tenantId": args.tenant, "params": login_params,
            }, code, method)
            if checked.get("message") != "success":
                log("  ✗ 验证失败")
                print_error_hint(checked.get("message"))
                save_json("login-03-verify-failed.json", {"ok": False, "trace": client.trace})
                return 4
        log("  ✓ 统一身份认证阶段已完成")
        return finalize(client, args, username=username, mode="password", two_factor_method=method)
    finally:
        client.sess.close()


# ---------------------------------------------------------------------------
# 入口 ②：企业微信扫码
# ---------------------------------------------------------------------------

_SCAN_STATUS_TEXT = {
    "QRCODE_SCAN_NEVER": "等待扫码", "QRCODE_SCAN_ING": "已扫码，请在手机上确认",
    "QRCODE_SCAN_SUCC": "已确认，换取会话", "QRCODE_SCAN_ERR": "二维码已过期",
    "QRCODE_SCAN_OVERDUE": "二维码已过期", "QRCODE_SCAN_CANCEL": "已取消扫码",
}


def wecom_scan_flow(args) -> int:
    client = ShuSSO(tenant=args.tenant, timeout=args.timeout, verify=not args.insecure)
    state = session_params()
    try:
        log("\n[企微扫码] 请求 qrConnect，生成本次二维码 ...")
        info = client.wecom_qrcode_info(state=state)
        if not info.get("key"):
            log("  ✗ 未取得扫码 key")
            save_json("login-00-wecom-scan-failed.json", {"ok": False, "trace": client.trace})
            return 6
        line = "─" * 62
        print("\n" + line)
        printed = print_wecom_qr(info["confirm_url"], args)
        print(" 请用企业微信扫描二维码，并在手机上点「确认登录」")
        # 即时扫码入口是一次性的；仅交互终端允许显示，禁止落入重定向日志。
        if sys.stdout.isatty():
            if not printed:
                print(f" 二维码图片（仅本次扫码）：{info['qr_img_url']}")
            print(f" 确认页（仅本次扫码）：{info['confirm_url']}")
        else:
            log("  输出不是交互终端，扫码链接已隐藏；请在终端运行此命令。")
            return 6
        print(line)
        log(f" 等待确认（最多 {args.scan_timeout} 秒，Ctrl+C 可中断）...")
        waited = client.wecom_wait_scan(
            info["key"], state=state, timeout=args.scan_timeout,
            poll_log=lambda status, _code: log(f"     {_SCAN_STATUS_TEXT.get(status, '扫码状态变化')}"))
        if not waited.get("ok") or not waited.get("auth_code"):
            log("  ✗ 扫码取消、过期或未确认")
            save_json("login-00-wecom-scan-failed.json", {"ok": False, "trace": client.trace})
            return 7
        log("  ✓ 已确认，换取 SSO 会话 ...")
        redeemed = client.wecom_redeem(waited["auth_code"], state)
        # 上游的 ok 仅是粗略错误筛查；同时要求跳转，最终仍由 there profile 判断。
        if not redeemed.get("ok") or redeemed.get("http_status") not in (301, 302, 303, 307, 308):
            log("  ✗ 扫码回调失败")
            save_json("login-00-wecom-redeem-failed.json", {"ok": False, "trace": client.trace})
            return 8
        return finalize(client, args, mode="wecom_scan")
    finally:
        client.sess.close()


# ---------------------------------------------------------------------------
# 入口 ③：手工 Cookie / 复探
# ---------------------------------------------------------------------------

def cookie_flow(args) -> int:
    try:
        session = creds_mod.manual_session(args.cookie or "")
    except creds_mod.CredentialsError as exc:
        log(f"  ✗ {exc}")
        return 1
    try:
        log("\n[手工 Cookie] 仅向 there 移动入口和 profile 发只读验证请求 ...")
        probe = probe_profile(session, args)
        _print_probe(probe)
        if not probe.get("ok"):
            return 6
        payload = creds_mod.build(session, args.room_type, probe["profile"])
        payload["source"] = "manual-cookie"
        return write_credentials(args, payload)
    finally:
        session.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="上海大学统一身份认证 → 四系统座位预约凭据")
    parser.add_argument("--tenant", default=config.DEFAULT_TENANT,
                        help=f"院校（默认 {config.DEFAULT_TENANT}）")
    parser.add_argument("--login", choices=["password", "wecom_scan"], help="省略则交互选择")
    parser.add_argument("--method", choices=["wecom", "sms"], help="密码登录的可选 2FA 方式")
    parser.add_argument("--scan-timeout", type=int, default=180, help="扫码等待秒数（默认 180）")
    parser.add_argument("--no-qr", action="store_true", help="不在终端渲染二维码")
    parser.add_argument("--qr-style", choices=["block", "ascii"], default="block", help="终端二维码样式")
    parser.add_argument("--system", choices=["there", "chaoxing", "both"], default="both",
                        help="登录目标系统（默认 both：一次认证，同时换两套会话）")
    parser.add_argument("--cookie", default=None, help="there Cookie 请求头；或 SHU_SEAT_COOKIE")
    parser.add_argument("--out", default=None, help="there 凭据路径；或 SHU_SEAT_CREDENTIALS")
    parser.add_argument("--out-chaoxing", default=None,
                        help="超星凭据路径；或 SHU_CHAOXING_CREDENTIALS（默认 .credentials.chaoxing.json）")
    parser.add_argument("--check", action="store_true", help="只读验证已有 Cookie，不覆盖凭据")
    parser.add_argument("--room-type", choices=list(creds_mod.MOBILE_PATHS), default="LIB_SEAT",
                        help="本次验证的移动入口（默认 LIB_SEAT）")
    parser.add_argument("--base", default=config.THERE_BASE, help="目标站根地址（固定 there 原站）")
    parser.add_argument("--timeout", type=float, default=30.0, help="单次请求超时秒数（默认 30）")
    parser.add_argument("--insecure", action="store_true", help="显式关闭 TLS 校验（默认开启）")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0 or args.scan_timeout <= 0:
        print("错误：timeout / scan-timeout 必须为正数")
        return 1
    if args.base.rstrip("/") != config.THERE_BASE:
        print("错误：此登录 POC 固定使用 https://there.shu.edu.cn，拒绝将认证发往其它站点")
        return 1
    args.base = config.THERE_BASE
    args.cookie = args.cookie if args.cookie is not None else os.getenv("SHU_SEAT_COOKIE")
    banner()
    if args.cookie and args.system != "there":
        print("错误：手工 Cookie 仅支持 there；超星请用 --system chaoxing/both 走 newsso 换会话")
        return 1
    try:
        if args.check:
            return check_flow(args)
        if args.cookie:
            return cookie_flow(args)
        mode = choose_login_mode(args)
        return wecom_scan_flow(args) if mode == "wecom_scan" else password_flow(args)
    except Exception as exc:
        # requests 异常可包含 password/code/session URL，异常类型足以诊断离线问题。
        log(f"\n  ✗ 流程中止（{type(exc).__name__}），未写入新的凭据。")
        return 9


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n已取消")
        sys.exit(130)
