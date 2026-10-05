#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""端到端离线自检：四入口的预约闭环与真实 PreparedRequest。

运行: python tests/test_e2e_mock.py
使用合成夹具拦截所有网络请求，绝不访问目标服务。
"""

from __future__ import annotations

import copy
import unittest
from urllib.parse import parse_qs, urlsplit

from test_offline import (  # noqa: E402
    END, PAGES, PROFILE, ROOM, START, OfflineCase, area_envelope,
)


class BookingFlowTests(OfflineCase):
    def test_four_types_reserve_detail_and_user_selected_terminal_action(self):
        for room_type in PAGES:
            with self.subTest(room_type=room_type):
                client = self.client(room_type)
                booking_id = "fixture-booking-" + room_type
                self.wire.add("GET", "/api/v3/my/profile", PROFILE)
                self.wire.add("GET", "/api/v3/my/bookings/recent", {"code": 0, "data": []})
                self.wire.add("GET", "/api/v3/booking-status/overview", {"code": 0, "data": {"dates": ["2030-06-01"]}})
                self.wire.add("GET", "/api/v3/booking-status/areas", {"code": 0, "data": [{"id": "fixture-area", "name": "测试区域"}]})
                self.wire.add("GET", "/api/v3/booking-status/areas/fixture-area", area_envelope())
                profile = client.profile()
                self.assertEqual(client.recent()["data"], [])
                client.overview("2030-06-01")
                client.areas("2030-06-01", "2030-06-01")
                room = client.area("fixture-area", START, END)["data"]["rooms"][0]
                self.wire.add("GET", "/api/v3/booking-status/areas/fixture-area", area_envelope())
                created = {"code": 0, "data": [{"id": booking_id, "beginAt": START, "endAt": END}]}
                self.wire.add("POST", "/api/v3/bookings", created)
                self.assertEqual(client.create(room, START, END, profile=profile), created)
                finish = room_type == "STATION"
                expected_abilities = ["close"] if finish else ["cancel", "waitOpen"]
                detail = {"code": 0, "data": {"id": booking_id, "beginAt": "2030-06-01 10:03" if finish else START,
                            "endAt": END, "status": "OPEN", "checkinStatus": "N", "abilities": expected_abilities}}
                self.wire.add("GET", "/api/v3/bookings/" + booking_id, detail)
                result = client.detail(booking_id)
                self.assertEqual(result["data"]["beginAt"], detail["data"]["beginAt"])
                self.assertEqual(result["data"]["checkinStatus"], "N")
                self.wire.add("GET", "/api/v3/bookings/" + booking_id, detail)
                suffix = "/finish" if finish else "/cancel"
                method = "PUT" if finish else "DELETE"
                mutation = {"code": 0, "noticeMessage": "提前结束预订成功"} if finish else {
                    "code": 0, "data": {"success": True, "abilities": []}, "noticeMessage": "取消预订成功"}
                self.wire.add(method, "/api/v3/bookings/" + booking_id + suffix, mutation)
                self.assertEqual(client.finish(booking_id) if finish else client.cancel(booking_id), mutation)
                recent = {"code": 0, "data": [{"id": booking_id, "status": "CANCEL", "abilities": [],
                          "beginAt": "2030-06-01 10:03" if finish else START,
                          "endAt": "2030-06-01 10:03" if finish else END, "duration": 0 if finish else 60}]}
                if finish:
                    recent["data"][0]["origEndAt"] = END
                self.wire.add("GET", "/api/v3/my/bookings/recent", recent)
                self.assertEqual(client.recent(), recent)
                for request, _ in self.wire.calls:
                    if urlsplit(request.url).path.startswith("/api/v3"):
                        self.assertEqual(request.headers["x-room-type"], room_type)
                self.wire.calls.clear()


if __name__ == "__main__":
    unittest.main(verbosity=2)
