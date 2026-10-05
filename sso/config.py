"""协议参数透传上游，SYSTEMS 仅保留空间预约 there，导入不联网。"""

from pathlib import Path

from src.config import DEFAULT_TENANT, SSO_BASE, WECOM  # noqa: F401
from src.registry import load_systems

THERE_BASE = "https://there.shu.edu.cn"
CAPTURE_DIR = Path(__file__).resolve().parent.parent / "captures"
_loaded = load_systems()
if "there" not in _loaded:
    raise RuntimeError("上游缺少 there 配置，请初始化固定版本的 shu-sso-poc 子模块")
SYSTEMS = {"there": _loaded["there"]}
