# 超星（学习通）图书馆座位系统

> [项目首页](../README.md) · [文档索引](README.md) · [命令行](cli.md)

上海大学图书馆的超星座位预约系统覆盖钱伟长图书馆、嘉定联合馆与延长文荟馆。业务站点为 `https://office.chaoxing.com`，与 `there.shu.edu.cn` 的四类资源使用独立会话、端点和预约 ID。两者可共用统一身份认证入口，但业务 Cookie 不可互换。

本页记录客户端使用的请求形状。表中的字段是客户端当前发送的字段，不能据此推断服务端的最小必填集合。日期、开放时间、可用座位和账号权限应以当前服务端响应为准。

## 1. 会话与业务入口

`python login.py --system chaoxing` 建立并验证超星会话，凭据默认保存在 `.credentials.chaoxing.json`。登录链经统一身份认证、图书馆桥接站与超星换会话接口，最后以座位首页的 `userLoginInfo` 确认业务身份。具体换会话实现由项目的统一认证子模块维护；座位客户端只消费已验证的 chaoxing.com 域 Cookie。

| 页面 | 路径 | 用途 |
| --- | --- | --- |
| 座位首页 | `/front/third/apps/seat/index?fidEnc=...` | 验证会话；签到、退座等首页操作的 Referer |
| 选座页 | `/front/third/apps/seat/select` | 首次预约的当前签名盐 |
| 座位操作页 | `/front/apps/seat/code?id=<roomId>&seatNum=<seatNum>` | 续约的当前签名盐和 `fidEnc` |
| 错误页 | `/front/apps/reserve/error/...` | 页面阶段的业务错误，错误文字可能在 query 中 |

机构参数 `deptId` / `fid` 指图书馆机构，`deptIdEnc` / `fidEnc` 为该机构的编码值。客户端默认值定义在 [config.py](../seat/chaoxing/config.py)；如服务端配置变化，应同步更新。房间 `roomId`、座位 `seatNum` 与预约 `reserveId` 是三类不同的标识。

## 2. 响应与状态

业务接口通常返回 JSON 信封：`{"success": true, "data": ...}`。操作类接口成功时也可能只返回 `{"success": true}`。请求收到 HTTP 200 后，仍须检查 `success`；`success=false` 时读取 `msg`，不要当成成功。提交超时或结果不明确时，先查询当前预约，不直接重复提交。

座位首页的 `data.curReserves` 是当前预约，`data.nearReserves` 是最近预约。每条预约的 `seatReserve.id` 是签到、暂离、回座、退座和取消使用的数字 `reserveId`。列表中的常见状态为 `0` 待签到、`1` 在座、`2` 已退座、`3` 暂离、`7` 已结束；未列出的状态保持服务端原值。

## 3. 查询与配置接口

除特别说明外，GET 字段放在 query，POST 字段使用 `application/x-www-form-urlencoded`。房间、日期和座位参数应由当前查询结果取得。

| 方法 | 路径 | 客户端发送的字段 | 返回或用途 |
| --- | --- | --- | --- |
| GET | `/data/apps/seat/index` | `fidEnc`、`r`（随机数） | `seatConfig`、`curReserves`、`nearReserves`、`officeDomain` |
| GET | `/data/apps/seat/config` | `fidEnc` | 座位规则配置 |
| GET | `/data/apps/seat/levels` | `deptIdEnc`、`type=0` | 场馆层级 |
| GET | `/data/apps/seat/room/list` | `time`、`cpage`、`pageSize`、`firstLevelName`、`secondLevelName`、`thirdLevelName`、`day`、`deptIdEnc` | 房间列表与容量 |
| GET | `/data/apps/seat/room/reserve-window/check` | `roomId`、`day`、`deptIdEnc`、`fidEnc` | 预约窗口状态 |
| POST | `/data/apps/seat/room/info` | `id=<roomId>`、`fidEnc`；选座时另传 `toDay`、`queryReserve` | `seatRoom` 和预约区间等房间信息 |
| POST | `/data/apps/seat/getusedseatnums` | `roomId`、`startTime`、`endTime`、`day`、`fidEnc` | 指定时段已占座位 |
| GET | `/data/apps/seat/check/exist` | `seatNum`、`roomId` | 座位检查 |
| GET / POST | `/data/apps/seat/reserve/info` | `id=<roomId>`、`seatNum` | 指定座位的当前预约信息；CLI 默认 GET，`--post` 使用 POST |
| POST | `/data/apps/seat/getusedtimes` | `roomId`、`seatNum`、`day`、`fidEnc` | 座位当日已占时段，`data` 包含毫秒时间戳区间 |
| GET | `/data/apps/seat/curusedshow` | `fidEnc` | 当前使用展示配置 |
| GET | `/data/apps/seat/person/role` | `fidEnc` | 用户座位角色 |
| GET | `/data/apps/seat/entrance/config` | `appType`、`fidEnc` | 入口功能开关 |
| GET | `/data/apps/seat/identity/verify` | `mappId`、`fidEnc` | 身份与管理权限 |
| GET | `/data/apps/seat/address` | `deptId`、`roomId` | 签到页使用的位置范围 |
| GET | `/data/apps/reserve/link/domain/rules` | 无 | 页面域名规则 |
| GET | `/data/apps/seat/i18n` | 无 | 页面文案 |
| POST | `/data/apps/seat/risk/check/config` | `appType`、`appId=<deptId>` | 风控配置 |

`poc.py available` 并非独立服务端接口。它读取 `room/info` 的容量与起始座号，再减去 `getusedseatnums` 返回的已占座位，得到客户端派生的可用列表；最终能否预约仍以提交结果为准。`recent` 也是客户端从 `index` 响应拆分出的视图。

座位号在选座提交与占用查询中按三位格式处理；操作页与 `reserve/info` 的 `seatNum` 使用未补零数字形式。客户端负责转换，调用方仍应传当前房间的有效座位号。

## 4. 首次预约与续约

两种操作均请求 `POST /data/apps/seat/submit`，但取盐页面和参与签名的字段不同。提交前打开对应页面，读取隐藏域 `submit_enc`；该值应按本次页面重新获取。签名算法将参与字段按键名字母序拼为 `[key=value]`，末尾加 `[salt]`，对 UTF-8 文本计算小写 MD5。

| 场景 | 取盐页面 | form 与签名字段 | Referer |
| --- | --- | --- | --- |
| 首次预约 | `/front/third/apps/seat/select` | `captcha`、`day`、`deptIdEnc`、`endTime`、`roomId`、`seatNum`、`startTime`、`wyToken`，再附 `enc` | 当前选座页 |
| 续约 | `/front/apps/seat/code` | `captcha`、`day`、`endTime`、`roomId`、`seatNum`、`startTime`、`wyToken`，再附 `enc` | 当前座位操作页 |

`day` 格式为 `YYYY-MM-DD`，`startTime` / `endTime` 为 `HH:MM`；结束时间必须晚于开始时间。`captcha` 和 `wyToken` 未使用时也作为空字段参与签名。首次预约的签名包含 `deptIdEnc`，续约不包含它；两者的 `enc` 不能互用。

成功响应中的 `data.seatReserve.id` 是后续操作的预约 ID。续约新增同一座位的时段，是否允许衔接及最终时段以服务端校验为准。客户端在同一实例中限制提交频率，并且不会自动重试结果不明确的写请求。`book --dry-run` 和 `renew --dry-run` 会拉取本次页面值并组装请求，但不发送 `submit`。

## 5. 当前预约操作

执行前运行 `python poc.py --system chaoxing recent`，在目标预约的 `seatReserve.id` 中取得 `reserveId`。以下操作均使用这个数字 ID，不能使用 `roomId` 或 `seatNum` 代替。

| 操作 | 方法与路径 | 参数位置 | Referer | 响应处理 |
| --- | --- | --- | --- | --- |
| 签到 / 暂离后回座 | `GET /data/apps/seat/sign` | query `id=<reserveId>` | 座位操作页 | 检查 `success`，刷新预约 |
| 暂离 | `POST /data/apps/seat/leave` | form `id=<reserveId>` | 座位操作页 | 检查 `success`，刷新预约 |
| 退座 | `GET /data/apps/seat/signback` | query `id=<reserveId>` | 座位首页 | 检查 `success`，刷新预约 |
| 取消 | `GET /data/apps/seat/cancel` | query `id=<reserveId>` | 默认业务请求头 | 检查 `success`，刷新预约 |

退座请求没有请求体；成功响应可仅有 `{"success":true}`，不要求 `data`。刷新后，目标预约应离开 `curReserves`，可能出现在 `nearReserves` 且状态为 `2`。若刷新失败或状态未变化，应向服务端重新查询后再决定下一步，不要仅凭一次 HTTP 状态推断结果。退座与取消的业务语义不同，调用前需核对当前状态。

## 6. 命令行示例

以下占位符由当前查询结果替换；示例没有固定日期、房间、座位或预约 ID。

```bash
python login.py --system chaoxing
python poc.py --system chaoxing recent
python poc.py --system chaoxing rooms --day <YYYY-MM-DD>
python poc.py --system chaoxing available --room <roomId> --day <YYYY-MM-DD> --begin <HH:MM> --end <HH:MM>
python poc.py --system chaoxing book --room <roomId> --day <YYYY-MM-DD> --begin <HH:MM> --end <HH:MM> --seat <seatNum> --dry-run
python poc.py --system chaoxing renew --room <roomId> --day <YYYY-MM-DD> --begin <HH:MM> --end <HH:MM> --seat <seatNum> --dry-run
python poc.py --system chaoxing sign <reserveId>
python poc.py --system chaoxing leave <reserveId>
python poc.py --system chaoxing signback <reserveId>
python poc.py --system chaoxing cancel <reserveId>
```

`--json` 可查看结构化业务结果；默认终端输出会隐藏姓名、学工号、联系方式、页面盐和会话信息。具体命令参数见 [命令行文档](cli.md)。离线测试覆盖方法、字段、Referer、响应信封与命令路由；实际权限和服务时段以当前服务端为准。
