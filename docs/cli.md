# 命令行参数

> 返回 [项目 README](../README.md) · [文档索引](README.md)

`login.py` 建立并验证凭据，`poc.py` 查询或操作预约。二者使用同一份 `.credentials.json`。

## login.py

| 参数 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `--login {password,wecom_scan}` | 交互选择 | 账号密码或企业微信扫码 |
| `--tenant` | `上海大学` | 统一身份认证 tenantId |
| `--method {wecom,sms}` | 交互选择 | 密码认证要求二步时使用的方式 |
| `--scan-timeout` | `180` | 扫码等待秒数 |
| `--no-qr` | 关闭 | 不渲染终端二维码；仍需交互终端展示即时扫码链接 |
| `--qr-style {block,ascii}` | `block` | 终端二维码样式 |
| `--out` | `.credentials.json` | 凭据输出路径；仅移动 profile 验证成功后保存 |
| `--cookie "<串>"` | 无 | 手动提供本站 Cookie，跳过 SSO 认证；仍需移动页面与 profile 校验 |
| 环境变量 `SHU_SEAT_COOKIE` | 无 | `--cookie` 的环境变量替代方式 |
| 环境变量 `SHU_SEAT_CREDENTIALS` | 无 | 未提供 `--out` 时使用的凭据路径 |
| `--check` | 关闭 | 从 `--out` 指定的已有凭据读取会话，只做移动 profile 检查 |
| `--room-type` | `LIB_SEAT` | 登录后校验使用的移动入口；支持四种已捕获类型 |
| `--timeout` | `30` | HTTP 超时秒数 |
| `--base` | `https://there.shu.edu.cn` | 登录目标固定为此地址，其他地址会被拒绝 |
| `--insecure` | 关闭 | 关闭 TLS 证书校验，默认校验 |

```bash
python login.py --login password --method wecom
python login.py --login wecom_scan --scan-timeout 180
python login.py --room-type STATION --out .credentials.json
python login.py --check --out .credentials.json
```

Cookie 必须是 there 当前会话的完整 Cookie 串，包含本站返回的会话值。
手动 Cookie 无法代替移动 HTML 的 `sessionId`；程序仍会打开对应页面读取它。
`x-hys-session` 不从 Cookie.utoken 填充，详见 [登录说明](login.md)。

## poc.py

公共参数可放在子命令前或后：

```text
python poc.py [公共参数] <子命令> [子命令参数]
```

| 参数 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `--credentials` | `.credentials.json` | 登录生成的凭据路径 |
| 环境变量 `SHU_SEAT_CREDENTIALS` | 无 | 未显式提供路径时使用；再回退项目根 `.credentials.json` |
| `--room-type` | 凭据中的类型 | `LIB_SEAT` / `STATION` / `SEAT` / `CS_SEAT`；无子命令时逐一读取四类 |
| `--json` | 关闭 | 打印 JSON；默认打印便于阅读的表格 |
| `--capture` | 关闭 | 将脱敏操作结果写到项目根 `captures/poc-<命令>.json` |
| `--base` | 凭据中的 there 根地址 | 业务站根地址；Cookie 仍按原域与路径发送 |
| `--timeout` | `30` | HTTP 超时秒数 |
| `--insecure` | 关闭 | 关闭 TLS 证书校验 |

不带子命令时读取账号与四类型概览；不会创建、取消、结束或签到。
选择某一种类型的命令会读取它对应的移动入口，以该入口的页面 sessionId 发送请求。

### 查询命令

| 子命令 | 参数 | 对应操作 |
| :--- | :--- | :--- |
| `profile` | 无 | 当前用户 |
| `recent` | 无 | 最近预约 |
| `overview` | `--day YYYY-MM-DD` | 日期概览 |
| `areas` | `--begin YYYY-MM-DD --end YYYY-MM-DD` | 区域列表 |
| `rooms` | `--area <areaId> --begin "YYYY-MM-DD HH:mm" --end "YYYY-MM-DD HH:mm"` | 选定区域完整时段内的座位与规则 |
| `detail` | `<bookingId> [--show-checks / --no-show-checks]` | 图书馆与 24H 默认携带 `showChecks=true`，另两类省略 |

```bash
python poc.py --room-type SEAT --json recent
python poc.py --room-type CS_SEAT overview --day 2026-10-04
python poc.py --room-type LIB_SEAT detail "<bookingId>" --show-checks
```

`overview` 的 `day` 是一个日期；区域列表 `begin/end` 是日期。
座位查询使用同一组参数名称。`areas/rooms` 支持捕获的日期或完整时间格式；
实际选座应查询最终完整时段，`book` 必须提供完整日期时间。

### 创建预约

```bash
python poc.py --room-type LIB_SEAT book --area "<areaId>" --room "<roomId>" \
    --begin "2026-10-04 09:00" --end "2026-10-04 10:00" --dry-run
```

| 参数 | 说明 |
| :--- | :--- |
| `--area` | 本类型当前区域列表里的 areaId |
| `--room` | 指定时段区域详情中的 roomId；不是 bookingId |
| `--begin` / `--end` | 上海本地日期时间，格式 `YYYY-MM-DD HH:mm` |
| `--dry-run` | 查询 profile、区域与座位，组装捕获形状的请求体；不发送 POST 创建 |

创建体保留该座位的完整对象，并从 profile 填充 subject 与 meetingMembers。
本实现只提供单座位、单时段、本人预约，抓包未验证多座位、多时段或代预约。
本地规则检查用于提示已知约束，最终结果由服务端返回决定。

删除 `--dry-run` 后会执行实际创建。`JSON.code=0` 时获取返回的预约 ID，再查看实际详情；
业务拒绝或网络结果不明确时先查询 recent，不能直接把同一 POST 重发。

### 取消、提前结束与签到

```bash
python poc.py --room-type LIB_SEAT cancel "<bookingId>"
python poc.py --room-type STATION finish "<bookingId>"
python poc.py --room-type LIB_SEAT check-in "<bookingId>" --experimental
```

| 子命令 | 证据 / 行为 |
| :--- | :--- |
| `cancel` | `DELETE /api/v3/bookings/{bookingId}/cancel`，图书馆 / 延长 / 科艺实际调用过 |
| `finish` | `PUT /api/v3/bookings/{bookingId}/finish`，24H 实际调用过；成功后状态可以为 CANCEL |
| `check-in --experimental` | 图书馆 JS 中的 `POST /api/v3/bookings/{bookingId}/checkInUse`，调用没有第二个 body 参数；实际载荷 / 响应未知 |

操作前读取详情中的 `abilities`；cancel 与 close 分别对应取消和提前结束。
签到需要明确给出 `--experimental`，其服务端资格、定位 / 开放时间与响应契约尚未捕获。
返回包装中的 `schema_verified=false` 明确表示未验证，`response` 保留脱敏响应；
HTTP 状态或其中任何字段均不被程序解释为签到成功。
二维码图片 / 签到页面 URL 的方法继续保留未知，不作为 CLI 调用入口。

## 输出与脱敏

`--json` 用于阅读完整业务对象；凭据文件仅保存在本地，终端与 capture 中的会话、
授权码、姓名、联系方式和学号应隐藏。资源 ID 与请求结构仍保留，方便排查。
文档固定样本中的 bookingId 已改为稳定别名，不能据此调用真实接口。

`poc.py` 的退出码为：0 正常，2 参数或当前资源状态无效，6 HTTP / 业务失败，
9 凭据不可用，130 用户中断。实验签到退出 0 仅表示收到 JSON 响应。
