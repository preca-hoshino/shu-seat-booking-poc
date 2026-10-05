# 证据、校验与请求时间线

> 返回 [项目 README](../README.md) · [文档索引](README.md)

资料依据 2026-10-03 的四个用户 HAR 与固定提交的 `shu-sso-poc`。以下保留完整捕获字段、脱敏样例与来源边界；章节编号沿用[完整研究记录](research.md)，方便交叉引用。接口章节见 [api.md](api.md)，认证章节见 [login.md](login.md)，预约设计与四条实测链见 [booking.md](booking.md)，来源及九十条时间线见 [evidence.md](evidence.md)。

## 9 证据与校验说明

证据 `文件名#N` 指原始 log.entries[N-1]，不是时间排序后的编号。HAR 顺序与请求时间不完全一致，本文按 startedDateTime 整理，时间统一为上海时区。敏感值以占位符替代，BOOKING_LIB/STATION/SEAT/CS 是脱敏别名，不能用于真实请求。

| HAR | SHA256 | 业务请求数 |
| --- | --- | --- |
| 校本部图书馆预约.har | `7516ed730fb70270612a9d088fc7b9e015d84dc4f8dc862089e858b9a60605e9` | 31 |
| 24H学习空间预约.har | `3dc6b69d77bf7bb107e041a174bc24f9549cce0a9b18bed14b4dcb5f3c239f2b` | 14 |
| 延长智能中心预约.har | `eb75c19e26f51151116e9330e1dc6fe9eb0bc3abd102eec3a85f064bc7e0713b` | 18 |
| 科学与艺术中心预约.har | `665607ed11bd0723468c8d3222783ff45755a363b6e0ece4cbed5e66eb218198` | 27 |

项目固定提交时间为 2026-10-03 01:10:52 +08:00，commit=`941c7d5ea876c3b511f1bf9a8862b0cf91df9c3b`。参考文件如下：

- [systems/there.shu.edu.cn/README.md](https://github.com/preca-hoshino/shu-sso-poc/blob/941c7d5ea876c3b511f1bf9a8862b0cf91df9c3b/systems/there.shu.edu.cn/README.md)
- [systems/there.shu.edu.cn/config.py](https://github.com/preca-hoshino/shu-sso-poc/blob/941c7d5ea876c3b511f1bf9a8862b0cf91df9c3b/systems/there.shu.edu.cn/config.py)
- [src/client.py](https://github.com/preca-hoshino/shu-sso-poc/blob/941c7d5ea876c3b511f1bf9a8862b0cf91df9c3b/src/client.py)
- [src/config.py](https://github.com/preca-hoshino/shu-sso-poc/blob/941c7d5ea876c3b511f1bf9a8862b0cf91df9c3b/src/config.py)
- [src/runner.py](https://github.com/preca-hoshino/shu-sso-poc/blob/941c7d5ea876c3b511f1bf9a8862b0cf91df9c3b/src/runner.py)
- [src/utils.py](https://github.com/preca-hoshino/shu-sso-poc/blob/941c7d5ea876c3b511f1bf9a8862b0cf91df9c3b/src/utils.py)
- [src/entry_password.py](https://github.com/preca-hoshino/shu-sso-poc/blob/941c7d5ea876c3b511f1bf9a8862b0cf91df9c3b/src/entry_password.py)
- [src/rsa_key.py](https://github.com/preca-hoshino/shu-sso-poc/blob/941c7d5ea876c3b511f1bf9a8862b0cf91df9c3b/src/rsa_key.py)
- [README.md](https://github.com/preca-hoshino/shu-sso-poc/blob/941c7d5ea876c3b511f1bf9a8862b0cf91df9c3b/README.md)

严格来源 OpenAPI 包含 26 个操作：13 个 HAR 实际请求操作（9 业务、4 页面）、2 个前端脚本/导航与项目来源操作、11 个项目明确方法操作。另有 7 条方法未知的 URL 记录；它们保存在扩展元数据，不冒充 HTTP 操作。外部登录操作按各自主机配置 servers。

规范按 OpenAPI 3.1.1 离线解析与检查内部引用；90 个原始业务响应、8 个原始创建体匹配其捕获 schema。个人及会话值与原 HAR 对比做脱敏检查。该校验只验证规范结构及样本一致性，不证明未捕获操作在线可用。

本次仍未知的内容包括：跨入口令牌替换、移动入口未登录跳转、真正签到条件、字段最低必填集合、多座位/多时段/代预约行为、未访问区域、v2 完整契约，以及登录项目所述行为在其他部署版本的适用性。

## 附录 全部九十条业务请求时间线

用于追溯正文中的参数、错误和刷新行为。query 按抓包实际值显示，返回码为 JSON.code，HTTP 均为 200。完整创建 JSON 与返回字段见正文。

| 上海时间 | 系统 | 证据 | 方法 | 路径 | query | JSON.code |
| --- | --- | --- | --- | --- | --- | --- |
| 00:25:31.686 | 校本部图书馆 | #68 | GET | `/api/v3/my/profile` | {} | 0 |
| 00:25:31.897 | 校本部图书馆 | #66 | GET | `/api/v3/my/bookings/recent` | {} | 0 |
| 00:25:45.902 | 校本部图书馆 | #57 | GET | `/api/v3/booking-status/areas` | {"begin":"2026-10-03","end":"2026-10-03"} | 0 |
| 00:25:45.940 | 校本部图书馆 | #67 | GET | `/api/v3/booking-status/overview` | {"day":"2026-10-03"} | 0 |
| 00:25:50.435 | 校本部图书馆 | #55 | GET | `/api/v3/booking-status/areas` | {"begin":"2026-10-04","end":"2026-10-04"} | 0 |
| 00:25:50.435 | 校本部图书馆 | #56 | GET | `/api/v3/booking-status/overview` | {"day":"2026-10-04"} | 0 |
| 00:25:52.069 | 校本部图书馆 | #53 | GET | `/api/v3/booking-status/overview` | {"day":"2026-10-05"} | 0 |
| 00:25:52.070 | 校本部图书馆 | #54 | GET | `/api/v3/booking-status/areas` | {"begin":"2026-10-05","end":"2026-10-05"} | 0 |
| 00:25:54.358 | 校本部图书馆 | #47 | GET | `/api/v3/booking-status/areas/KRdcGiyK99gzrqCepi91Cv` | {"begin":"2026-10-05","end":"2026-10-05"} | 0 |
| 00:26:01.206 | 校本部图书馆 | #41 | GET | `/api/v3/booking-status/areas/KRdcGiyK99gzrqCepi91Cv` | {"begin":"2026-10-05 09:00","end":"2026-10-05"} | 0 |
| 00:26:01.216 | 校本部图书馆 | #40 | GET | `/api/v3/booking-status/areas/KRdcGiyK99gzrqCepi91Cv` | {"begin":"2026-10-05 09:00","end":"2026-10-05 12:00"} | 0 |
| 00:26:04.232 | 校本部图书馆 | #39 | POST | `/api/v3/bookings` | {} | 200 |
| 00:26:05.436 | 校本部图书馆 | #38 | GET | `/api/v3/my/bookings/recent` | {} | 0 |
| 00:26:05.439 | 校本部图书馆 | #37 | GET | `/api/v3/booking-status/areas/KRdcGiyK99gzrqCepi91Cv` | {"begin":"2026-10-05 09:00","end":"2026-10-05 12:00"} | 0 |
| 00:26:05.593 | 校本部图书馆 | #35 | GET | `/api/v3/booking-status/overview` | {"day":"2026-10-05"} | 0 |
| 00:26:13.569 | 校本部图书馆 | #34 | POST | `/api/v3/bookings` | {} | 200 |
| 00:26:13.835 | 校本部图书馆 | #33 | GET | `/api/v3/my/bookings/recent` | {} | 0 |
| 00:26:13.836 | 校本部图书馆 | #31 | GET | `/api/v3/booking-status/overview` | {"day":"2026-10-05"} | 0 |
| 00:26:14.034 | 校本部图书馆 | #30 | GET | `/api/v3/booking-status/areas/KRdcGiyK99gzrqCepi91Cv` | {"begin":"2026-10-05 09:00","end":"2026-10-05 12:00"} | 0 |
| 00:26:18.501 | 校本部图书馆 | #29 | GET | `/api/v3/booking-status/overview` | {"day":"2026-10-04"} | 0 |
| 00:26:19.001 | 校本部图书馆 | #27 | GET | `/api/v3/booking-status/overview` | {"day":"2026-10-03"} | 0 |
| 00:26:24.391 | 校本部图书馆 | #26 | GET | `/api/v3/booking-status/areas/KRdcGiyK99gzrqCepi91Cv` | {"begin":"2026-10-03","end":"2026-10-03"} | 0 |
| 00:26:28.728 | 校本部图书馆 | #22 | GET | `/api/v3/booking-status/areas/KRdcGiyK99gzrqCepi91Cv` | {"begin":"2026-10-03 08:30","end":"2026-10-03"} | 0 |
| 00:26:28.739 | 校本部图书馆 | #21 | GET | `/api/v3/booking-status/areas/KRdcGiyK99gzrqCepi91Cv` | {"begin":"2026-10-03 08:30","end":"2026-10-03 09:30"} | 0 |
| 00:26:31.483 | 校本部图书馆 | #20 | POST | `/api/v3/bookings` | {} | 0 |
| 00:26:32.777 | 校本部图书馆 | #19 | GET | `/api/v3/booking-status/areas/KRdcGiyK99gzrqCepi91Cv` | {"begin":"2026-10-03 08:30","end":"2026-10-03 09:30"} | 0 |
| 00:26:32.778 | 校本部图书馆 | #17 | GET | `/api/v3/my/bookings/recent` | {} | 0 |
| 00:26:33.236 | 校本部图书馆 | #14 | GET | `/api/v3/booking-status/overview` | {"day":"2026-10-03"} | 0 |
| 00:26:33.553 | 校本部图书馆 | #12 | GET | `/api/v3/bookings/BOOKING_LIB` | {"showChecks":"true"} | 0 |
| 00:26:46.228 | 校本部图书馆 | #5 | DELETE | `/api/v3/bookings/BOOKING_LIB/cancel` | {} | 0 |
| 00:26:47.377 | 校本部图书馆 | #4 | GET | `/api/v3/my/bookings/recent` | {} | 0 |
| 00:32:08.477 | 24H学习空间 | #36 | GET | `/api/v3/my/profile` | {} | 0 |
| 00:32:08.743 | 24H学习空间 | #35 | GET | `/api/v3/my/bookings/recent` | {} | 0 |
| 00:32:12.413 | 24H学习空间 | #27 | GET | `/api/v3/booking-status/overview` | {"day":"2026-10-03"} | 0 |
| 00:32:12.449 | 24H学习空间 | #38 | GET | `/api/v3/booking-status/areas` | {"begin":"2026-10-03","end":"2026-10-03"} | 0 |
| 00:32:16.290 | 24H学习空间 | #21 | GET | `/api/v3/booking-status/areas/DsNjTXf8icSMh3SXB5HPge` | {"begin":"2026-10-03","end":"2026-10-03"} | 0 |
| 00:32:21.355 | 24H学习空间 | #16 | GET | `/api/v3/booking-status/areas/DsNjTXf8icSMh3SXB5HPge` | {"begin":"2026-10-03 00:30","end":"2026-10-03"} | 0 |
| 00:32:21.363 | 24H学习空间 | #15 | GET | `/api/v3/booking-status/areas/DsNjTXf8icSMh3SXB5HPge` | {"begin":"2026-10-03 00:30","end":"2026-10-03 01:30"} | 0 |
| 00:32:24.484 | 24H学习空间 | #14 | POST | `/api/v3/bookings` | {} | 0 |
| 00:32:25.751 | 24H学习空间 | #13 | GET | `/api/v3/my/bookings/recent` | {} | 0 |
| 00:32:25.753 | 24H学习空间 | #12 | GET | `/api/v3/booking-status/areas/DsNjTXf8icSMh3SXB5HPge` | {"begin":"2026-10-03 00:30","end":"2026-10-03 01:30"} | 0 |
| 00:32:25.792 | 24H学习空间 | #37 | GET | `/api/v3/booking-status/overview` | {"day":"2026-10-03"} | 0 |
| 00:32:26.305 | 24H学习空间 | #9 | GET | `/api/v3/bookings/BOOKING_STATION` | {"showChecks":"true"} | 0 |
| 00:32:35.607 | 24H学习空间 | #2 | PUT | `/api/v3/bookings/BOOKING_STATION/finish` | {} | 0 |
| 00:32:36.707 | 24H学习空间 | #1 | GET | `/api/v3/my/bookings/recent` | {} | 0 |
| 00:33:48.303 | 延长智能中心 | #63 | GET | `/api/v3/my/profile` | {} | 0 |
| 00:33:48.998 | 延长智能中心 | #64 | GET | `/api/v3/my/bookings/recent` | {} | 0 |
| 00:33:52.175 | 延长智能中心 | #52 | GET | `/api/v3/booking-status/areas` | {"begin":"2026-10-03","end":"2026-10-03"} | 0 |
| 00:33:52.175 | 延长智能中心 | #53 | GET | `/api/v3/booking-status/overview` | {"day":"2026-10-03"} | 0 |
| 00:33:54.465 | 延长智能中心 | #44 | GET | `/api/v3/booking-status/overview` | {"day":"2026-10-04"} | 0 |
| 00:33:54.466 | 延长智能中心 | #45 | GET | `/api/v3/booking-status/areas` | {"begin":"2026-10-04","end":"2026-10-04"} | 0 |
| 00:33:55.324 | 延长智能中心 | #42 | GET | `/api/v3/booking-status/areas` | {"begin":"2026-10-05","end":"2026-10-05"} | 0 |
| 00:33:55.325 | 延长智能中心 | #41 | GET | `/api/v3/booking-status/overview` | {"day":"2026-10-05"} | 0 |
| 00:33:58.794 | 延长智能中心 | #32 | GET | `/api/v3/booking-status/areas/KbuCBLACKv74KmiBqE51z6` | {"begin":"2026-10-03","end":"2026-10-03"} | 0 |
| 00:34:00.963 | 延长智能中心 | #28 | GET | `/api/v3/booking-status/areas/KbuCBLACKv74KmiBqE51z6` | {"begin":"2026-10-03 09:30","end":"2026-10-03"} | 0 |
| 00:34:00.964 | 延长智能中心 | #27 | GET | `/api/v3/booking-status/areas/KbuCBLACKv74KmiBqE51z6` | {"begin":"2026-10-03 09:30","end":"2026-10-03 10:30"} | 0 |
| 00:34:06.351 | 延长智能中心 | #26 | POST | `/api/v3/bookings` | {} | 0 |
| 00:34:07.746 | 延长智能中心 | #23 | GET | `/api/v3/booking-status/overview` | {"day":"2026-10-03"} | 0 |
| 00:34:07.746 | 延长智能中心 | #25 | GET | `/api/v3/my/bookings/recent` | {} | 0 |
| 00:34:07.898 | 延长智能中心 | #20 | GET | `/api/v3/booking-status/areas/KbuCBLACKv74KmiBqE51z6` | {"begin":"2026-10-03 09:30","end":"2026-10-03 10:30"} | 0 |
| 00:34:08.202 | 延长智能中心 | #18 | GET | `/api/v3/bookings/BOOKING_SEAT` | {} | 0 |
| 00:34:25.456 | 延长智能中心 | #3 | DELETE | `/api/v3/bookings/BOOKING_SEAT/cancel` | {} | 0 |
| 00:34:26.686 | 延长智能中心 | #2 | GET | `/api/v3/my/bookings/recent` | {} | 0 |
| 00:35:07.011 | 科学与艺术中心 | #62 | GET | `/api/v3/my/profile` | {} | 0 |
| 00:35:07.230 | 科学与艺术中心 | #60 | GET | `/api/v3/my/bookings/recent` | {} | 0 |
| 00:35:10.300 | 科学与艺术中心 | #51 | GET | `/api/v3/booking-status/overview` | {"day":"2026-10-03"} | 0 |
| 00:35:10.336 | 科学与艺术中心 | #61 | GET | `/api/v3/booking-status/areas` | {"begin":"2026-10-03","end":"2026-10-03"} | 0 |
| 00:35:11.799 | 科学与艺术中心 | #46 | GET | `/api/v3/booking-status/areas` | {"begin":"2026-10-04","end":"2026-10-04"} | 0 |
| 00:35:11.799 | 科学与艺术中心 | #47 | GET | `/api/v3/booking-status/overview` | {"day":"2026-10-04"} | 0 |
| 00:35:12.542 | 科学与艺术中心 | #41 | GET | `/api/v3/booking-status/areas` | {"begin":"2026-10-05","end":"2026-10-05"} | 0 |
| 00:35:12.542 | 科学与艺术中心 | #42 | GET | `/api/v3/booking-status/overview` | {"day":"2026-10-05"} | 0 |
| 00:35:14.202 | 科学与艺术中心 | #38 | GET | `/api/v3/booking-status/areas/VQyeEokNwJnq7h8sVwmnfg` | {"begin":"2026-10-03","end":"2026-10-03"} | 0 |
| 00:35:17.906 | 科学与艺术中心 | #36 | GET | `/api/v3/booking-status/areas/VQyeEokNwJnq7h8sVwmnfg` | {"begin":"2026-10-03 09:00","end":"2026-10-03"} | 0 |
| 00:35:17.910 | 科学与艺术中心 | #35 | GET | `/api/v3/booking-status/areas/VQyeEokNwJnq7h8sVwmnfg` | {"begin":"2026-10-03 09:00","end":"2026-10-03 18:00"} | 0 |
| 00:35:20.934 | 科学与艺术中心 | #34 | POST | `/api/v3/bookings` | {} | 200 |
| 00:35:22.084 | 科学与艺术中心 | #33 | GET | `/api/v3/my/bookings/recent` | {} | 0 |
| 00:35:22.088 | 科学与艺术中心 | #31 | GET | `/api/v3/booking-status/areas/VQyeEokNwJnq7h8sVwmnfg` | {"begin":"2026-10-03 09:00","end":"2026-10-03 18:00"} | 0 |
| 00:35:22.240 | 科学与艺术中心 | #30 | GET | `/api/v3/booking-status/overview` | {"day":"2026-10-03"} | 0 |
| 00:35:27.759 | 科学与艺术中心 | #29 | GET | `/api/v3/booking-status/areas/VQyeEokNwJnq7h8sVwmnfg` | {"begin":"2026-10-03 09:00","end":"2026-10-03 14:00"} | 0 |
| 00:35:29.615 | 科学与艺术中心 | #28 | POST | `/api/v3/bookings` | {} | 200 |
| 00:35:29.867 | 科学与艺术中心 | #26 | GET | `/api/v3/booking-status/areas/VQyeEokNwJnq7h8sVwmnfg` | {"begin":"2026-10-03 09:00","end":"2026-10-03 14:00"} | 0 |
| 00:35:29.867 | 科学与艺术中心 | #27 | GET | `/api/v3/my/bookings/recent` | {} | 0 |
| 00:35:29.904 | 科学与艺术中心 | #32 | GET | `/api/v3/booking-status/overview` | {"day":"2026-10-03"} | 0 |
| 00:35:44.954 | 科学与艺术中心 | #25 | POST | `/api/v3/bookings` | {} | 0 |
| 00:35:46.254 | 科学与艺术中心 | #22 | GET | `/api/v3/booking-status/areas/VQyeEokNwJnq7h8sVwmnfg` | {"begin":"2026-10-03 09:00","end":"2026-10-03 14:00"} | 0 |
| 00:35:46.254 | 科学与艺术中心 | #23 | GET | `/api/v3/booking-status/overview` | {"day":"2026-10-03"} | 0 |
| 00:35:46.254 | 科学与艺术中心 | #24 | GET | `/api/v3/my/bookings/recent` | {} | 0 |
| 00:35:47.695 | 科学与艺术中心 | #17 | GET | `/api/v3/bookings/BOOKING_CS` | {} | 0 |
| 00:35:57.264 | 科学与艺术中心 | #3 | DELETE | `/api/v3/bookings/BOOKING_CS/cancel` | {} | 0 |
| 00:35:58.331 | 科学与艺术中心 | #2 | GET | `/api/v3/my/bookings/recent` | {} | 0 |
