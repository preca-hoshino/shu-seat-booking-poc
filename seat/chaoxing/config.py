"""超星（学习通）图书馆座位预约协议常量。

来源：2026-10-05 两份 HAR（业务链 `图书馆分馆座位预约.har`、登录链 `补充.har`）
与浏览器实测。只收录已实测的端点与参数；未捕获项不写。

机构说明：`fid=35480` 是"上海大学图书馆"在超星的机构号（校图书馆采购的
座位系统单位），与全校账号 `209`（上海大学/泛雅）是两个不同的机构。
"""

from __future__ import annotations

# ---- 站点 ----
CX_BASE = "https://office.chaoxing.com"
CX_HOST = "office.chaoxing.com"
CX_DOMAIN_BARE = "chaoxing.com"        # 全站 Cookie 域（login6 一次性下发）

# ---- 机构 ----
DEPT_ID = "35480"                 # 图书馆机构号（fid）
DEPT_ENC = "00bae7f2bdea485a"     # deptIdEnc == fidEnc，座位 API 与页面通用
# 换会话（newsso → 5read → login6）的 client_id / redirect_uri / 跳数上限等常量
# 已随实现外置到 vendor 子模块：vendor/shu-sso-poc/systems/chaoxing.com/config.py

# 浏览器实测：普通桌面 UA 与服务端 + 接口全通；无需企微 UA 伪装。
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36")

DEFAULT_TIMEOUT = 30.0
SUBMIT_INTERVAL = 10.0            # 服务端"同一用户10秒只能提交一次"（HAR 实测文案）

# ---- 页面 ----
SEAT_INDEX_PATH = "/front/third/apps/seat/index"
SEAT_SELECT_PATH = "/front/third/apps/seat/select"
# select 页失败会跳转到这里（200 错误页，msg 在 query 里）
ERROR_PATH_PREFIX = "/front/apps/reserve/error"

# ---- 实测 API（13 个，2026-10-05 HAR + 浏览器复验）----
HOME_PATH = "/data/apps/seat/index"                 # GET  fidEnc,r → seatConfig/curReserves/nearReserves
CONFIG_PATH = "/data/apps/seat/config"              # GET  fidEnc → 规则配置
LEVELS_PATH = "/data/apps/seat/levels"              # GET  deptIdEnc,type=0 → 层级字典
ROOM_LIST_PATH = "/data/apps/seat/room/list"        # GET  time,cpage,pageSize,day,deptIdEnc → seatRoomList
WINDOW_CHECK_PATH = "/data/apps/seat/room/reserve-window/check"   # GET roomId,day,deptIdEnc,fidEnc
ROOM_INFO_PATH = "/data/apps/seat/room/info"        # POST id,toDay,fidEnc,queryReserve → seatRoom/groupedReservesMap
USED_SEATS_PATH = "/data/apps/seat/getusedseatnums"  # POST roomId,startTime,endTime,day,fidEnc
CHECK_EXIST_PATH = "/data/apps/seat/check/exist"    # GET  seatNum,roomId
SUBMIT_PATH = "/data/apps/seat/submit"              # POST（含 enc，见 enc.py）
CANCEL_PATH = "/data/apps/seat/cancel"              # GET  id
CUR_USED_PATH = "/data/apps/seat/curusedshow"       # GET  fidEnc
PERSON_ROLE_PATH = "/data/apps/seat/person/role"    # GET  fidEnc
ENTRANCE_CONFIG_PATH = "/data/apps/seat/entrance/config"   # GET appType,fidEnc
IDENTITY_VERIFY_PATH = "/data/apps/seat/identity/verify"   # GET mappId,fidEnc
DOMAIN_RULES_PATH = "/data/apps/reserve/link/domain/rules"  # GET
RISK_CHECK_PATH = "/data/apps/seat/risk/check/config"       # POST appType,appId

# ---- 规则（HAR/页面实测值；服务端响应为准）----
OPEN_TIME = "07:00"               # 当天预约开放（beforeOpenTimeStamp）
SERVICE_START = "08:00"           # 每日开放时段
SERVICE_END = "22:00"
TIME_UNIT_MINUTES = 30            # timeUnit
MIN_DURATION_HOURS = 1.0          # minReserveDuration
MAX_CONCURRENT_RESERVES = 2       # reserveNumLimit
SAME_DAY_ONLY = True              # 次日 select 页报"未到开放预约时间"（实测）
