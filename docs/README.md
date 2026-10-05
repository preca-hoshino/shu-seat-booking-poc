# 文档索引

> 返回 [项目 README](../README.md)

| 文档 | 内容 |
| :--- | :--- |
| [login.md](login.md) | newsso 认证、二步验证、扫码、OAuth 授权、本站 Cookie 与移动 sessionId |
| [api.md](api.md) | 四系统覆盖、九个 HAR 业务端点、完整捕获字段与样例、区域规则、源码与 URL 记录 |
| [booking.md](booking.md) | 预约状态与数据依赖、一次完整预约设计、四段实测链、全部八次创建 |
| [cli.md](cli.md) | 认证与业务 CLI 参数、只读 / dry-run / 写操作的用法 |
| [testing.md](testing.md) | 离线契约测试、本地模拟全链路、真实环境验证方法 |
| [evidence.md](evidence.md) | 固定提交、HAR 哈希、来源层级、九十条请求时间线 |
| [research.md](research.md) | 本次研究的九章完整结论与时间线 |
| [openapi/there.openapi.yaml](openapi/there.openapi.yaml) | OpenAPI 3.1.1，26 个明确方法操作与 7 个方法未知 URL 条目 |
| [openapi/there.openapi.json](openapi/there.openapi.json) | 与 YAML 相同内容的 JSON 规范 |
| [data/api_catalog.json](data/api_catalog.json) | 九个端点、参数 / 返回字段、脱敏样例与 517 个座位快照 |
| [data/unified_api_evidence.json](data/unified_api_evidence.json) | 跨系统来源与端点证据汇总 |
| [data/login_chain_evidence.json](data/login_chain_evidence.json) | 固定 SSO 项目来源与离线会话关联证据 |
| [data/har_timeline.csv](data/har_timeline.csv) | 九十条请求的机器可读时间线（UTF-8 BOM） |
| [data/poc_validation.json](data/poc_validation.json) | 34 项离线测试、语法、文档链接及原 HAR 敏感值扫描结果 |
| [data/openapi_validation.json](data/openapi_validation.json) | OpenAPI 结构、引用、样例和 90 响应 / 8 创建体校验结果 |

## 阅读顺序

先从项目 README 的流程图与命令开始；需要确认请求形状时读 `api.md`，
排查登录时读 `login.md`，决定如何组织一次预约时读 `booking.md`。
完整字段与样本未缩减，长篇研究记录另外保留在 `research.md`。

## 来源层级

| 标记 / 情况 | 含义 |
| :--- | :--- |
| HAR 实际请求 | 已发生请求、响应与时间线；本文保留全部捕获字段的并集 |
| 脚本调用 | 捕获 JS 中明确写出的调用，尚无实际业务响应 |
| 固定项目源码 / 文档 | `shu-sso-poc` 的登录实现或 there 流程记录，本次未在线复核 |
| URL / 路径记录 | 仅知道 URL 或路径；未知方法、请求体、返回体继续标注未知 |

原始 HAR 含个人信息与会话，未随项目分发。`docs/data` 只携带已经脱敏的分析数据。
字段表表示“样本出现过”，不等于所有部署或场景必返。
