# 座位系统研究结论

> [文档索引](README.md)

上海大学座位预约涉及两套独立业务系统：

| 系统 | 地址 | 资源范围 | 凭据 |
| --- | --- | --- | --- |
| there | `there.shu.edu.cn` | 图书馆、24H 学习空间、延长智能中心、科学与艺术中心 | `.credentials.json` |
| 超星学习通 | `office.chaoxing.com` | 图书馆座位 | `.credentials.chaoxing.json` |

两套业务会话可由统一身份认证建立，但业务 Cookie、请求头、资源 ID 和预约 ID 不能互换。[登录文档](login.md)说明认证与会话；[there API](api.md)和[超星 API](chaoxing.md)分别列出操作。

there 的四入口共用 `/api/v3`，通过移动页面和 `x-room-type` 选择资源。查询当前用户、可用区域与座位后，使用即时数据创建预约；再以返回的 `bookingId` 查询、取消或结束。对业务结果应检查 JSON `code`。

超星系统从座位首页读取当前预约，查询房间、座位和占用时段。创建与续约通过动态 `enc` 提交。签到、暂离、回座与退座使用 `seatReserve.id`；退座为 `GET /data/apps/seat/signback?id=<reserveId>`，成功后应刷新预约列表确认状态。

本项目的离线测试检查协议组装、凭据边界、响应处理和命令路由。在线权限、开放时间、可用时段及异常响应以服务端当次结果为准。参见[预约流程](booking.md)、[命令行](cli.md)和[测试](testing.md)。
