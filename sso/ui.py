"""沿用原 POC 的终端横幅、菜单、二维码与结果汇总风格。"""

from __future__ import annotations

import sys

from . import config
from .qr import render_qr_terminal
from .utils import log

REASON_TEXT = {
    "session_not_reused": "SSO 会话未复用，需重新登录",
    "no_redirect": "SSO 未返回授权重定向",
    "invalid_callback": "授权回调域、路径、code 或 state 无效",
    "callback_not_redirected": "回调未产生预期跳转（含 HTTP 200 空正文失败）",
    "unsafe_callback_redirect": "回调跳转目标不在本站允许路径",
    "empty_or_failed_landing": "回调落地页为空或 HTTP 失败",
    "too_many_callback_redirects": "回调跳转次数超过限制",
    "invalid_bootstrap": "移动入口未取得 sessionId",
    "exception": "请求或非匿名用户验证失败",
}
ERROR_HINTS = {
    "badPassword": "密码错误", "userNotFound": "用户不存在",
    "userLocked": "账号已锁定", "userNotAllowed": "账号不允许登录",
    "invalidCode": "验证码错误或已过期", "ipLimitExceeded": "请求过于频繁",
    "wecomAuthFailed": "企业微信认证失败", "internalServerError": "服务端内部错误",
}


def banner() -> None:
    print("=" * 62)
    print(" 上海大学统一身份认证 · 四系统座位预约凭据获取")
    print(" 协议: OAuth 2.0 授权码模式，非 OIDC")
    print()
    print(" ① 预置 there 会话 / 构造 newsso 授权参数")
    print(" ② 密码 + 可选 2FA，或企业微信扫码")
    print(" ③ GET /oauth/authorize 获取授权回调")
    print(" ④ /login-oauth2 换会话 → 移动入口 + profile 验证")
    print("=" * 62)
    print(f" 目标业务系统: {config.SYSTEMS['there']['name']}")
    print("=" * 62)


def choose_login_mode(args) -> str:
    if args.login:
        return args.login
    print("\n请选择登录方式：")
    print("  [1] 账号密码登录（学号/工号 + 密码 + 可选两步验证）")
    print("  [2] 企业微信扫码登录")
    choice = input("输入 1 或 2 [默认 1]: ").strip() or "1"
    return "wecom_scan" if choice == "2" else "password"


def print_summary(results: dict[str, dict]) -> int:
    log("=" * 62)
    log(" 验证结果汇总")
    log("=" * 62)
    count = 0
    for key, cfg in config.SYSTEMS.items():
        result = results.get(key) or {}
        if result.get("logged_in"):
            count += 1
            detail = f"{result.get('room_type')} 移动入口及非匿名 profile 已验证"
            log(f"  ✓ 成功  {cfg['name']}  {detail}")
        else:
            reason = result.get("reason") or "unknown"
            log(f"  ✗ 失败  {cfg['name']}  {REASON_TEXT.get(reason, reason)}")
    log("=" * 62)
    log(f"  合计：{count}/{len(config.SYSTEMS)} 个系统登录成功")
    return count


def print_error_hint(message: str | None) -> None:
    if message in ERROR_HINTS:
        print(f"  提示：{ERROR_HINTS[message]}")


def print_wecom_qr(confirm_url: str, args) -> bool:
    if getattr(args, "no_qr", False):
        log("     （已按 --no-qr 关闭终端二维码）")
        return False
    if not sys.stdout.isatty():
        log("     （输出不是终端，跳过二维码渲染）")
        return False
    if render_qr_terminal(confirm_url, getattr(args, "qr_style", "block") or "block"):
        return True
    log("     （未安装 qrcode，无法渲染终端二维码）")
    return False
