"""协议参数透传上游：SYSTEMS 仅保留空间预约 there；超星 SYSTEM 见 CHAOXING。导入不联网。"""

from pathlib import Path

from src.config import DEFAULT_TENANT, SSO_BASE, WECOM  # noqa: F401
from src.registry import load_systems

THERE_BASE = "https://there.shu.edu.cn"
CAPTURE_DIR = Path(__file__).resolve().parent.parent / "captures"
_loaded = load_systems()
for _key in ("there", "chaoxing"):
    if _key not in _loaded:
        raise RuntimeError(
            f"上游缺少 {_key} 配置，请把 shu-sso-poc 子模块更新到含超星系统的版本")
SYSTEMS = {"there": _loaded["there"]}

# 超星（学习通）图书馆座位：SYSTEM 由 vendor 子模块提供
# （systems/chaoxing.com/，换会话实现为同目录 client.py，sso/runner.py 调用）。
CHAOXING = _loaded["chaoxing"]
