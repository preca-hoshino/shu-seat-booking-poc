#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""主脚本：读凭据 → 查四类资源 → 创建/查看/取消/提前结束预约。

无子命令时只读四入口用户与最近预约。book/cancel/finish 是显式业务操作；
book --dry-run 只查询并显示完整请求体。check-in 仅有脚本证据，需 --experimental。
退出码：0 正常；2 参数无效；6 上游/业务失败；9 凭据不可用；130 用户中断。
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import sys

from seat import config, credentials as creds_mod, ui
from seat.client import BusinessError, SeatClient, SeatError


# ---------------------------------------------------------------------------
# 凭据与输出
# ---------------------------------------------------------------------------

def make_client(creds: dict, args, session=None, room_type: str | None = None) -> SeatClient:
    return SeatClient(session=session or creds_mod.restore_session(creds),
                      room_type=room_type or args.room_type or creds.get("room_type") or config.DEFAULT_ROOM_TYPE,
                      base=args.base or (creds.get("there") or {}).get("base") or config.THERE_BASE,
                      timeout=args.timeout, verify=not args.insecure)


def _display(result: dict, args, command: str) -> None:
    printable = ui.safe_output(result, profile=command == "profile")
    if args.json:
        print(json.dumps(printable, ensure_ascii=False, indent=2))
    else:
        print(ui.render(printable, command))
    if args.capture:
        # 诊断证据经二次严格脱敏；原 Cookie/HTML/profile 不进入 captures。
        from sso.utils import save_json
        path = save_json(f"poc-{command}.json", {"operation": command,
                         "room_type": args.room_type or config.DEFAULT_ROOM_TYPE,
                         "response": printable})
        print(f"证据已保存：{path}", file=sys.stderr if args.json else sys.stdout)


# ---------------------------------------------------------------------------
# 九个实测 API 的 CLI 编排
# ---------------------------------------------------------------------------

def run_overview(creds: dict, args) -> dict:
    """默认只读四入口，各自重新取页面 sessionId；不跨入口搬用令牌。"""
    session = creds_mod.restore_session(creds)
    rows = []
    try:
        for room_type, system in config.SYSTEMS.items():
            client = make_client(creds, args, session=session, room_type=room_type)
            try:
                profile = client.profile()["data"]
                bookings = client.recent().get("data") or []
                rows.append({"room_type": room_type, "name": system["name"], "available": True,
                             "isAnonymous": profile.get("isAnonymous"), "disableBooking": profile.get("disableBooking"),
                             "recent_count": len(bookings)})
            except (SeatError, ValueError) as exc:
                rows.append({"room_type": room_type, "name": system["name"], "available": False, "error": str(exc)})
    finally:
        session.close()
    return {"systems": rows, "read_only": True}


def run_command(client: SeatClient, args) -> dict:
    command = args.command
    if command == "profile":
        return client.profile()
    if command == "recent":
        return client.recent()
    if command == "overview":
        return client.overview(args.day)
    if command == "areas":
        return client.areas(args.begin, args.end)
    if command == "rooms":
        return client.area(args.area, args.begin, args.end)
    if command == "detail":
        return client.detail(args.booking_id, show_checks=args.show_checks)
    if command == "book":
        payload = client.prepare_booking(args.area, args.room, args.begin, args.end)
        if args.dry_run:
            return {"dry_run": True, "submitted": False, "request": payload}
        result = client.submit(payload)
        booking_id = result["data"][0]["id"]
        output = {"created": result, "booking_id": booking_id}
        # 已创建后只刷新，不因刷新失败再次创建。
        refresh = (("recent", client.recent), ("area", lambda: client.area(args.area, args.begin, args.end)),
                   ("overview", lambda: client.overview(args.begin[:10])),
                   ("detail", lambda: client.detail(booking_id)))
        for name, fetch in refresh:
            try:
                output[name] = fetch()
            except SeatError as exc:
                output.setdefault("refresh_errors", {})[name] = str(exc)
        return output
    if command in ("cancel", "finish"):
        result = client.cancel(args.booking_id) if command == "cancel" else client.finish(args.booking_id)
        output = {"operation": command, "response": result, "booking_id": args.booking_id}
        try:
            output["recent"] = client.recent()
        except SeatError as exc:
            output["refresh_error"] = str(exc)
        return output
    if command == "check-in":
        return client.check_in(args.booking_id, experimental=args.experimental)
    raise ValueError(f"未知操作：{command}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _common(parser, *, sparse: bool = False) -> None:
    def default(value):
        return argparse.SUPPRESS if sparse else value
    parser.add_argument("--credentials", default=default(None),
                        help="凭据文件（默认 .credentials.json，可用 SHU_SEAT_CREDENTIALS）")
    parser.add_argument("--room-type", choices=list(config.SYSTEMS), default=default(None),
                        help="四种捕获类型（默认取凭据中的 room_type）")
    parser.add_argument("--base", default=default(None), help="业务站点根地址（默认 there.shu.edu.cn）")
    parser.add_argument("--timeout", type=float, default=default(30.0), help="请求超时秒数（默认 30）")
    parser.add_argument("--insecure", action="store_true", default=default(False), help="显式跳过业务 TLS 校验")
    parser.add_argument("--json", action="store_true", default=default(False), help="JSON 输出，屏蔽个人及会话字段")
    parser.add_argument("--capture", action="store_true", default=default(False), help="将脱敏诊断写入 captures/")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="上海大学 there 四入口预约 POC（默认只读概览）")
    _common(p)
    sub = p.add_subparsers(dest="command")
    commands = {
        "profile": "查询当前用户", "recent": "查询最近预约", "overview": "查询日期概览",
        "areas": "查询区域树", "rooms": "查询区域座位与规则", "detail": "查询预约详情",
        "book": "创建一座位单时段预约", "cancel": "取消预约", "finish": "提前结束预约",
        "check-in": "图书馆脚本引用的签到（未验证）",
    }
    for name, help_text in commands.items():
        child = sub.add_parser(name, help=help_text, description=help_text)
        _common(child, sparse=True)
        if name == "overview":
            child.add_argument("--day", required=True, help="YYYY-MM-DD")
        if name in ("areas", "rooms", "book"):
            child.add_argument("--begin", required=True, help="日期；book 必须为 YYYY-MM-DD HH:mm")
            child.add_argument("--end", required=True, help="日期；book 必须为 YYYY-MM-DD HH:mm")
        if name in ("rooms", "book"):
            child.add_argument("--area", required=True, help="区域列表返回的 areaId")
        if name == "book":
            child.add_argument("--room", required=True, help="区域详情返回的 roomId")
            child.add_argument("--dry-run", action="store_true", help="查询并组装完整请求体，不提交")
        if name in ("detail", "cancel", "finish", "check-in"):
            child.add_argument("booking_id", help="创建响应或 recent 返回的 bookingId")
        if name == "detail":
            child.add_argument("--show-checks", action=argparse.BooleanOptionalAction, default=None,
                               help="showChecks=true（默认图书馆/24H携带，其余省略）")
        if name == "check-in":
            child.add_argument("--experimental", action="store_true", help="显式执行仅脚本引用、响应未知的签到")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        creds = creds_mod.load(args.credentials)
    except creds_mod.CredentialsError as exc:
        print(f"凭据不可用：{exc}", file=sys.stderr)
        return 9
    if not args.json:
        chosen = args.room_type or creds.get("room_type") or config.DEFAULT_ROOM_TYPE
        print(ui.banner(chosen, creds.get("_path") or str(creds_mod.DEFAULT_PATH)))
    if not args.command:
        try:
            result = run_overview(creds, args)
            _display(result, args, "systems")
            return 0 if all(r["available"] for r in result["systems"]) else 6
        except ValueError as exc:
            print(f"参数无效：{exc}", file=sys.stderr)
            return 2
    client = None
    try:
        client = make_client(creds, args)
        args.room_type = client.room_type
        result = run_command(client, args)
        _display(result, args, args.command)
        return 0
    except BusinessError as exc:
        output = {"error": {"message": str(exc), "business_code": exc.code}}
        if args.command == "book" and client is not None:
            try:
                output["recent"] = client.recent()
            except SeatError:
                output["recent_check"] = "失败；请自行查询核对，不要立即重复提交"
        _display(output, args, args.command)
        return 6
    except SeatError as exc:
        _display({"error": {"message": str(exc), "http_status": exc.http_status}}, args, args.command)
        return 6
    except ValueError as exc:
        print(f"参数或当前资源状态无效：{exc}", file=sys.stderr)
        return 2
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n已停止")
        sys.exit(130)
