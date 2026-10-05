"""`sso/`：git 子模块 shu-sso-poc 的薄适配层，vendor 原版不修改。

qr / registry / rsa_key / system_api 复用上游单份实现；本地负责 there 换会话、
目标 Cookie 导出与更严的脱敏。公钥抓取只调整传输策略：默认校验证书、禁止跨域跳转。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

VENDOR_DIR = Path(os.getenv("SHU_SSO_POC_DIR") or
                  Path(__file__).resolve().parent.parent / "vendor" / "shu-sso-poc")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if not (VENDOR_DIR / "src" / "client.py").is_file():
    raise RuntimeError(
        f"找不到上游子模块：{VENDOR_DIR}\n"
        "  请执行 git submodule update --init --recursive\n"
        "  或用 SHU_SSO_POC_DIR 指定固定版本的 shu-sso-poc"
    )
if str(VENDOR_DIR) not in sys.path:
    # 上游也有 poc.py / login.py；保留本项目入口的导入优先级。
    project_index = sys.path.index(str(PROJECT_ROOT)) if str(PROJECT_ROOT) in sys.path else -1
    sys.path.insert(project_index + 1, str(VENDOR_DIR))

from src import qr as _qr                         # noqa: E402
from src import registry as _registry             # noqa: E402
from src import rsa_key as _rsa_key               # noqa: E402
from src import system_api as _system_api         # noqa: E402

_rsa_key.CACHE_PATH = PROJECT_ROOT / ".rsa_public_key.pem"
sys.modules["src.config"].CAPTURE_DIR = PROJECT_ROOT / "captures"


def _verified_rsa_text(url, session, timeout):
    """复用上游抓取/解析流程，显式覆盖其 Session.verify=False。"""
    parsed = urlparse(url)
    if (parsed.scheme != "https" or parsed.hostname != "newsso.shu.edu.cn"
            or parsed.port not in (None, 443) or parsed.username or parsed.password):
        return ""
    try:
        response = session.get(url, timeout=timeout,
                               verify=getattr(_rsa_key, "SEAT_TLS_VERIFY", True),
                               allow_redirects=False)
        return response.text or "" if 200 <= response.status_code < 300 else ""
    except Exception:
        return ""


_rsa_key._fetch_text = _verified_rsa_text
_rsa_key.SEAT_TLS_VERIFY = True
sys.modules[__name__ + ".qr"] = _qr
sys.modules[__name__ + ".registry"] = _registry
sys.modules[__name__ + ".rsa_key"] = _rsa_key
sys.modules[__name__ + ".system_api"] = _system_api
qr, registry, rsa_key, system_api = _qr, _registry, _rsa_key, _system_api
__all__ = ["config", "registry", "rsa_key", "utils", "client", "system_api",
           "runner", "ui", "qr"]
