"""预约协议常量：仅收录 HAR 请求或脚本直接调用的端点。"""

from __future__ import annotations

from datetime import timedelta, timezone

THERE_BASE = "https://there.shu.edu.cn"
DEFAULT_ROOM_TYPE = "LIB_SEAT"
LOCAL_TZ = timezone(timedelta(hours=8), name="Asia/Shanghai")
SUBMIT_INTERVAL = 10.0

# ---- 四个实际抓到的入口；其他三种 HTML 配置类型不作为可执行入口 ----
SYSTEMS = {
    "LIB_SEAT": {"name": "校本部图书馆", "path": "/mobile/libseat", "show_checks": True},
    "STATION": {"name": "24H学习空间", "path": "/mobile/seat2021", "show_checks": True},
    "SEAT": {"name": "延长智能中心", "path": "/mobile/seat-mgr", "show_checks": False},
    "CS_SEAT": {"name": "科学与艺术中心", "path": "/mobile/csseat", "show_checks": False},
}

# ---- 路径 + HTTP 方法；方法未知的 v2/二维码 URL 只写在 docs 中 ----
PROFILE_PATH = "/api/v3/my/profile"
RECENT_PATH = "/api/v3/my/bookings/recent"
OVERVIEW_PATH = "/api/v3/booking-status/overview"
AREAS_PATH = "/api/v3/booking-status/areas"
BOOKINGS_PATH = "/api/v3/bookings"

KNOWN_OPERATIONS = (
    ("GET", PROFILE_PATH),
    ("GET", RECENT_PATH),
    ("GET", OVERVIEW_PATH),
    ("GET", AREAS_PATH),
    ("GET", AREAS_PATH + "/{areaId}"),
    ("POST", BOOKINGS_PATH),
    ("GET", BOOKINGS_PATH + "/{bookingId}"),
    ("DELETE", BOOKINGS_PATH + "/{bookingId}/cancel"),
    ("PUT", BOOKINGS_PATH + "/{bookingId}/finish"),
)

REFERENCED_CHECKIN = ("POST", BOOKINGS_PATH + "/{bookingId}/checkInUse")
