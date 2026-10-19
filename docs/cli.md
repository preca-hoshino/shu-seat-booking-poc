# 命令行

> [文档索引](README.md)

## 登录

```bash
python login.py --system both
python login.py --system there --login password --method wecom
python login.py --system chaoxing --login wecom_scan
python login.py --check
```

`--system` 选择 `there`、`chaoxing` 或 `both`；`--out` 和 `--out-chaoxing` 可指定凭据路径。扫码模式可用 `--scan-timeout` 调整等待时间。完整参数以 `python login.py --help` 为准。

## there 业务

```bash
python poc.py --room-type LIB_SEAT profile
python poc.py --room-type LIB_SEAT recent
python poc.py --room-type LIB_SEAT overview --day <YYYY-MM-DD>
python poc.py --room-type LIB_SEAT areas --begin <YYYY-MM-DD> --end <YYYY-MM-DD>
python poc.py --room-type LIB_SEAT rooms --area <areaId> --begin "<YYYY-MM-DD HH:mm>" --end "<YYYY-MM-DD HH:mm>"
python poc.py --room-type LIB_SEAT book --area <areaId> --room <roomId> --begin "<YYYY-MM-DD HH:mm>" --end "<YYYY-MM-DD HH:mm>" --dry-run
python poc.py --room-type LIB_SEAT detail <bookingId>
python poc.py --room-type LIB_SEAT cancel <bookingId>
python poc.py --room-type STATION finish <bookingId>
```

`--room-type` 可选 `LIB_SEAT`、`STATION`、`SEAT`、`CS_SEAT`。`book --dry-run` 只组装请求；去掉后才提交。there 的签到命令需要 `--experimental`，其服务端行为尚未确认。

## 超星业务

所有命令均加 `--system chaoxing`。`roomId` 为房间 ID，`reserveId` 为当前预约对象中的 `seatReserve.id`。

| 命令 | 用途 |
| --- | --- |
| `recent` | 当前和最近预约 |
| `rooms --day <YYYY-MM-DD>` | 当日房间 |
| `available --room <roomId> --day <YYYY-MM-DD> --begin <HH:MM> --end <HH:MM>` | 时段可用座位 |
| `reserve-info --room <roomId> --seat <seatNum>` | 座位当前预约 |
| `used-times --room <roomId> --seat <seatNum> --day <YYYY-MM-DD>` | 占用时段 |
| `book ... --dry-run` | 组装首次预约 |
| `renew ... --dry-run` | 组装同座位续约 |
| `sign <reserveId>` | 签到或回座 |
| `leave <reserveId>` | 暂离 |
| `signback <reserveId>` | 退座 |
| `cancel <reserveId>` | 取消预约 |

```bash
python poc.py --system chaoxing recent
python poc.py --system chaoxing signback <reserveId>
```

`--json` 打印结构化响应。`python poc.py --help` 和各子命令 `--help` 提供完整参数。操作前核对当前状态，操作后重新查询 `recent`。接口说明见 [超星座位](chaoxing.md)。
