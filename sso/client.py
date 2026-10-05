"""ShuSSO 本地子类：认证/2FA/扫码仍用上游，trace 只记录非敏感摘要。"""

from __future__ import annotations

from datetime import datetime

from seat.there.config import LOCAL_TZ
from src.client import ShuSSO as _UpstreamShuSSO
from . import config, rsa_key

_TRACE_FIELDS = {"http_status", "status", "ok", "needs_login", "reason",
                 "logged_in", "system", "method", "cookie_count"}


class ShuSSO(_UpstreamShuSSO):
    """默认验证 TLS；SSO Cookie 保留在内存，不按 Cookie 名字扁平导出。"""

    def __init__(self, tenant: str = config.DEFAULT_TENANT,
                 timeout: float = 30.0, verify: bool = True):
        super().__init__(tenant=tenant, timeout=timeout)
        self.sess.verify = verify
        rsa_key.SEAT_TLS_VERIFY = verify

    def record(self, step: str, detail: dict) -> None:
        # 上游 authorize/redeem/qr 会返回敏感正文，保存之前仅取白名单。
        from .utils import redact
        safe = {k: v for k, v in detail.items() if k in _TRACE_FIELDS}
        self.trace.append({"step": step, "time": datetime.now(LOCAL_TZ).isoformat(),
                           **redact(safe)})

    def cookies(self, domain_contains: str | None = None) -> list[dict]:
        """用于兼容查询，输出完整记录；最终落盘请用 seat.there.credentials.build。"""
        from seat.there.credentials import _cookie_record
        return [_cookie_record(c) for c in self.sess.cookies
                if not domain_contains or (c.domain or "").lstrip(".") == domain_contains]


__all__ = ["ShuSSO"]
