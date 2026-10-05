# 测试与取证

> 返回 [项目 README](../README.md) · [文档索引](README.md)

本项目把捕获契约、离线实现与在线可用性分开验证。以下离线测试不访问 there、SSO 或企微。
真实网络验证需在可访问学校服务的环境，由用户使用本人账号执行。

## 离线单测

```bash
python tests/test_offline.py
```

测试围绕实际容易出错的契约：移动 HTML.sessionId 与 loginUser 的解析，Cookie 域 / 路径的保留，
`x-room-type` 与入口的匹配，九个业务接口的方法 / query / JSON 请求体，业务 code 与 HTTP 状态的区别，
完整座位对象和 profile 的创建数据依赖，以及敏感字段脱敏。

## 本地模拟全链路

```bash
python tests/test_e2e_mock.py
python tests/test_auth_mock.py
# 一次运行全部测试
python -m unittest discover -s tests -v
```

在 `requests.Session.send` 边界接管真实 PreparedRequest，提供合成响应及 Cookie，
并封锁 socket 连接。`test_auth_mock.py` 覆盖密码 / 短信 2FA / 企业微信扫码、本站预热、
授权与回调、四入口移动验证、凭据保存及 CLI 的只读 / dry-run 行为；
`test_e2e_mock.py` 覆盖四类资源的查询、创建、详情与取消 / 结束等数据依赖。
密码加密调用在集成夹具中用占位密文替代，未连接真实公钥服务。
模拟响应验证客户端组织请求及处理失败的方式，不替代真实服务验证。

本次 60 项离线测试全部通过（含超星签名向量、跨域换会话桥接与凭据导出、回调 http→https 升级与 /main 落地形态；Python 3.12+、requests 2.34.2）。
验证包括 HTTP 200 空回调
不会生成凭据、失败不覆盖旧凭据、外域回调不跟随、SSO 默认请求头不流入预约 API、
同一实例并发创建最多发送一次，以及创建超时 / 拒绝不自动重试。
机器可读结果见 [POC 校验报告](data/poc_validation.json)；
原始样本与规范的结构校验见 [OpenAPI 校验报告](data/openapi_validation.json)。

## 资料校验

[完整研究记录](research.md) 与 [证据说明](evidence.md) 保留上一阶段的校验结论：

| 项 | 校验内容 |
| :--- | :--- |
| HAR 来源 | 四个原始文件 SHA256 与原始 log.entries 下标 |
| 捕获样本 | 九十个业务响应、八个创建体与各自捕获 schema 一致 |
| OpenAPI | 3.1.1 格式、内部引用、路径参数与操作 ID；YAML / JSON 内容一致 |
| 资料范围 | 26 个明确方法操作；7 个方法未知的 URL 保存在扩展记录 |
| 隐私 | 文档与机器可读资料已对原 HAR 的个人及会话值做脱敏检查 |

机器可读证据位于 [data/](data/)，字段与例子位于 [api.md](api.md)，
资源快照仅来自四个选中区域，不能当作当前服务端占用数据。

## 在真实环境验证

先跑 `python login.py --check`，或完成登录后读取四种类型的 profile 与 overview；
只读结果确认当前身份、移动 sessionId 和场馆权限。
然后查询目标日期、区域与座位，使用 `book --dry-run` 检查请求体。
仅在确实要预约时删除 `--dry-run`。

创建后应核对返回的 bookingId、详情里的实际日期 / 时间与 `abilities`。
选择取消或提前结束后再次读取 recent；保留服务端返回状态，不能把 CANCEL 自动改写成 FINISHED。
业务 code 非 0 或网络中断时先核对 recent，避免重复创建。

真实取证可为命令加上 `--capture`，在项目 `captures/` 保存脱敏记录，用于补齐未捕获的协议行为。
签到只具有源码来源，应单独记录开放条件与实际返回；本项目没有宣称它已在真实服务上验证。

## 当前验证边界

本次开发环境无法访问目标域名，未输入真实密码、进行扫码或发送真实预约。
通过离线或模拟测试表示实现与现有资料一致；不表示未捕获接口在线可用，
也不表示登录与移动预约已经有一条完整连续 HAR。
