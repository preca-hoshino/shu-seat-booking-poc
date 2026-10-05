"""there / chaoxing 两条换会话：there 走本地收紧流程，超星调 vendor 子模块实现。

there：预置会话 → OAuth code → 回调 → HTML/profile 双重验证。
超星：`chaoxing_redeem`（authorize → 5read → login6 → 座位首页 userLoginInfo）。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

from seat.there.config import LOCAL_TZ

from . import config
from .client import ShuSSO
from .system_api import RedeemContext, fail
from .utils import b64_params, log, save_json

_REDIRECT_STATUSES = {301, 302, 303, 307, 308}
_SSO_HOSTS = {"newsso.shu.edu.cn", "oauth.shu.edu.cn"}


def total_systems() -> int:
    return len(config.SYSTEMS)


def session_params(system: dict | None = None) -> str:
    """与原项目相同的 newsso paramsBase64；SYSTEMS 固定只有 there。"""
    cfg = system or config.SYSTEMS["there"]
    return b64_params({
        "responseType": "code", "clientId": cfg["client_id"],
        "clientName": cfg["name"], "scope": cfg["scope"],
        "redirectUri": cfg["redirect_uri"], "state": "",
    })


def _origin_url(url: str, hostname: str) -> bool:
    parsed = urlparse(url)
    return (parsed.scheme == "https" and parsed.hostname == hostname
            and parsed.port in (None, 443) and not parsed.username and not parsed.password)


def _there_headers() -> dict:
    return {"Origin": config.THERE_BASE, "Referer": config.THERE_BASE + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}


def _valid_callback(location: str, expected_state: str = "") -> bool:
    if not _origin_url(location, "there.shu.edu.cn"):
        return False
    parsed = urlparse(location)
    if parsed.path != "/login-oauth2" or parsed.fragment:
        return False
    query = parse_qs(parsed.query, keep_blank_values=True)
    codes = query.get("code", [])
    if len(codes) != 1 or not codes[0].strip():
        return False
    # 项目文档中的成功回调可能不带 state；带 state 时校验，绝不盲目忽略不一致。
    returned_state = query.get("state")
    if returned_state is not None:
        if len(returned_state) != 1 or (expected_state and returned_state[0] != expected_state):
            return False
    return True


def _prewarm(client: ShuSSO, cfg: dict) -> str:
    """只取 /login 的 302 state 和目标 Cookie，不跟随其 SSO 重定向。"""
    response = client.sess.get(cfg["needs_state_bootstrap"], headers=_there_headers(),
                               allow_redirects=False, timeout=client.timeout)
    client.record("bootstrap/there", {"http_status": response.status_code})
    location = response.headers.get("Location", "")
    parsed = urlparse(location)
    if (response.status_code in _REDIRECT_STATUSES and parsed.hostname in _SSO_HOSTS
            and parsed.scheme == "https" and parsed.path == "/oauth/authorize"
            and not parsed.username and not parsed.password):
        return parse_qs(parsed.query).get("state", [""])[0]
    return ""


def _callback(client: ShuSSO, location: str) -> dict:
    """严格控制回调跳转域/路径；HTTP 200 空正文不是登录成功。"""
    response = client.sess.get(location, headers=_there_headers(),
                               allow_redirects=False, timeout=client.timeout)
    client.record("callback/there", {"http_status": response.status_code})
    if response.status_code not in _REDIRECT_STATUSES:
        return fail("callback_not_redirected", http_status=response.status_code)
    current = location
    for _ in range(8):
        next_url = urljoin(current, response.headers.get("Location", ""))
        parsed = urlparse(next_url)
        if (not response.headers.get("Location")
                or not _origin_url(next_url, "there.shu.edu.cn")
                or not (parsed.path == "/web" or parsed.path.startswith("/web/"))):
            return fail("unsafe_callback_redirect", http_status=response.status_code)
        current = next_url
        response = client.sess.get(current, headers=_there_headers(),
                                   allow_redirects=False, timeout=client.timeout)
        client.record("landing/there", {"http_status": response.status_code})
        if response.status_code in _REDIRECT_STATUSES:
            continue
        if response.status_code != 200 or not (response.text or "").strip():
            return fail("empty_or_failed_landing", http_status=response.status_code)
        # URL/HTTP 在此仅是流程条件；真正的成功条件在 bootstrap + profile。
        return {"logged_in": False, "reason": "awaiting_profile_verification",
                "http_status": response.status_code,
                "final_url": config.THERE_BASE + parsed.path}
    return fail("too_many_callback_redirects", http_status=response.status_code)


def login_one(ctx: RedeemContext, room_type: str = "LIB_SEAT",
              verify: bool = True) -> dict:
    """上游 RedeemContext 接口；只允许固定 there 配置，返回原始 profile 供私有凭据。"""
    from seat.there.client import SeatClient
    from seat.there.credentials import build

    client, cfg = ctx.client, ctx.cfg
    if ctx.key != "there" or cfg.get("redirect_uri") != config.THERE_BASE + "/login-oauth2":
        return fail("unsupported_system")
    log("     [OAuth ①] 预置 there 会话 ...")
    state = _prewarm(client, cfg)
    auth = client.authorize(cfg["client_id"], cfg["redirect_uri"], cfg.get("scope", ""), state)
    if auth.get("needs_login"):
        return fail("session_not_reused", http_status=auth.get("http_status"))
    if auth.get("http_status") not in _REDIRECT_STATUSES:
        return fail("no_redirect", http_status=auth.get("http_status"))
    location = auth.get("location") or ""
    if not _valid_callback(location, state):
        return fail("invalid_callback", http_status=auth.get("http_status"))
    log("     [OAuth ③④] 已取得授权回调，换取 there 会话 ...")
    result = _callback(client, location)
    if result.get("reason") != "awaiting_profile_verification":
        return result
    log(f"     [验证] {room_type} 移动入口 + profile ...")
    seat = SeatClient(session=client.sess, room_type=room_type,
                      base=config.THERE_BASE, timeout=client.timeout, verify=verify)
    bootstrap = seat.bootstrap()
    if not isinstance(bootstrap, dict) or not str(bootstrap.get("sessionId") or "").strip():
        return fail("invalid_bootstrap")
    profile = seat.profile()
    # 共用凭据的严格非匿名条件，避免另一套判定把坏会话误标为成功。
    build(client.sess, room_type, profile, username=ctx.username)
    result.update({"logged_in": True, "reason": "verified_profile",
                   "room_type": room_type, "profile": profile})
    client.record("verify/there", {"logged_in": True, "system": "there"})
    return result


def chaoxing_redeem(client: ShuSSO, username: str = "") -> dict:
    """超星换会话：调 vendor 子模块的实现，再组装座位侧凭据。

    `systems/chaoxing.com/client.py` 在上游维护换会话链（authorize → 5read →
    login6 → 座位首页校验），此处只做两件座位侧适配：

    ① 以 `RedeemContext` 调 vendor 的 `redeem(ctx)`（同一 SSO 会话，Cookie 回写共享 Jar）；
    ② 成功后把共享会话里的 chaoxing.com Cookie 交给 `seat.chaoxing.credentials`
       组装成私有载荷，供 login.py 立即取出写盘（credentials 不进证据）。
    """
    from src.registry import redeem_impl
    from src.system_api import RedeemContext as VendorRedeemContext

    impl = redeem_impl("chaoxing")
    if impl is None:                 # 子模块版本过旧（sso/config.py 已做装载期检查）
        return fail("unsupported_system")
    result = impl(VendorRedeemContext(client=client, key="chaoxing",
                                      cfg=config.CHAOXING, username=username))
    if not result.get("logged_in"):
        return result

    from seat.chaoxing.credentials import CredentialsError, build

    user = {"uid": result.get("user_id"), "uname": result.get("real_name"),
            "sno": result.get("username")}
    try:
        credentials = build(client.sess, user, username=username, login="newsso/5read")
    except CredentialsError:
        return fail("no_session_cookies")
    result.update({"user": user, "cookie_count": len(credentials["cookies"]),
                   "credentials": credentials})
    return result


def login_all_systems(client: ShuSSO, username: str = "", room_type: str = "LIB_SEAT",
                      timeout: float | None = None, verify: bool = True,
                      systems: tuple[str, ...] = ("there",)) -> dict[str, dict]:
    """按 systems 依次登录：there（OAuth 回调 + 移动入口验证）与超星（5read/login6 换会话）。

    两个系统共享同一 newsso 认证会话（SHU_OAUTH2），但换会话与落地域彼此独立；
    任一系统失败只记为该系统失败，不影响另一个。默认仍是只登录 there，
    由 login.py 的 --system 决定实际范围。
    """
    if timeout is not None:
        client.timeout = timeout
    results: dict[str, dict] = {}
    if "there" in systems:
        log("\n[OAuth ①③④] 用 SSO 会话登录空间预约系统（there） ...\n")
        ctx = RedeemContext(client=client, key="there", cfg=config.SYSTEMS["there"],
                            username=username)
        try:
            results["there"] = login_one(ctx, room_type=room_type, verify=verify)
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            # 网络异常往往自带完整 URL；不打印/保存原始 exception 文本。
            results["there"] = fail("exception", error_type=type(exc).__name__)
    if "chaoxing" in systems:
        log("\n[换会话] 用 SSO 会话登录超星（学习通）图书馆座位 ...\n")
        try:
            results["chaoxing"] = chaoxing_redeem(client, username=username)
            if results["chaoxing"].get("logged_in"):
                log("     ✓ 已取得 office 会话（凭据在写入阶段保存）")
            else:
                log(f"     ✗ 失败（{results['chaoxing'].get('reason')}）")
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            results["chaoxing"] = {"logged_in": False, "reason": "exception",
                                   "error_type": type(exc).__name__, "final_url": ""}
    return results


def save_evidence(name: str, client: ShuSSO, results: dict[str, dict], **fields) -> Path:
    """证据只保存流程摘要；private profile / callback authJump 不保存。"""
    evidence = {
        "timestamp": datetime.now(LOCAL_TZ).isoformat(),
        "protocol": "OAuth 2.0 Authorization Code",
        "summary": {key: {field: value for field, value in result.items()
                           if field in {"logged_in", "reason", "http_status", "room_type",
                                        "error_type", "final_url"}}
                    for key, result in results.items()},
        "trace": client.trace, **fields,
    }
    return save_json(name, evidence)
