"""submit 防伪签名（enc）与 select 页盐解析。

2026-10-05 通过浏览器动态分析（requirejs 加载模块 + hook `hex_md5` 捕获明文）
复现，并做了服务端 A/B 对照：

- 正确签名 → 服务端进入业务校验（如"该时间段已过，不可预约！"）；
- 改动一位的错误签名 → "您在页面停留过久，本次操作安全验证已超时(代码:303)"。

算法：8 个提交字段按键名字母序拼 ``[k=v]``，末尾拼 select 页下发的盐
``[<salt>]``，整体取小写 MD5：

    enc = md5("[captcha=][day=…][deptIdEnc=…][endTime=…][roomId=…]"
              "[seatNum=…][startTime=…][wyToken=…][<32hex>_<uid>]")

- 8 个字段固定全含，空值也必须保留；
- 盐来自 select 页隐藏域 ``<input type="hidden" id="submit_enc" value="…">``，
  每次载入页面服务端重新下发（实测两次不同），提交前必须重新拉取。
"""

from __future__ import annotations

import hashlib
import re

# 参与签名的字段（与 seat_select_third.js 的 paramObj 一一对应，勿增删）。
SUBMIT_FIELDS = ("captcha", "day", "deptIdEnc", "endTime",
                 "roomId", "seatNum", "startTime", "wyToken")

_SALT_RE = re.compile(r'id="submit_enc"\s+value="([^"]+)"', re.I)


class SignatureError(ValueError):
    """签名输入不满足实测契约（缺字段、多余字段或盐为空）。"""


def build_plain(params: dict, salt: str) -> str:
    """返回参与 MD5 的原文；单独暴露以便测试与诊断（不含敏感值）。"""
    missing = [name for name in SUBMIT_FIELDS if name not in params]
    if missing:
        raise SignatureError(f"签名缺少字段：{', '.join(missing)}")
    extra = [name for name in params if name not in SUBMIT_FIELDS]
    if extra:
        raise SignatureError(f"签名包含未实测字段：{', '.join(sorted(extra))}")
    if not isinstance(salt, str) or not salt.strip():
        raise SignatureError("盐不能为空；提交前需重新拉取 select 页")
    body = "".join(f"[{name}={params[name]}]" for name in sorted(params))
    return f"{body}[{salt.strip()}]"


def build_enc(params: dict, salt: str) -> str:
    """按实测算法计算 enc（32 位小写 hex）。"""
    return hashlib.md5(build_plain(params, salt).encode("utf-8")).hexdigest()


def parse_salt(html: str) -> str:
    """从 select 页 HTML 解析盐；未找到或为空时抛 ValueError。"""
    match = _SALT_RE.search(html or "")
    if not match or not match.group(1).strip():
        raise ValueError("select 页未包含 submit_enc 盐（页面被替换或契约变化）")
    return match.group(1).strip()


__all__ = ["SUBMIT_FIELDS", "SignatureError", "build_plain", "build_enc", "parse_salt"]
