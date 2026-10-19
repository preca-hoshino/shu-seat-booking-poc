# SHU Seat Booking POC

上海大学座位预约命令行工具，支持 there 四类资源与超星（学习通）图书馆座位。两套系统共享统一身份认证入口，但业务会话和预约 ID 独立。

| 系统 | 资源 | 命令参数 |
| --- | --- | --- |
| there | 校本部图书馆、24H 学习空间、延长智能中心、科学与艺术中心 | `--system there`（默认） |
| 超星 | 学习通图书馆座位 | `--system chaoxing` |

## 安装与登录

需要 Python 3.10+。安装 `requirements.txt` 后运行：

```bash
python login.py
python login.py --system chaoxing
python login.py --check
```

`login.py` 默认可建立两套业务凭据，分别保存到 `.credentials.json` 和 `.credentials.chaoxing.json`。凭据失效时重新登录。更多登录方式见 [登录说明](docs/login.md)。

## 使用

无子命令时只读展示账号与预约概览。日期、区域、座位号和预约 ID 应从当前查询结果选择。

```bash
python poc.py
python poc.py --room-type LIB_SEAT recent
python poc.py --room-type LIB_SEAT overview --day <YYYY-MM-DD>
python poc.py --room-type LIB_SEAT areas --begin <YYYY-MM-DD> --end <YYYY-MM-DD>
python poc.py --room-type LIB_SEAT rooms --area <areaId> --begin "<YYYY-MM-DD HH:mm>" --end "<YYYY-MM-DD HH:mm>"
python poc.py --room-type LIB_SEAT book --area <areaId> --room <roomId> --begin "<YYYY-MM-DD HH:mm>" --end "<YYYY-MM-DD HH:mm>" --dry-run
```

超星座位操作：

```bash
python poc.py --system chaoxing recent
python poc.py --system chaoxing rooms --day <YYYY-MM-DD>
python poc.py --system chaoxing sign <reserveId>
python poc.py --system chaoxing leave <reserveId>
python poc.py --system chaoxing signback <reserveId>
```

退座使用当前预约的 `seatReserve.id`。写操作后重新查询预约状态；HTTP 成功仍须检查业务结果。创建与续约支持 `--dry-run`，详细参数见 [命令行文档](docs/cli.md) 和 [超星接口](docs/chaoxing.md)。

## 文档与测试

[文档索引](docs/README.md)包含 [there API](docs/api.md)、[登录](docs/login.md)、[预约流程](docs/booking.md)、[超星接口](docs/chaoxing.md)和 [OpenAPI](docs/openapi/there.openapi.yaml)。离线测试：

```bash
python -m unittest discover -s tests -v
```

[测试说明](docs/testing.md)列出验证范围与真实环境检查步骤。

## License

AGPL-3.0
