# there 四系统 API 与登录预约流程文档

四个移动入口共用 `https://there.shu.edu.cn/api/v3` 预约接口，通过 `x-room-type` 区分资源范围。本文集中列出四个系统的实测端点、参数、完整返回字段、脱敏样例、一次预约闭环设计，以及向 `newsso.shu.edu.cn` 登录后换取本站会话的流程。

抓包日期为 **2026-10-03，Asia/Shanghai**。本次分析读取桌面 shuyo 的四个 HAR 及其中 HTML/JS，并阅读指定项目的固定提交，未访问 there、SSO 或企业微信登录服务，也未执行 POC。HAR 从已登录状态开始；项目登录链与移动预约链的连接依据本站会话和页面引导，尚无一条包含登录全过程的连续 HAR。

文档只列明确来源的接口。没有来源的方法、参数、返回字段保留为未知。正文的流程设计是客户端组织方式，不能代替对服务端契约的验证。姓名、学号、联系方式、会话、授权码及签到令牌已脱敏；实际预约 ID 使用稳定别名，区域和座位资源 ID 保留。

[项目 README](../README.md) · [文档索引](README.md)

## 1 合并结论与四个系统的对应关系

四个入口具有同域名、同 `/api/v3` 路由、同用户 ID、机构 ID、角色集合、七类公共资源配置和相同请求封装。这些证据支持合并为同一预约 API 服务的四个资源范围；无法由抓包确定物理后端部署方式或所有范围之间的权限互通。

| 系统 | 移动页面 | x-room-type | HAR 总条数 | 业务 API 条数 | 预约结果 |
| --- | --- | --- | --- | --- | --- |
| 校本部图书馆 | `/mobile/libseat` | LIB_SEAT | 80 | 31 | 取消 |
| 24H学习空间 | `/mobile/seat2021` | STATION | 120 | 14 | 提前结束 |
| 延长智能中心 | `/mobile/seat-mgr` | SEAT | 77 | 18 | 取消 |
| 科学与艺术中心 | `/mobile/csseat` | CS_SEAT | 70 | 27 | 取消 |

共 347 条记录、25 个主机。there 主机 101 条，其中业务 API 90、页面 4、CONNECT 6、favicon 1。9 类业务 API 的 HTTP 状态全部为 200。8 次创建中 4 次成功、4 次业务拒绝；业务成败必须检查 JSON.code。CONNECT 的 status=0/time=-1 属隧道记录。

HTML 中资源类型共七项：ROOM 空间、SEAT 工位、SEAT2 环化学院工位、STATION 24小时座位、STATION2 办公室工位、LIB_SEAT 图书馆自修区、CS_SEAT 交流展示中心。只有四项实际用于本次请求，另外三项仅为页面配置，不据此增加入口或操作。

### 1.1 九个业务端点与四种资源的覆盖情况

| 方法 | 端点 | 合计 | 图书馆 | 24H | 延长 | 科艺 |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/api/v3/my/profile` | 4 | 1 | 1 | 1 | 1 |
| GET | `/api/v3/my/bookings/recent` | 16 | 5 | 3 | 3 | 5 |
| GET | `/api/v3/booking-status/overview` | 20 | 8 | 2 | 4 | 6 |
| GET | `/api/v3/booking-status/areas` | 10 | 3 | 1 | 3 | 3 |
| GET | `/api/v3/booking-status/areas/{areaId}` | 24 | 9 | 4 | 4 | 7 |
| POST | `/api/v3/bookings` | 8 | 3 | 1 | 1 | 3 |
| GET | `/api/v3/bookings/{bookingId}` | 4 | 1 | 1 | 1 | 1 |
| DELETE | `/api/v3/bookings/{bookingId}/cancel` | 3 | 1 | 0 | 1 | 1 |
| PUT | `/api/v3/bookings/{bookingId}/finish` | 1 | 0 | 1 | 0 | 0 |

图书馆、延长和科艺实际取消；24H 实际提前结束。四个前端脚本都声明 cancel 与 finish，因此“本次未调用”不能当作功能不存在，也不能作为跨类型调用权限已验证的依据。签到 `checkInUse` 仅有图书馆脚本调用证据，参数与响应另列在第 7 节。

## 2 会话来源与公共请求参数

### 2.1 there 业务请求头与 Cookie

| 位置 | 名称 | 捕获值或来源 | 说明 |
| --- | --- | --- | --- |
| header | x-hys-session | `<当前移动 HTML.sessionId>` | 90 次业务请求均等于相应入口页面 sessionId。 |
| cookie | SPHYS_SESSION | `<本站会话>` | 业务请求均携带，保持 Cookie jar 的域、路径与更新。 |
| cookie | authenticityToken | `<本站 CSRF Cookie>` | 项目描述为 CSRF Cookie；服务端强制校验策略未知。 |
| cookie | HYS_LANG | zh | 语言 Cookie。 |
| header | x-room-type | LIB_SEAT / STATION / SEAT / CS_SEAT | 由当前入口决定。 |
| header | x-hys-platform | UNDEFINE | 保留捕获拼写；HTML.apiPlatform=WXCP 不是此头的值。 |
| header | x-lang | zh | 公共客户端从登录用户语言读取。 |
| header | Content-Type | application/json | 捕获的 GET 也携带。 |
| header | X-Requested-With | com.tencent.wework | 捕获于企微环境，服务端必需性未知。 |
| header | Referer | 当前移动页面绝对 URL | 与四入口对应。 |
| header | Origin | https://there.shu.edu.cn | 创建、取消、结束请求实际携带，浏览器自行控制。 |

抓包没有 Authorization Bearer。以上是成功捕获请求的携带组合，未经删字段测试，不能宣称某字段可省略或单独足够。四段的会话与 authenticityToken 值不同，不能假定互换。当前入口的页面与 API 请求应使用同一 Cookie jar 和该页面产生的 sessionId。

### 2.2 SSO 与本站的凭据分工

| 对象 | 来源与作用 | 关系 |
| --- | --- | --- |
| SHU_OAUTH2 | newsso 的 SSO Cookie | 认证阶段生成，用于 SSO 授权；不等于本站 Cookie。 |
| OAuth code | /oauth/authorize 的 Location | 传给 there/login-oauth2，按本次授权结果使用。 |
| SPHYS_SESSION | there 回调写入或更新 | 项目描述其中携带 utoken。 |
| authenticityToken | there 回调下发 | 本站 Cookie，不与 SHU_OAUTH2 混用。 |
| authJump | there 成功落地 /web 的查询参数 | 不是 API 的 x-hys-session。 |
| HTML.sessionId | /mobile/* 的页面引导数据 | 是业务头 x-hys-session 的来源。 |

离线检查显示，90 次请求的 SPHYS_SESSION 中 utoken 和 x-hys-session 均为声明 HS512、DEF 压缩的 JWT 形状；解码字段名为 sub/aud/exp，两者 sub 均对应 profile.data.id，但令牌字符串不同。本次没有验证签名、输出实际 claims 或调用令牌。该关系支持同用户关联，不能把 utoken 直接填到 x-hys-session。

已捕获的 JS 分块包含公共 HTTP 客户端模块，可核对请求头、401 跳登录等行为；主 app.js 的响应正文缺失，因此无法恢复全部页面交互。

## 3 如何向 newsso 登录并换取 there 会话

以下方法和字段来自 shu-sso-poc 固定提交 `941c7d5ea876c3b511f1bf9a8862b0cf91df9c3b`，不是本次 HAR 实测的 SSO 契约。所列 JSON 字段是项目客户端提交或消费的结构；登录接口的完整原始响应和实际 HTTP 状态未提供。[systems/there.shu.edu.cn/README.md](https://github.com/preca-hoshino/shu-sso-poc/blob/941c7d5ea876c3b511f1bf9a8862b0cf91df9c3b/systems/there.shu.edu.cn/README.md)、[src/client.py](https://github.com/preca-hoshino/shu-sso-poc/blob/941c7d5ea876c3b511f1bf9a8862b0cf91df9c3b/src/client.py)。

### 3.1 there 的 OAuth 配置与初始化

| 参数 | 项目配置 |
| --- | --- |
| client_id | `eDrd-M0i0WoSWRxk7ShDC1n-fbS7jRvi` |
| redirect_uri | `https://there.shu.edu.cn/login-oauth2` |
| scope | 字符串 `1`，项目要求原样携带。 |
| response_type | `code` |
| 本站初始化入口 | `GET https://there.shu.edu.cn/login?from=web` |
| 项目密码及授权服务 | `https://newsso.shu.edu.cn` |
| 本站初始化 Location 的授权主机 | `https://oauth.shu.edu.cn` |

先访问本站初始化入口，保留 Set-Cookie 的 SPHYS_SESSION 与 Location 中的授权上下文/state。项目说明此步骤用于预置本站会话。另一入口为不带 code 的 GET /login-oauth2，可跳到授权地址。newsso 与 oauth 的协议互通是项目依据前端产物及成功流程给出的报告；SHU_OAUTH2 是 host-scoped，应按真实 Cookie 域发送，不能把 newsso Cookie 人为复制为 oauth Cookie。

项目记录过成功回调不含 state；本文只保留这个观察，不据此认定所有分支都可忽略关联上下文。初始化得到的 state 按对应授权流程保存和传递；密码 params 及企微回调 state 是另一层编码上下文，见下文。

### 3.2 密码分支的请求和二步验证

取得当期 newsso 公钥：GET `/oauth2/login/` → 页面引用的版本化 preload_helper/umi 脚本 → 对应登录 chunk `p__oauth2__login__index.<hash>.async.js` → 公钥 PEM。项目通过该公钥执行 RSA PKCS#1 v1.5 加密，再对密文做标准 Base64。公钥及脚本 hash 随部署变化，本文不固定一个回退密钥作为现行密钥。[src/rsa_key.py](https://github.com/preca-hoshino/shu-sso-poc/blob/941c7d5ea876c3b511f1bf9a8862b0cf91df9c3b/src/rsa_key.py)、[src/utils.py](https://github.com/preca-hoshino/shu-sso-poc/blob/941c7d5ea876c3b511f1bf9a8862b0cf91df9c3b/src/utils.py)。

`params` 的解码对象使用 camelCase；将紧凑 JSON 的 UTF-8 字节做 URL-safe Base64，删除末尾 `=`。项目 runner 的 session_params 可选择任一系统上下文；下面使用 there 配置展示。此参数是顶层登录 JSON 中的一条编码字符串。

```json
{
  "responseType": "code",
  "clientId": "eDrd-M0i0WoSWRxk7ShDC1n-fbS7jRvi",
  "clientName": "空间预约管理系统",
  "scope": "1",
  "redirectUri": "https://there.shu.edu.cn/login-oauth2",
  "state": ""
}
```

上例 state 空字符串是 runner.session_params 的源码行为；不应把它当作覆盖本站初始化 state 的指令。授权 GET 使用初始化的对应上下文。[src/runner.py](https://github.com/preca-hoshino/shu-sso-poc/blob/941c7d5ea876c3b511f1bf9a8862b0cf91df9c3b/src/runner.py#L24)。

**POST https://newsso.shu.edu.cn/oauth/userLogin**，Content-Type 为 application/json。项目客户端同时生成 UUID 类型的 `Request-Id` 头，是否为服务端必需条件未知。

| JSON 字段 | 类型 | 内容与来源 |
| --- | --- | --- |
| username | string | 用户本人提供的学号或工号。 |
| password | string | RSA PKCS#1 v1.5 加密密码的 Base64 密文。 |
| tenantId | string | 项目默认值为上海大学。 |
| params | string | 上述 OAuth 上下文的 base64url，无等号填充；项目明确提示缺失会 badRequestParams。 |

```json
{
  "username": "<本人学号或工号>",
  "password": "<Base64 RSA ciphertext>",
  "tenantId": "上海大学",
  "params": "<base64url encoded OAuth context without padding>"
}
```

项目按响应 `message == "success"` 判断该步骤成功。若 `twoStepRequired == true`，先读取 `twoStepMethods` 可用方式；项目使用 sms 或 wecom。`twoStepMethods` 内部结构与完整响应未知，不能固定为仅两种方式。

| 消费的返回字段 | 源码所期望的类型 | 用途 |
| --- | --- | --- |
| message | string | success 时继续，其他值停止认证。 |
| twoStepRequired | boolean | 决定是否执行二步。 |
| twoStepMethods | object | 从其键选可用 method；值结构未知。 |

**POST https://newsso.shu.edu.cn/oauth/twoStep/send** 使用同一会话 jar 和登录待验证上下文，JSON 为 `{"method":"<选定方式>"}`；项目要求返回 message=success。待验证上下文的实际 Cookie 名称未提供，不能提前要求它已有完整 SHU_OAUTH2。

**POST https://newsso.shu.edu.cn/oauth/twoStep/verify** 使用同一会话，提交以下字段；password 仍为加密密文，code 是用户收到的二步验证码。项目检查 message=success 后进入授权。[src/entry_password.py](https://github.com/preca-hoshino/shu-sso-poc/blob/941c7d5ea876c3b511f1bf9a8862b0cf91df9c3b/src/entry_password.py#L50)。

```json
{
  "username": "<本人学号或工号>",
  "password": "<Base64 RSA ciphertext>",
  "tenantId": "上海大学",
  "params": "<same encoded OAuth context>",
  "code": "<用户收到的二步验证码>",
  "method": "<twoStepMethods 中选定方式>"
}
```

密码分支成功或二步成功后，项目描述建立 SHU_OAUTH2。密码分支与扫码分支均要由用户完成认证/确认；本文没有执行任何登录。

### 3.3 企微扫码分支

该分支在企微外部域名建立确认结果，再由 newsso 换成 SSO 会话。参数是项目代码常量，非用户会话秘密。[src/config.py](https://github.com/preca-hoshino/shu-sso-poc/blob/941c7d5ea876c3b511f1bf9a8862b0cf91df9c3b/src/config.py#L16)、[src/client.py](https://github.com/preca-hoshino/shu-sso-poc/blob/941c7d5ea876c3b511f1bf9a8862b0cf91df9c3b/src/client.py#L172)。

| 步骤与方法 | 主机与端点 | 实际源码参数 | 返回形式或消费字段 |
| --- | --- | --- | --- |
| 扫码页面 GET | `open.work.weixin.qq.com/wwopen/sso/qrConnect` | appid=wxa8dea949443de641；agentid=1000059；redirect_uri=https://newsso.shu.edu.cn/oauth/wecom/qrcode；state=编码上下文；lang=zh；version=1.2.7；login_type=jssdk | HTML 中提取 qrImg?key=... 的 key。 |
| POC 轮询 GET | `open.work.weixin.qq.com/wwopen/sso/l/qrConnect` | callback=jsonpCallback；key；redirect_uri；appid；_=毫秒时间戳 | JSONP，消费 status、auth_code。 |
| 浏览器轮询 POST | `open.work.weixin.qq.com/wwopen/sso/lp/qrConnect` | 项目 there README 只记载方法与 URL；请求体未知 | 真实浏览器流程报告，响应体未提供。 |
| newsso 回调 GET | `newsso.shu.edu.cn/oauth/wecom/qrcode` | code=企微 auth_code；state=编码上下文；appid=wxa8dea949443de641 | 项目报告更新 SHU_OAUTH2 后继续授权；源码判断错误跳转/正文。 |

POC 轮询头为 Referer=https://open.work.weixin.qq.com/wwopen/sso/qrConnect、Origin=https://open.work.weixin.qq.com、x-requested-with=XMLHttpRequest、Accept 为 JavaScript 类型。这些头与 there 业务 WebView 的捕获值不同，分别按当前服务管理。POST /lp 的载荷未知，不能复制 GET /l 的查询字段当作已验证请求体。

JSONP 状态在源码中包括 QRCODE_SCAN_NEVER、QRCODE_SCAN_ING、QRCODE_SCAN_SUCC、QRCODE_SCAN_ERR、QRCODE_SCAN_OVERDUE、QRCODE_SCAN_CANCEL。SUCC 且 auth_code 有值后继续；错误、过期、取消停止。下面仅展示源码期望结构，没有原始响应样本：

```javascript
jsonpCallback({"status":"QRCODE_SCAN_SUCC","auth_code":"<企微确认码>"})
```

newsso 回调必须传 appid 是项目源码注释与错误处理给出的要求；缺失会 badRequestParams。源码也将 Location 中 message=wecomAuthFailed 视为失败。企微 auth_code 不是下一步 OAuth code，也不是二步验证码。

项目构造二维码图片 `/wwopen/sso/qrImg?key=...` 和确认页 `/wwopen/sso/confirm2?k=...&notretry=yes` URL，没有请求或返回样本，放在第 7 节来源记录中。

### 3.4 授权与 there 回调

已有可用 newsso SSO 会话后，项目使用 **GET https://newsso.shu.edu.cn/oauth/authorize**，禁止自动跟随时可从 Location 取出回调 code。本站入口 Location 中的 oauth.shu.edu.cn 同名路径是另一个被项目记载的主机分支。

| query 参数 | 值或来源 | 说明 |
| --- | --- | --- |
| response_type | code | 注意这里为 snake_case。 |
| client_id | eDrd-M0i0WoSWRxk7ShDC1n-fbS7jRvi | there 应用公开标识。 |
| redirect_uri | https://there.shu.edu.cn/login-oauth2 | 以查询参数方式编码。 |
| scope | 1 | 保留项目要求的值。 |
| state | 初始化对应上下文 | 项目源码为空时不发此项；按当前流程保存和关联。 |

```http
GET https://newsso.shu.edu.cn/oauth/authorize?response_type=code&client_id=eDrd-M0i0WoSWRxk7ShDC1n-fbS7jRvi&redirect_uri=https%3A%2F%2Fthere.shu.edu.cn%2Flogin-oauth2&scope=1&state=<URL-encoded-context>
```

授权成功返回 302 Location 指向 there/login-oauth2 并携带 code。若 Location 包含 /oauth2/login/，项目视为 SSO 会话不可用。302 本身不是授权成功标志，应检查回调目标和 code。

沿返回的回调地址访问 **GET there/login-oauth2?code=...**，并使用已初始化的本站 Cookie jar。项目描述成功时更新 SPHYS_SESSION/authenticityToken，302 到 `/web?authJump=...`，之后 307→200，SPA 导航 `/web/home`。这些页面不返回预约 API 的 JSON envelope。

| 本站路由 | 参数 | 项目记录的返回 |
| --- | --- | --- |
| GET /login | from=web | 302 至 SSO 授权，并预置本站会话 Cookie。 |
| GET /login-oauth2 | 入口可不带 code；回调带 code，state 取对应上下文 | 成功回调 302 至 /web；坏 code 一种表现为 HTTP 200 空正文。 |
| GET /web | authJump，值来自回调 Location | 成功落地链 307→200 HTML；未登录 Web 入口可转 /login?from=web。 |

登录完成判据设计：先核对回调落地 /web 与页面特征，再进入选定移动页面获取登录用户/sessionId，最后用 profile.code=0 且非匿名的用户信息确认业务会话。/shu、/shu/booking.html、/shu/rule.html 是项目所述公开介绍页，不作为登录成功判据。仅 HTTP 200 或仅 URL 含 there 域名都不足以排除空回调失败。

项目描述本站后端用授权码换 token，但没有给出其实际内部请求、client secret 和完整响应。本文不提供一个前端 token 交换契约。授权码长度、authJump 长度只为项目所述样本，未固定成格式限制。

### 3.5 登录到移动预约的接点

本站会话建立后选择四入口之一，从其 HTML 的 loginUser/sessionId 引导数据取得当前身份与业务会话值，随后按第 2 节发送 API。四个入口返回的 HTML 均有这些数据，且 x-hys-session 与各自 sessionId 一致。每个入口首次未登录的实际跳转分支尚未捕获；此接点是项目与 HAR 的证据拼接。

![登录到预约流程](assets/login-to-booking.svg)

## 4 九个实测业务 API 的端点 参数与返回体

本节基地址统一为 `https://there.shu.edu.cn`，所有接口携带第 2 节公共参数。参数表中的“实际传入”是抓包事实，未测试服务端最低必填集合。路径变量必须有具体值。返回字段表为该端点全部捕获响应的字段并集，保留对象与数组层级；没有将样本字段声明为服务器永远必返，也没有把样本值封闭为 enum。

本节样例从原 HAR 取出并脱敏，保留对象的所有字段；为阅读压缩对象数组为首项，原始数组长度不受影响，字段表仍基于全部样本。单个样例不能代表四系统全部字段，完整结构以字段表为准。提示字段名称、HTTP 200 与 JSON.code 组合均按抓包保留。

### 4.1 当前用户

**GET `/api/v3/my/profile`**。初始化用户；创建请求的 subject 和 meetingMembers 分别来自 data.name、data.id。 本次调用 4 次，HTTP 状态 200，JSON.code 捕获值 0。

本次没有查询参数。

**完整捕获返回字段**

| JSON 字段路径 | 捕获类型 | 说明 |
| --- | --- | --- |
| `code` | `integer` | HAR：0 为业务成功，200 为业务拒绝；与 HTTP 状态码不同。 |
| `data` | `object` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.id` | `string` | profile 时是用户 ID；区域详情时是 areaId；预约详情时是 bookingId。 |
| `data.loginName` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.name` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.namePinyin` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.jobNumber` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.cardNo` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.nickName` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.sex` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.headImgUrl` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.mobile` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.position` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.deptId` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.deptName` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.corp` | `object` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.corp.id` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.corp.name` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.corp.meetingRoomCount` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.corp.abilities` | `array<unknown>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.corpName` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.roles` | `array<string>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.status` | `string` | OPEN 不等于已签到；finish 后捕获状态也可为 CANCEL。 |
| `data.statusLabel` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.deptIds` | `array<string>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.depts` | `array<object>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.depts[]` | `object` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.depts[].id` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.depts[].name` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.depts[].shortName` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.depts[].fullName` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.depts[].parentId` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.depts[].parentName` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.depts[].showOrder` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.depts[].labelName` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.depts[].userCount` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.depts[].userCountWithNew` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.depts[].upstreamId` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.depts[].isSett` | `boolean` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.isAnonymous` | `boolean` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.disableBooking` | `boolean` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.defaultArea` | `object` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.defaultArea.id` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.defaultArea.name` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.defaultArea.level` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.defaultArea.shortName` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.defaultArea.supportRoomTypes` | `array<string>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.defaultArea.validRoomCount` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.defaultArea.abilities` | `array<unknown>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.officeAreaResponse` | `object` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.officeAreaResponse.id` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.officeAreaResponse.name` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.officeAreaResponse.level` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.officeAreaResponse.shortName` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.officeAreaResponse.supportRoomTypes` | `array<string>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.officeAreaResponse.validRoomCount` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.officeAreaResponse.abilities` | `array<unknown>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.permissions` | `array<string>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.receiveMeetingMail` | `boolean` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.receiveNotify` | `boolean` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.upstreamId` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.createdAt` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.updatedAt` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.isAdmin` | `boolean` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.abilities` | `array<string>` | 详情的操作能力，例如 cancel、waitOpen、close；不能用状态字段单独替代。 |

**校本部图书馆返回样例**，校本部图书馆预约.har#68，00:25:31.686，HTTP 200 / JSON.code=0。

```json
{
  "code": 0,
  "data": {
    "id": "<profile.data.id>",
    "loginName": "<redacted>",
    "name": "<profile.data.name>",
    "namePinyin": "<redacted>",
    "jobNumber": "<redacted>",
    "cardNo": "<redacted>",
    "nickName": "<redacted>",
    "sex": "MALE",
    "headImgUrl": "<redacted>",
    "mobile": "<redacted>",
    "position": "",
    "deptId": "<redacted>",
    "deptName": "<redacted>",
    "corp": {
      "id": "<corp.id>",
      "name": "上海大学",
      "meetingRoomCount": 300,
      "abilities": []
    },
    "corpName": "上海大学",
    "roles": [
      "3Y1Uhmq7nSK"
    ],
    "status": "ACTIVE",
    "statusLabel": "已激活",
    "deptIds": [
      "<redacted>"
    ],
    "depts": [
      {
        "id": "<redacted>",
        "name": "<redacted>",
        "shortName": "<redacted>",
        "fullName": "<redacted>",
        "parentId": "<redacted>",
        "parentName": "院系",
        "showOrder": 550055767,
        "labelName": "<redacted>",
        "userCount": 7328,
        "userCountWithNew": 7328,
        "upstreamId": "<redacted>",
        "isSett": true
      }
    ],
    "isAnonymous": false,
    "disableBooking": false,
    "defaultArea": {
      "id": "all",
      "name": "所有区域",
      "level": "FLOOR",
      "shortName": "所有区域",
      "supportRoomTypes": [
        "ROOM"
      ],
      "validRoomCount": 0,
      "abilities": []
    },
    "officeAreaResponse": {
      "id": "all",
      "name": "所有区域",
      "level": "FLOOR",
      "shortName": "所有区域",
      "supportRoomTypes": [
        "ROOM"
      ],
      "validRoomCount": 0,
      "abilities": []
    },
    "permissions": [
      "dashboard",
      "corp.setting",
      "corp.dept",
      "corp.employee",
      "profile"
    ],
    "receiveMeetingMail": true,
    "receiveNotify": true,
    "upstreamId": "<redacted>",
    "createdAt": "2025-08-26 02:09:14",
    "updatedAt": "2026-09-25 02:07:13",
    "isAdmin": false,
    "abilities": [
      "fromUpstream"
    ]
  }
}
```

来源：校本部图书馆预约.har#68、24H学习空间预约.har#36、延长智能中心预约.har#63、科学与艺术中心预约.har#62。

### 4.2 最近预约

**GET `/api/v3/my/bookings/recent`**。初始、创建后、取消或结束后刷新；列表含已取消记录，不能把非空列表直接当作当前有效预约。 本次调用 16 次，HTTP 状态 200，JSON.code 捕获值 0。

本次没有查询参数。

**完整捕获返回字段**

| JSON 字段路径 | 捕获类型 | 说明 |
| --- | --- | --- |
| `code` | `integer` | HAR：0 为业务成功，200 为业务拒绝；与 HTTP 状态码不同。 |
| `data` | `array<object>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[]` | `object` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].id` | `string` | recent/创建响应时是 bookingId；区域列表时是 areaId。 |
| `data[].subject` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].ownerId` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].ownerName` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].ownerMobile` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].ownerPhone` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].ownerPosition` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].ownerDeptId` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].clientType` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].meetingInfra` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].ownerUpStreamId` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].ownerUpstreamId` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].ownerDeptName` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].ownerJobNumber` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].ownerUserNamePinYin` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingUserId` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingUsernamePinYin` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingUserUpStreamId` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingUserName` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingUserShowName` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].beginTime` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].endTime` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].duration` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].roomId` | `string` | 座位资源 ID，不是预约 ID。 |
| `data[].roomName` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].officeAreaId` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].officeAreaName` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].allOfficeAreaName` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].roomNeedApproved` | `boolean` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].templateType` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].receptionId` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].receptionName` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].receptionMobile` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].memberNumbers` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].customFormIds` | `array<unknown>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].roomType` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].status` | `string` | recent 可含 CANCEL 历史记录，非空不等于存在有效预约。 |
| `data[].workflow` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].statusLabel` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].needCheckin` | `boolean` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].checkedStatus` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].meetingRepeatType` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].meetingType` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].busyCssName` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].createdAt` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].updatedAt` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].beforeNotify` | `boolean` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].facilityNames` | `array<unknown>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].abilities` | `array<string>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].origEndAt` | `string` | 提前结束后保留原结束时间。 |

**校本部图书馆返回样例**，校本部图书馆预约.har#4，00:26:47.377，HTTP 200 / JSON.code=0。

```json
{
  "code": 0,
  "data": [
    {
      "id": "BOOKING_LIB",
      "subject": "<profile.data.name>",
      "ownerId": "<profile.data.id>",
      "ownerName": "<profile.data.name>",
      "ownerMobile": "<redacted>",
      "ownerPhone": "<redacted>",
      "ownerPosition": "",
      "ownerDeptId": "<redacted>",
      "clientType": "SYS",
      "meetingInfra": "",
      "ownerUpStreamId": "<redacted>",
      "ownerUpstreamId": "<redacted>",
      "ownerDeptName": "<redacted>",
      "ownerJobNumber": "<redacted>",
      "ownerUserNamePinYin": "<redacted>",
      "bookingUserId": "<profile.data.id>",
      "bookingUsernamePinYin": "<redacted>",
      "bookingUserUpStreamId": "<redacted>",
      "bookingUserName": "<profile.data.name>",
      "bookingUserShowName": "<profile.data.name>",
      "beginTime": "2026-10-03 08:30:00",
      "endTime": "2026-10-03 09:30:00",
      "duration": 60,
      "roomId": "2RLARqe9egAFzej4ALBizj",
      "roomName": "2E015",
      "officeAreaId": "KRdcGiyK99gzrqCepi91Cv",
      "officeAreaName": "二楼东侧",
      "allOfficeAreaName": "校本部图书馆自修区-二楼东侧",
      "roomNeedApproved": false,
      "templateType": "",
      "receptionId": "",
      "receptionName": "",
      "receptionMobile": "",
      "memberNumbers": 1,
      "customFormIds": [],
      "roomType": "LIB_SEAT",
      "status": "CANCEL",
      "workflow": "STAND",
      "statusLabel": "已取消",
      "needCheckin": true,
      "checkedStatus": "N",
      "meetingRepeatType": "NONE",
      "meetingType": "STANDARD",
      "busyCssName": "busy busy-for-me",
      "createdAt": "2026-10-03 00:26:33",
      "updatedAt": "2026-10-03 00:26:46",
      "beforeNotify": false,
      "facilityNames": [],
      "abilities": []
    }
  ]
}
```

**24H学习空间返回样例**，24H学习空间预约.har#1，00:32:36.707，HTTP 200 / JSON.code=0。

```json
{
  "code": 0,
  "data": [
    {
      "id": "BOOKING_STATION",
      "subject": "<profile.data.name>",
      "ownerId": "<profile.data.id>",
      "ownerName": "<profile.data.name>",
      "ownerMobile": "<redacted>",
      "ownerPhone": "<redacted>",
      "ownerPosition": "",
      "ownerDeptId": "<redacted>",
      "clientType": "SYS",
      "meetingInfra": "",
      "ownerUpStreamId": "<redacted>",
      "ownerUpstreamId": "<redacted>",
      "ownerDeptName": "<redacted>",
      "ownerJobNumber": "<redacted>",
      "ownerUserNamePinYin": "<redacted>",
      "bookingUserId": "<profile.data.id>",
      "bookingUsernamePinYin": "<redacted>",
      "bookingUserUpStreamId": "<redacted>",
      "bookingUserName": "<profile.data.name>",
      "bookingUserShowName": "<profile.data.name>",
      "beginTime": "2026-10-03 00:33:00",
      "endTime": "2026-10-03 00:33:00",
      "origEndAt": "2026-10-03 01:30:00",
      "duration": 0,
      "roomId": "4q4z61HkGbJZnK89ejv9wU",
      "roomName": "B-034",
      "officeAreaId": "DsNjTXf8icSMh3SXB5HPge",
      "officeAreaName": "B",
      "allOfficeAreaName": "图书馆24小时自习区-B",
      "roomNeedApproved": false,
      "templateType": "",
      "receptionId": "",
      "receptionName": "",
      "receptionMobile": "",
      "memberNumbers": 1,
      "customFormIds": [],
      "roomType": "STATION",
      "status": "CANCEL",
      "workflow": "STAND",
      "statusLabel": "已取消",
      "needCheckin": true,
      "checkedStatus": "N",
      "meetingRepeatType": "NONE",
      "meetingType": "STANDARD",
      "busyCssName": "busy busy-for-me",
      "createdAt": "2026-10-03 00:32:26",
      "updatedAt": "2026-10-03 00:32:36",
      "beforeNotify": false,
      "facilityNames": [],
      "abilities": []
    }
  ]
}
```

**延长智能中心返回样例**，延长智能中心预约.har#2，00:34:26.686，HTTP 200 / JSON.code=0。

```json
{
  "code": 0,
  "data": [
    {
      "id": "BOOKING_SEAT",
      "subject": "<redacted>",
      "ownerId": "<profile.data.id>",
      "ownerName": "<profile.data.name>",
      "ownerMobile": "<redacted>",
      "ownerPhone": "<redacted>",
      "ownerPosition": "",
      "ownerDeptId": "<redacted>",
      "clientType": "SYS",
      "meetingInfra": "",
      "ownerUpStreamId": "<redacted>",
      "ownerUpstreamId": "<redacted>",
      "ownerDeptName": "<redacted>",
      "ownerJobNumber": "<redacted>",
      "ownerUserNamePinYin": "<redacted>",
      "bookingUserId": "<profile.data.id>",
      "bookingUsernamePinYin": "<redacted>",
      "bookingUserUpStreamId": "<redacted>",
      "bookingUserName": "<profile.data.name>",
      "bookingUserShowName": "<profile.data.name>",
      "beginTime": "2026-10-03 09:30:00",
      "endTime": "2026-10-03 10:30:00",
      "duration": 60,
      "roomId": "FLiAcmbCuHCEkRu5SH1rhX",
      "roomName": "11-3",
      "officeAreaId": "KbuCBLACKv74KmiBqE51z6",
      "officeAreaName": "B",
      "allOfficeAreaName": "智能信息中心智慧共享空间-B",
      "roomNeedApproved": false,
      "templateType": "",
      "receptionId": "",
      "receptionName": "",
      "receptionMobile": "",
      "memberNumbers": 1,
      "customFormIds": [],
      "roomType": "SEAT",
      "status": "CANCEL",
      "workflow": "STAND",
      "statusLabel": "已取消",
      "needCheckin": true,
      "checkedStatus": "N",
      "meetingRepeatType": "NONE",
      "meetingType": "STANDARD",
      "busyCssName": "busy busy-for-me",
      "createdAt": "2026-10-03 00:34:07",
      "updatedAt": "2026-10-03 00:34:26",
      "beforeNotify": false,
      "facilityNames": [],
      "abilities": []
    }
  ]
}
```

**科学与艺术中心返回样例**，科学与艺术中心预约.har#2，00:35:58.331，HTTP 200 / JSON.code=0。

```json
{
  "code": 0,
  "data": [
    {
      "id": "BOOKING_CS",
      "subject": "<profile.data.name>",
      "ownerId": "<profile.data.id>",
      "ownerName": "<profile.data.name>",
      "ownerMobile": "<redacted>",
      "ownerPhone": "<redacted>",
      "ownerPosition": "",
      "ownerDeptId": "<redacted>",
      "clientType": "SYS",
      "meetingInfra": "",
      "ownerUpStreamId": "<redacted>",
      "ownerUpstreamId": "<redacted>",
      "ownerDeptName": "<redacted>",
      "ownerJobNumber": "<redacted>",
      "ownerUserNamePinYin": "<redacted>",
      "bookingUserId": "<profile.data.id>",
      "bookingUsernamePinYin": "<redacted>",
      "bookingUserUpStreamId": "<redacted>",
      "bookingUserName": "<profile.data.name>",
      "bookingUserShowName": "<profile.data.name>",
      "beginTime": "2026-10-03 09:00:00",
      "endTime": "2026-10-03 14:00:00",
      "duration": 300,
      "roomId": "ECsWTCtuEoMSq9DqD8ZAPV",
      "roomName": "A-27",
      "officeAreaId": "VQyeEokNwJnq7h8sVwmnfg",
      "officeAreaName": "学生共享创作中心A",
      "allOfficeAreaName": "科学与艺术中心-学生共享创作中心A",
      "roomNeedApproved": false,
      "templateType": "",
      "receptionId": "",
      "receptionName": "",
      "receptionMobile": "",
      "memberNumbers": 1,
      "customFormIds": [],
      "roomType": "CS_SEAT",
      "status": "CANCEL",
      "workflow": "STAND",
      "statusLabel": "已取消",
      "needCheckin": true,
      "checkedStatus": "N",
      "meetingRepeatType": "NONE",
      "meetingType": "STANDARD",
      "busyCssName": "busy busy-for-me",
      "createdAt": "2026-10-03 00:35:46",
      "updatedAt": "2026-10-03 00:35:58",
      "beforeNotify": false,
      "facilityNames": [],
      "abilities": []
    }
  ]
}
```

来源：校本部图书馆预约.har#66、校本部图书馆预约.har#38、校本部图书馆预约.har#33、校本部图书馆预约.har#17、校本部图书馆预约.har#4、24H学习空间预约.har#35、24H学习空间预约.har#13、24H学习空间预约.har#1、延长智能中心预约.har#64、延长智能中心预约.har#25、延长智能中心预约.har#2、科学与艺术中心预约.har#60、科学与艺术中心预约.har#33、科学与艺术中心预约.har#27、科学与艺术中心预约.har#24、科学与艺术中心预约.har#2。

### 4.3 日期概览

**GET `/api/v3/booking-status/overview`**。提供日期概览；overview 的通用配置可与实际区域配置不同。 本次调用 20 次，HTTP 状态 200，JSON.code 捕获值 0。

| 位置 | 参数 | 类型 | 值或格式 | 来源与说明 |
| --- | --- | --- | --- | --- |
| query | `day` | string | 2026-10-03 | 捕获格式 YYYY-MM-DD；每次 overview 调用均携带，省略行为未验证。 |

**完整捕获返回字段**

| JSON 字段路径 | 捕获类型 | 说明 |
| --- | --- | --- |
| `code` | `integer` | HAR：0 为业务成功，200 为业务拒绝；与 HTTP 状态码不同。 |
| `data` | `object` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.currentOfficeArea` | `object` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.currentOfficeArea.id` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.currentOfficeArea.name` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.currentOfficeArea.shortName` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.currentOfficeArea.supportRoomTypes` | `array<string>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.currentOfficeArea.abilities` | `array<unknown>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes` | `object` | 当前响应的时间配置；须区分概览通用配置和选中区域配置。 |
| `data.bookingTimes.timeBlockType` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.startHour` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.endHour` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.morningEndHour` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.afternoonStartHour` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.maxDuration` | `integer` | 本次按分钟使用；所选四区域均为 480。 |
| `data.bookingTimes.configMaxDuration` | `integer` | 本次按分钟使用；所选四区域均为 480。 |
| `data.bookingTimes.meetingInterval` | `integer` | 本次按分钟使用，四区域分别为 30、30、15、60。 |
| `data.bookingTimes.bookingLimitDays` | `integer` | 不要直接用该数值截断 bookingDays；样本存在差异。 |
| `data.bookingTimes.meetingHalfHours` | `array<string>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.timeBlocks` | `array<object>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.timeBlocks[]` | `object` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.timeBlocks[].key` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.timeBlocks[].start` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.timeBlocks[].end` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.timeBlocks[].startMinutes` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.timeBlocks[].endMinutes` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.allMeetingDurations` | `array<object>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.allMeetingDurations[]` | `object` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.allMeetingDurations[].name` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.allMeetingDurations[].value` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.allWeekDays` | `array<object>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.allWeekDays[]` | `object` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.allWeekDays[].name` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.allWeekDays[].value` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.meetingRepeatTypes` | `array<string>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.needCheckin` | `boolean` | 四区域均为 true；实际签到请求未捕获。 |
| `data.bookingTimes.disablePersonConflict` | `boolean` | 24H 为 true，其余 false；没有验证具体冲突校验效果。 |
| `data.bookingTimes.enableFixedBooking` | `boolean` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.enableAgentBooking` | `boolean` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingDays` | `array<object>` | 捕获的候选日期数组，不等同于服务端准入边界。 |
| `data.bookingDays[]` | `object` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingDays[].day` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingDays[].workDay` | `boolean` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingDays[].lawDay` | `boolean` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingDays[].weekDay` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingDays[].meetingCount` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingDays[].roomCount` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingDays[].bookingRoomCount` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingDays[].bookingRate` | `number` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingDays[].meetingMinutes` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingDays[].rooms` | `array<unknown>` | 捕获字段；未验证其在全部场景是否必返。 |

**校本部图书馆返回样例**，校本部图书馆预约.har#14，00:26:33.236，HTTP 200 / JSON.code=0。

```json
{
  "code": 0,
  "data": {
    "currentOfficeArea": {
      "id": "all",
      "name": "所有区域",
      "shortName": "所有区域",
      "supportRoomTypes": [
        "ROOM"
      ],
      "abilities": []
    },
    "bookingTimes": {
      "timeBlockType": "FIXED_BLOCK",
      "startHour": 9,
      "endHour": 18,
      "morningEndHour": 12,
      "afternoonStartHour": 12,
      "maxDuration": 480,
      "configMaxDuration": 480,
      "meetingInterval": 15,
      "bookingLimitDays": 365,
      "meetingHalfHours": [
        "09:00",
        "09:15",
        "09:30",
        "09:45",
        "10:00",
        "10:15",
        "10:30",
        "10:45",
        "11:00",
        "11:15",
        "11:30",
        "11:45",
        "12:00",
        "12:15",
        "12:30",
        "12:45",
        "13:00",
        "13:15",
        "13:30",
        "13:45",
        "14:00",
        "14:15",
        "14:30",
        "14:45",
        "15:00",
        "15:15",
        "15:30",
        "15:45",
        "16:00",
        "16:15",
        "16:30",
        "16:45",
        "17:00",
        "17:15",
        "17:30",
        "17:45"
      ],
      "timeBlocks": [
        {
          "key": "T_540_555",
          "start": "09:00",
          "end": "09:15",
          "startMinutes": 540,
          "endMinutes": 555
        }
      ],
      "allMeetingDurations": [
        {
          "name": 15,
          "value": "15分钟"
        }
      ],
      "allWeekDays": [
        {
          "name": 1,
          "value": "周一"
        }
      ],
      "meetingRepeatTypes": [
        "NONE",
        "WEEK",
        "MONTH"
      ],
      "needCheckin": true,
      "disablePersonConflict": false,
      "enableFixedBooking": false,
      "enableAgentBooking": true
    },
    "bookingDays": [
      {
        "day": "2026-10-03",
        "workDay": false,
        "lawDay": false,
        "weekDay": 6,
        "meetingCount": 5,
        "roomCount": 532,
        "bookingRoomCount": 0,
        "bookingRate": 0.94,
        "meetingMinutes": 900,
        "rooms": []
      }
    ]
  }
}
```

**24H学习空间返回样例**，24H学习空间预约.har#37，00:32:25.792，HTTP 200 / JSON.code=0。

```json
{
  "code": 0,
  "data": {
    "currentOfficeArea": {
      "id": "all",
      "name": "所有区域",
      "shortName": "所有区域",
      "supportRoomTypes": [
        "ROOM"
      ],
      "abilities": []
    },
    "bookingTimes": {
      "timeBlockType": "FIXED_BLOCK",
      "startHour": 8,
      "endHour": 24,
      "morningEndHour": 12,
      "afternoonStartHour": 12,
      "maxDuration": 1440,
      "configMaxDuration": 1440,
      "meetingInterval": 15,
      "bookingLimitDays": 7,
      "meetingHalfHours": [
        "08:00",
        "08:15",
        "08:30",
        "08:45",
        "09:00",
        "09:15",
        "09:30",
        "09:45",
        "10:00",
        "10:15",
        "10:30",
        "10:45",
        "11:00",
        "11:15",
        "11:30",
        "11:45",
        "12:00",
        "12:15",
        "12:30",
        "12:45",
        "13:00",
        "13:15",
        "13:30",
        "13:45",
        "14:00",
        "14:15",
        "14:30",
        "14:45",
        "15:00",
        "15:15",
        "15:30",
        "15:45",
        "16:00",
        "16:15",
        "16:30",
        "16:45",
        "17:00",
        "17:15",
        "17:30",
        "17:45",
        "18:00",
        "18:15",
        "18:30",
        "18:45",
        "19:00",
        "19:15",
        "19:30",
        "19:45",
        "20:00",
        "20:15",
        "20:30",
        "20:45",
        "21:00",
        "21:15",
        "21:30",
        "21:45",
        "22:00",
        "22:15",
        "22:30",
        "22:45",
        "23:00",
        "23:15",
        "23:30",
        "23:45"
      ],
      "timeBlocks": [
        {
          "key": "T_480_495",
          "start": "08:00",
          "end": "08:15",
          "startMinutes": 480,
          "endMinutes": 495
        }
      ],
      "allMeetingDurations": [
        {
          "name": 15,
          "value": "15分钟"
        }
      ],
      "allWeekDays": [
        {
          "name": 1,
          "value": "周一"
        }
      ],
      "meetingRepeatTypes": [
        "NONE",
        "WEEK",
        "MONTH"
      ],
      "needCheckin": true,
      "disablePersonConflict": true,
      "enableFixedBooking": false,
      "enableAgentBooking": true
    },
    "bookingDays": [
      {
        "day": "2026-10-03",
        "workDay": false,
        "lawDay": false,
        "weekDay": 6,
        "meetingCount": 736,
        "roomCount": 309,
        "bookingRoomCount": 0,
        "bookingRate": 238.19,
        "meetingMinutes": 254877,
        "rooms": []
      }
    ]
  }
}
```

**延长智能中心返回样例**，延长智能中心预约.har#23，00:34:07.746，HTTP 200 / JSON.code=0。

```json
{
  "code": 0,
  "data": {
    "currentOfficeArea": {
      "id": "all",
      "name": "所有区域",
      "shortName": "所有区域",
      "supportRoomTypes": [
        "ROOM"
      ],
      "abilities": []
    },
    "bookingTimes": {
      "timeBlockType": "FIXED_BLOCK",
      "startHour": 9,
      "endHour": 18,
      "morningEndHour": 12,
      "afternoonStartHour": 12,
      "maxDuration": 480,
      "configMaxDuration": 480,
      "meetingInterval": 15,
      "bookingLimitDays": 365,
      "meetingHalfHours": [
        "09:00",
        "09:15",
        "09:30",
        "09:45",
        "10:00",
        "10:15",
        "10:30",
        "10:45",
        "11:00",
        "11:15",
        "11:30",
        "11:45",
        "12:00",
        "12:15",
        "12:30",
        "12:45",
        "13:00",
        "13:15",
        "13:30",
        "13:45",
        "14:00",
        "14:15",
        "14:30",
        "14:45",
        "15:00",
        "15:15",
        "15:30",
        "15:45",
        "16:00",
        "16:15",
        "16:30",
        "16:45",
        "17:00",
        "17:15",
        "17:30",
        "17:45"
      ],
      "timeBlocks": [
        {
          "key": "T_540_555",
          "start": "09:00",
          "end": "09:15",
          "startMinutes": 540,
          "endMinutes": 555
        }
      ],
      "allMeetingDurations": [
        {
          "name": 15,
          "value": "15分钟"
        }
      ],
      "allWeekDays": [
        {
          "name": 1,
          "value": "周一"
        }
      ],
      "meetingRepeatTypes": [
        "NONE",
        "WEEK",
        "MONTH"
      ],
      "needCheckin": true,
      "disablePersonConflict": false,
      "enableFixedBooking": false,
      "enableAgentBooking": true
    },
    "bookingDays": [
      {
        "day": "2026-10-03",
        "workDay": false,
        "lawDay": false,
        "weekDay": 6,
        "meetingCount": 1,
        "roomCount": 54,
        "bookingRoomCount": 0,
        "bookingRate": 1.85,
        "meetingMinutes": 60,
        "rooms": []
      }
    ]
  }
}
```

**科学与艺术中心返回样例**，科学与艺术中心预约.har#23，00:35:46.254，HTTP 200 / JSON.code=0。

```json
{
  "code": 0,
  "data": {
    "currentOfficeArea": {
      "id": "all",
      "name": "所有区域",
      "shortName": "所有区域",
      "supportRoomTypes": [
        "ROOM"
      ],
      "abilities": []
    },
    "bookingTimes": {
      "timeBlockType": "FIXED_BLOCK",
      "startHour": 9,
      "endHour": 18,
      "morningEndHour": 12,
      "afternoonStartHour": 12,
      "maxDuration": 480,
      "configMaxDuration": 480,
      "meetingInterval": 15,
      "bookingLimitDays": 365,
      "meetingHalfHours": [
        "09:00",
        "09:15",
        "09:30",
        "09:45",
        "10:00",
        "10:15",
        "10:30",
        "10:45",
        "11:00",
        "11:15",
        "11:30",
        "11:45",
        "12:00",
        "12:15",
        "12:30",
        "12:45",
        "13:00",
        "13:15",
        "13:30",
        "13:45",
        "14:00",
        "14:15",
        "14:30",
        "14:45",
        "15:00",
        "15:15",
        "15:30",
        "15:45",
        "16:00",
        "16:15",
        "16:30",
        "16:45",
        "17:00",
        "17:15",
        "17:30",
        "17:45"
      ],
      "timeBlocks": [
        {
          "key": "T_540_555",
          "start": "09:00",
          "end": "09:15",
          "startMinutes": 540,
          "endMinutes": 555
        }
      ],
      "allMeetingDurations": [
        {
          "name": 15,
          "value": "15分钟"
        }
      ],
      "allWeekDays": [
        {
          "name": 1,
          "value": "周一"
        }
      ],
      "meetingRepeatTypes": [
        "NONE",
        "WEEK",
        "MONTH"
      ],
      "needCheckin": true,
      "disablePersonConflict": false,
      "enableFixedBooking": false,
      "enableAgentBooking": true
    },
    "bookingDays": [
      {
        "day": "2026-10-03",
        "workDay": false,
        "lawDay": false,
        "weekDay": 6,
        "meetingCount": 1,
        "roomCount": 241,
        "bookingRoomCount": 0,
        "bookingRate": 0.41,
        "meetingMinutes": 300,
        "rooms": []
      }
    ]
  }
}
```

来源：校本部图书馆预约.har#67、校本部图书馆预约.har#56、校本部图书馆预约.har#53、校本部图书馆预约.har#35、校本部图书馆预约.har#31、校本部图书馆预约.har#29、校本部图书馆预约.har#27、校本部图书馆预约.har#14、24H学习空间预约.har#27、24H学习空间预约.har#37、延长智能中心预约.har#53、延长智能中心预约.har#44、延长智能中心预约.har#41、延长智能中心预约.har#23、科学与艺术中心预约.har#51、科学与艺术中心预约.har#47、科学与艺术中心预约.har#42、科学与艺术中心预约.har#30、科学与艺术中心预约.har#32、科学与艺术中心预约.har#23。

### 4.4 区域列表

**GET `/api/v3/booking-status/areas`**。取得区域树。目录节点和可选区域均可能使用 level=FLOOR，不能只靠 level 判断叶节点。 本次调用 10 次，HTTP 状态 200，JSON.code 捕获值 0。

| 位置 | 参数 | 类型 | 值或格式 | 来源与说明 |
| --- | --- | --- | --- | --- |
| query | `begin` | string | 2026-10-03, 2026-10-03 08:30 | 本次 YYYY-MM-DD 或 YYYY-MM-DD HH:mm，使用 Asia/Shanghai。应以标准 URL 编码传输空格。省略行为未验证。 |
| query | `end` | string | 2026-10-03, 2026-10-03 09:30 | 本次格式同 begin。仅选择开始时间的中间请求出现 begin 含时间而 end 只有日期，不能把这种 UI 中间状态当作最终预约区间。 |

**完整捕获返回字段**

| JSON 字段路径 | 捕获类型 | 说明 |
| --- | --- | --- |
| `code` | `integer` | HAR：0 为业务成功，200 为业务拒绝；与 HTTP 状态码不同。 |
| `data` | `array<object>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[]` | `object` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].disabledResourceCount` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingTimes` | `object` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingTimes.timeBlockType` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingTimes.startHour` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingTimes.endHour` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingTimes.morningEndHour` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingTimes.afternoonStartHour` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingTimes.maxDuration` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingTimes.minDuration` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingTimes.configMaxDuration` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingTimes.meetingInterval` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingTimes.bookingLimitDays` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingTimes.meetingHalfHours` | `array<string>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingTimes.timeBlocks` | `array<object>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingTimes.timeBlocks[]` | `object` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingTimes.timeBlocks[].key` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingTimes.timeBlocks[].start` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingTimes.timeBlocks[].end` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingTimes.timeBlocks[].startMinutes` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingTimes.timeBlocks[].endMinutes` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingTimes.allMeetingDurations` | `array<object>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingTimes.allMeetingDurations[]` | `object` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingTimes.allMeetingDurations[].name` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingTimes.allMeetingDurations[].value` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingTimes.allWeekDays` | `array<object>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingTimes.allWeekDays[]` | `object` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingTimes.allWeekDays[].name` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingTimes.allWeekDays[].value` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingTimes.meetingRepeatTypes` | `array<string>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingTimes.needCheckin` | `boolean` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingTimes.disablePersonConflict` | `boolean` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingTimes.enableFixedBooking` | `boolean` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookingTimes.enableAgentBooking` | `boolean` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].id` | `string` | recent/创建响应时是 bookingId；区域列表时是 areaId。 |
| `data[].name` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].level` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].path` | `array<object>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].path[]` | `object` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].path[].id` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].path[].name` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].shortName` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].showOrder` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].supportRoomTypes` | `array<string>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].abilities` | `array<unknown>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].totalResourceCount` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookedResourceCount` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookedMeetingCount` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].bookableResourceCount` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].busyResourceCount` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].freeResourceCount` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].parentId` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].parentName` | `string` | 捕获字段；未验证其在全部场景是否必返。 |

**校本部图书馆返回样例**，校本部图书馆预约.har#54，00:25:52.070，HTTP 200 / JSON.code=0。

```json
{
  "code": 0,
  "data": [
    {
      "disabledResourceCount": 0,
      "bookingTimes": {
        "timeBlockType": "FIXED_BLOCK",
        "startHour": 8,
        "endHour": 23,
        "morningEndHour": 12,
        "afternoonStartHour": 12,
        "maxDuration": 480,
        "minDuration": 30,
        "configMaxDuration": 480,
        "meetingInterval": 30,
        "bookingLimitDays": 1,
        "meetingHalfHours": [
          "08:00",
          "08:30",
          "09:00",
          "09:30",
          "10:00",
          "10:30",
          "11:00",
          "11:30",
          "12:00",
          "12:30",
          "13:00",
          "13:30",
          "14:00",
          "14:30",
          "15:00",
          "15:30",
          "16:00",
          "16:30",
          "17:00",
          "17:30",
          "18:00",
          "18:30",
          "19:00",
          "19:30",
          "20:00",
          "20:30",
          "21:00",
          "21:30",
          "22:00",
          "22:30"
        ],
        "timeBlocks": [
          {
            "key": "T_480_510",
            "start": "08:00",
            "end": "08:30",
            "startMinutes": 480,
            "endMinutes": 510
          }
        ],
        "allMeetingDurations": [
          {
            "name": 30,
            "value": "30分钟"
          }
        ],
        "allWeekDays": [
          {
            "name": 1,
            "value": "周一"
          }
        ],
        "meetingRepeatTypes": [
          "NONE",
          "WEEK",
          "MONTH"
        ],
        "needCheckin": true,
        "disablePersonConflict": false,
        "enableFixedBooking": false,
        "enableAgentBooking": true
      },
      "id": "CvT5k6Aivz2riLTRTq2FxM",
      "name": "校本部图书馆自修区",
      "level": "FLOOR",
      "path": [
        {
          "id": "CvT5k6Aivz2riLTRTq2FxM",
          "name": "校本部图书馆自修区"
        }
      ],
      "shortName": "校本部图书馆自修区",
      "showOrder": 24,
      "supportRoomTypes": [
        "LIB_SEAT"
      ],
      "abilities": []
    }
  ]
}
```

**24H学习空间返回样例**，24H学习空间预约.har#38，00:32:12.449，HTTP 200 / JSON.code=0。

```json
{
  "code": 0,
  "data": [
    {
      "disabledResourceCount": 0,
      "bookingTimes": {
        "timeBlockType": "FIXED_BLOCK",
        "startHour": 8,
        "endHour": 24,
        "morningEndHour": 12,
        "afternoonStartHour": 12,
        "maxDuration": 1440,
        "configMaxDuration": 1440,
        "meetingInterval": 15,
        "bookingLimitDays": 7,
        "meetingHalfHours": [
          "08:00",
          "08:15",
          "08:30",
          "08:45",
          "09:00",
          "09:15",
          "09:30",
          "09:45",
          "10:00",
          "10:15",
          "10:30",
          "10:45",
          "11:00",
          "11:15",
          "11:30",
          "11:45",
          "12:00",
          "12:15",
          "12:30",
          "12:45",
          "13:00",
          "13:15",
          "13:30",
          "13:45",
          "14:00",
          "14:15",
          "14:30",
          "14:45",
          "15:00",
          "15:15",
          "15:30",
          "15:45",
          "16:00",
          "16:15",
          "16:30",
          "16:45",
          "17:00",
          "17:15",
          "17:30",
          "17:45",
          "18:00",
          "18:15",
          "18:30",
          "18:45",
          "19:00",
          "19:15",
          "19:30",
          "19:45",
          "20:00",
          "20:15",
          "20:30",
          "20:45",
          "21:00",
          "21:15",
          "21:30",
          "21:45",
          "22:00",
          "22:15",
          "22:30",
          "22:45",
          "23:00",
          "23:15",
          "23:30",
          "23:45"
        ],
        "timeBlocks": [
          {
            "key": "T_480_495",
            "start": "08:00",
            "end": "08:15",
            "startMinutes": 480,
            "endMinutes": 495
          }
        ],
        "allMeetingDurations": [
          {
            "name": 15,
            "value": "15分钟"
          }
        ],
        "allWeekDays": [
          {
            "name": 1,
            "value": "周一"
          }
        ],
        "meetingRepeatTypes": [
          "NONE",
          "WEEK",
          "MONTH"
        ],
        "needCheckin": true,
        "disablePersonConflict": true,
        "enableFixedBooking": false,
        "enableAgentBooking": true
      },
      "id": "7pcMcUCRxXE6fzXhLp7za7",
      "name": "图书馆24小时自习区",
      "level": "FLOOR",
      "path": [
        {
          "id": "7pcMcUCRxXE6fzXhLp7za7",
          "name": "图书馆24小时自习区"
        }
      ],
      "shortName": "图书馆24小时自习区",
      "showOrder": 55,
      "supportRoomTypes": [
        "STATION"
      ],
      "abilities": []
    }
  ]
}
```

**延长智能中心返回样例**，延长智能中心预约.har#42，00:33:55.324，HTTP 200 / JSON.code=0。

```json
{
  "code": 0,
  "data": [
    {
      "disabledResourceCount": 0,
      "bookingTimes": {
        "timeBlockType": "FIXED_BLOCK",
        "startHour": 9,
        "endHour": 18,
        "morningEndHour": 12,
        "afternoonStartHour": 12,
        "maxDuration": 480,
        "configMaxDuration": 480,
        "meetingInterval": 15,
        "bookingLimitDays": 365,
        "meetingHalfHours": [
          "09:00",
          "09:15",
          "09:30",
          "09:45",
          "10:00",
          "10:15",
          "10:30",
          "10:45",
          "11:00",
          "11:15",
          "11:30",
          "11:45",
          "12:00",
          "12:15",
          "12:30",
          "12:45",
          "13:00",
          "13:15",
          "13:30",
          "13:45",
          "14:00",
          "14:15",
          "14:30",
          "14:45",
          "15:00",
          "15:15",
          "15:30",
          "15:45",
          "16:00",
          "16:15",
          "16:30",
          "16:45",
          "17:00",
          "17:15",
          "17:30",
          "17:45"
        ],
        "timeBlocks": [
          {
            "key": "T_540_555",
            "start": "09:00",
            "end": "09:15",
            "startMinutes": 540,
            "endMinutes": 555
          }
        ],
        "allMeetingDurations": [
          {
            "name": 15,
            "value": "15分钟"
          }
        ],
        "allWeekDays": [
          {
            "name": 1,
            "value": "周一"
          }
        ],
        "meetingRepeatTypes": [
          "NONE",
          "WEEK",
          "MONTH"
        ],
        "needCheckin": true,
        "disablePersonConflict": false,
        "enableFixedBooking": false,
        "enableAgentBooking": true
      },
      "id": "4N9ynVts4eU8toDS7qP6qk",
      "name": "智能信息中心智慧共享空间",
      "level": "FLOOR",
      "path": [
        {
          "id": "4N9ynVts4eU8toDS7qP6qk",
          "name": "智能信息中心智慧共享空间"
        }
      ],
      "shortName": "智能信息中心智慧共享空间",
      "showOrder": 37,
      "supportRoomTypes": [
        "SEAT"
      ],
      "abilities": []
    }
  ]
}
```

**科学与艺术中心返回样例**，科学与艺术中心预约.har#41，00:35:12.542，HTTP 200 / JSON.code=0。

```json
{
  "code": 0,
  "data": [
    {
      "disabledResourceCount": 0,
      "bookingTimes": {
        "timeBlockType": "FIXED_BLOCK",
        "startHour": 8,
        "endHour": 22,
        "morningEndHour": 12,
        "afternoonStartHour": 12,
        "maxDuration": 480,
        "configMaxDuration": 480,
        "meetingInterval": 60,
        "bookingLimitDays": 365,
        "meetingHalfHours": [
          "08:00",
          "09:00",
          "10:00",
          "11:00",
          "12:00",
          "13:00",
          "14:00",
          "15:00",
          "16:00",
          "17:00",
          "18:00",
          "19:00",
          "20:00",
          "21:00"
        ],
        "timeBlocks": [
          {
            "key": "T_480_540",
            "start": "08:00",
            "end": "09:00",
            "startMinutes": 480,
            "endMinutes": 540
          }
        ],
        "allMeetingDurations": [
          {
            "name": 60,
            "value": "1小时"
          }
        ],
        "allWeekDays": [
          {
            "name": 1,
            "value": "周一"
          }
        ],
        "meetingRepeatTypes": [
          "NONE",
          "WEEK",
          "MONTH"
        ],
        "needCheckin": true,
        "disablePersonConflict": false,
        "enableFixedBooking": false,
        "enableAgentBooking": true
      },
      "id": "WtgvL1bEPyVVjtdHDVtH4i",
      "name": "科学与艺术中心",
      "level": "FLOOR",
      "path": [
        {
          "id": "WtgvL1bEPyVVjtdHDVtH4i",
          "name": "科学与艺术中心"
        }
      ],
      "shortName": "科学与艺术中心",
      "showOrder": 1,
      "supportRoomTypes": [
        "CS_SEAT"
      ],
      "abilities": []
    }
  ]
}
```

来源：校本部图书馆预约.har#57、校本部图书馆预约.har#55、校本部图书馆预约.har#54、24H学习空间预约.har#38、延长智能中心预约.har#52、延长智能中心预约.har#45、延长智能中心预约.har#42、科学与艺术中心预约.har#61、科学与艺术中心预约.har#46、科学与艺术中心预约.har#41。

### 4.5 区域座位与规则

**GET `/api/v3/booking-status/areas/{areaId}`**。rooms[].id 用于预约；rooms[].officeAreaId 对应该区域。查询指定时间区间后选择未禁用且可预约的座位。 本次调用 24 次，HTTP 状态 200，JSON.code 捕获值 0。

| 位置 | 参数 | 类型 | 值或格式 | 来源与说明 |
| --- | --- | --- | --- | --- |
| path | `areaId` | string | KRdcGiyK99gzrqCepi91Cv | 来自区域列表 data[].id 或 rooms[].officeAreaId。 |
| query | `begin` | string | 2026-10-03, 2026-10-03 08:30 | 本次 YYYY-MM-DD 或 YYYY-MM-DD HH:mm，使用 Asia/Shanghai。应以标准 URL 编码传输空格。省略行为未验证。 |
| query | `end` | string | 2026-10-03, 2026-10-03 09:30 | 本次格式同 begin。仅选择开始时间的中间请求出现 begin 含时间而 end 只有日期，不能把这种 UI 中间状态当作最终预约区间。 |

**完整捕获返回字段**

| JSON 字段路径 | 捕获类型 | 说明 |
| --- | --- | --- |
| `code` | `integer` | HAR：0 为业务成功，200 为业务拒绝；与 HTTP 状态码不同。 |
| `data` | `object` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.totalResourceCount` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookedResourceCount` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookedMeetingCount` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.disabledResourceCount` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookableResourceCount` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes` | `object` | 当前响应的时间配置；须区分概览通用配置和选中区域配置。 |
| `data.bookingTimes.timeBlockType` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.supportAcrossDayBooking` | `boolean` | 四个选中区域均为 false。 |
| `data.bookingTimes.suggestStartTime` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.suggestEndTime` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.startHour` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.endHour` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.morningEndHour` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.afternoonStartHour` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.maxDuration` | `integer` | 本次按分钟使用；所选四区域均为 480。 |
| `data.bookingTimes.minDuration` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.configMaxDuration` | `integer` | 本次按分钟使用；所选四区域均为 480。 |
| `data.bookingTimes.meetingInterval` | `integer` | 本次按分钟使用，四区域分别为 30、30、15、60。 |
| `data.bookingTimes.bookingLimitDays` | `integer` | 不要直接用该数值截断 bookingDays；样本存在差异。 |
| `data.bookingTimes.meetingHalfHours` | `array<string>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.timeBlocks` | `array<object>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.timeBlocks[]` | `object` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.timeBlocks[].key` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.timeBlocks[].start` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.timeBlocks[].end` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.timeBlocks[].startMinutes` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.timeBlocks[].endMinutes` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.timeBlocks[].disabled` | `boolean` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.allMeetingDurations` | `array<object>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.allMeetingDurations[]` | `object` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.allMeetingDurations[].name` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.allMeetingDurations[].value` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.allWeekDays` | `array<object>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.allWeekDays[]` | `object` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.allWeekDays[].name` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.allWeekDays[].value` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.meetingRepeatTypes` | `array<string>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.needCheckin` | `boolean` | 四区域均为 true；实际签到请求未捕获。 |
| `data.bookingTimes.disablePersonConflict` | `boolean` | 24H 为 true，其余 false；没有验证具体冲突校验效果。 |
| `data.bookingTimes.enableFixedBooking` | `boolean` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingTimes.enableAgentBooking` | `boolean` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.assetFiles` | `array<object>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.assetFiles[]` | `object` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.assetFiles[].id` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.assetFiles[].uid` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.assetFiles[].title` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.assetFiles[].url` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.assetFiles[].thumbnailUrl` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.assetFiles[].name` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.assetFiles[].fileName` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingDays` | `array<string>` | 捕获的候选日期数组，不等同于服务端准入边界。 |
| `data.id` | `string` | profile 时是用户 ID；区域详情时是 areaId；预约详情时是 bookingId。 |
| `data.name` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.level` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.path` | `array<object>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.path[]` | `object` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.path[].id` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.path[].name` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.shortName` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.showOrder` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.supportRoomTypes` | `array<string>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.parentId` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.parentName` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.rooms` | `array<object>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.rooms[]` | `object` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.rooms[].id` | `string` | 座位资源 ID，创建请求 rooms[].id 的来源。 |
| `data.rooms[].name` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.rooms[].officeAreaId` | `string` | 所属区域 ID。 |
| `data.rooms[].disabled` | `boolean` | 座位禁用状态。 |
| `data.rooms[].showOrder` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.rooms[].isBusy` | `boolean` | 当前查询区间的状态；不保证提交时仍可用。 |
| `data.rooms[].isBooked` | `boolean` | 当前查询返回的预约状态。 |
| `data.rooms[].abilities` | `array<string>` | 前端可执行能力；创建候选通常包含 booking。 |
| `data.rooms[].currentBooking` | `object` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.rooms[].currentBooking.id` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.rooms[].currentBooking.subject` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.rooms[].currentBooking.ownerId` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.rooms[].currentBooking.beginTime` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.rooms[].currentBooking.endTime` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.rooms[].currentBooking.templateType` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.rooms[].currentBooking.beforeNotify` | `boolean` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.rooms[].currentBooking.abilities` | `array<unknown>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.abilities` | `array<unknown>` | 详情的操作能力，例如 cancel、waitOpen、close；不能用状态字段单独替代。 |
| `data.busyResourceCount` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.freeResourceCount` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |

**校本部图书馆返回样例**，校本部图书馆预约.har#19，00:26:32.777，HTTP 200 / JSON.code=0。

```json
{
  "code": 0,
  "data": {
    "totalResourceCount": 268,
    "bookedResourceCount": 1,
    "bookedMeetingCount": 1,
    "disabledResourceCount": 0,
    "bookableResourceCount": 268,
    "bookingTimes": {
      "timeBlockType": "FIXED_BLOCK",
      "supportAcrossDayBooking": false,
      "suggestStartTime": "08:30",
      "suggestEndTime": "09:30",
      "startHour": 8,
      "endHour": 22,
      "morningEndHour": 12,
      "afternoonStartHour": 12,
      "maxDuration": 480,
      "minDuration": 30,
      "configMaxDuration": 480,
      "meetingInterval": 30,
      "bookingLimitDays": 1,
      "meetingHalfHours": [
        "08:00",
        "08:30",
        "09:00",
        "09:30",
        "10:00",
        "10:30",
        "11:00",
        "11:30",
        "12:00",
        "12:30",
        "13:00",
        "13:30",
        "14:00",
        "14:30",
        "15:00",
        "15:30",
        "16:00",
        "16:30",
        "17:00",
        "17:30",
        "18:00",
        "18:30",
        "19:00",
        "19:30",
        "20:00",
        "20:30",
        "21:00",
        "21:30"
      ],
      "timeBlocks": [
        {
          "key": "T_480_510",
          "start": "08:00",
          "end": "08:30",
          "startMinutes": 480,
          "endMinutes": 510,
          "disabled": false
        }
      ],
      "allMeetingDurations": [
        {
          "name": 30,
          "value": "30分钟"
        }
      ],
      "allWeekDays": [
        {
          "name": 1,
          "value": "周一"
        }
      ],
      "meetingRepeatTypes": [
        "NONE",
        "WEEK",
        "MONTH"
      ],
      "needCheckin": true,
      "disablePersonConflict": false,
      "enableFixedBooking": false,
      "enableAgentBooking": true
    },
    "assetFiles": [],
    "bookingDays": [
      "2026-10-03",
      "2026-10-04"
    ],
    "id": "KRdcGiyK99gzrqCepi91Cv",
    "name": "二楼东侧",
    "level": "FLOOR",
    "path": [
      {
        "id": "CvT5k6Aivz2riLTRTq2FxM",
        "name": "校本部图书馆自修区"
      }
    ],
    "shortName": "二楼东侧",
    "showOrder": 33,
    "supportRoomTypes": [
      "LIB_SEAT"
    ],
    "parentId": "CvT5k6Aivz2riLTRTq2FxM",
    "parentName": "校本部图书馆自修区",
    "rooms": [
      {
        "id": "HfRA7PNYwKydAmB5yfeVLs",
        "name": "2E001",
        "officeAreaId": "KRdcGiyK99gzrqCepi91Cv",
        "disabled": false,
        "showOrder": 1,
        "isBusy": false,
        "isBooked": false,
        "abilities": [
          "booking"
        ]
      }
    ],
    "abilities": []
  }
}
```

**24H学习空间返回样例**，24H学习空间预约.har#12，00:32:25.753，HTTP 200 / JSON.code=0。

```json
{
  "code": 0,
  "data": {
    "totalResourceCount": 171,
    "bookedResourceCount": 1,
    "bookedMeetingCount": 1,
    "disabledResourceCount": 0,
    "bookableResourceCount": 171,
    "busyResourceCount": 1,
    "freeResourceCount": 170,
    "bookingTimes": {
      "timeBlockType": "FIXED_BLOCK",
      "supportAcrossDayBooking": false,
      "suggestStartTime": "00:30",
      "suggestEndTime": "01:30",
      "startHour": 0,
      "endHour": 24,
      "morningEndHour": 12,
      "afternoonStartHour": 12,
      "maxDuration": 480,
      "configMaxDuration": 480,
      "meetingInterval": 30,
      "bookingLimitDays": 1,
      "meetingHalfHours": [
        "00:00",
        "00:30",
        "01:00",
        "01:30",
        "02:00",
        "02:30",
        "03:00",
        "03:30",
        "04:00",
        "04:30",
        "05:00",
        "05:30",
        "06:00",
        "06:30",
        "07:00",
        "07:30",
        "08:00",
        "08:30",
        "09:00",
        "09:30",
        "10:00",
        "10:30",
        "11:00",
        "11:30",
        "12:00",
        "12:30",
        "13:00",
        "13:30",
        "14:00",
        "14:30",
        "15:00",
        "15:30",
        "16:00",
        "16:30",
        "17:00",
        "17:30",
        "18:00",
        "18:30",
        "19:00",
        "19:30",
        "20:00",
        "20:30",
        "21:00",
        "21:30",
        "22:00",
        "22:30",
        "23:00",
        "23:30"
      ],
      "timeBlocks": [
        {
          "key": "T_0_30",
          "start": "00:00",
          "end": "00:30",
          "startMinutes": 0,
          "endMinutes": 30,
          "disabled": true
        }
      ],
      "allMeetingDurations": [
        {
          "name": 30,
          "value": "30分钟"
        }
      ],
      "allWeekDays": [
        {
          "name": 1,
          "value": "周一"
        }
      ],
      "meetingRepeatTypes": [
        "NONE",
        "WEEK",
        "MONTH"
      ],
      "needCheckin": true,
      "disablePersonConflict": true,
      "enableFixedBooking": false,
      "enableAgentBooking": true
    },
    "assetFiles": [
      {
        "id": "WWbboYASvwko2JUpxF91Bn",
        "uid": "WWbboYASvwko2JUpxF91Bn",
        "title": "B",
        "url": "https://there.shu.edu.cn/upload-images/2022-03-27/580db9e12d384ef89e201430112c644b.jpg",
        "thumbnailUrl": "https://there.shu.edu.cn/upload-images/2022-03-27/580db9e12d384ef89e201430112c644b.jpg/96",
        "name": "24小时座位图20220327.jpg",
        "fileName": "24小时座位图20220327.jpg"
      }
    ],
    "bookingDays": [
      "2026-10-03",
      "2026-10-04"
    ],
    "id": "DsNjTXf8icSMh3SXB5HPge",
    "name": "B",
    "level": "FLOOR",
    "path": [
      {
        "id": "7pcMcUCRxXE6fzXhLp7za7",
        "name": "图书馆24小时自习区"
      }
    ],
    "shortName": "B",
    "showOrder": 58,
    "supportRoomTypes": [
      "STATION"
    ],
    "parentId": "7pcMcUCRxXE6fzXhLp7za7",
    "parentName": "图书馆24小时自习区",
    "rooms": [
      {
        "id": "SAHimHHHYMvdPzPzLt7cLC",
        "name": "B-001",
        "officeAreaId": "DsNjTXf8icSMh3SXB5HPge",
        "disabled": false,
        "showOrder": 1,
        "isBusy": false,
        "isBooked": false,
        "abilities": [
          "booking"
        ]
      }
    ],
    "abilities": []
  }
}
```

**延长智能中心返回样例**，延长智能中心预约.har#20，00:34:07.898，HTTP 200 / JSON.code=0。

```json
{
  "code": 0,
  "data": {
    "totalResourceCount": 18,
    "bookedResourceCount": 1,
    "bookedMeetingCount": 1,
    "disabledResourceCount": 0,
    "bookableResourceCount": 18,
    "bookingTimes": {
      "timeBlockType": "FIXED_BLOCK",
      "supportAcrossDayBooking": false,
      "suggestStartTime": "09:30",
      "suggestEndTime": "10:30",
      "startHour": 9,
      "endHour": 18,
      "morningEndHour": 12,
      "afternoonStartHour": 12,
      "maxDuration": 480,
      "configMaxDuration": 480,
      "meetingInterval": 15,
      "bookingLimitDays": 365,
      "meetingHalfHours": [
        "09:00",
        "09:15",
        "09:30",
        "09:45",
        "10:00",
        "10:15",
        "10:30",
        "10:45",
        "11:00",
        "11:15",
        "11:30",
        "11:45",
        "12:00",
        "12:15",
        "12:30",
        "12:45",
        "13:00",
        "13:15",
        "13:30",
        "13:45",
        "14:00",
        "14:15",
        "14:30",
        "14:45",
        "15:00",
        "15:15",
        "15:30",
        "15:45",
        "16:00",
        "16:15",
        "16:30",
        "16:45",
        "17:00",
        "17:15",
        "17:30",
        "17:45"
      ],
      "timeBlocks": [
        {
          "key": "T_540_555",
          "start": "09:00",
          "end": "09:15",
          "startMinutes": 540,
          "endMinutes": 555,
          "disabled": false
        }
      ],
      "allMeetingDurations": [
        {
          "name": 15,
          "value": "15分钟"
        }
      ],
      "allWeekDays": [
        {
          "name": 1,
          "value": "周一"
        }
      ],
      "meetingRepeatTypes": [
        "NONE",
        "WEEK",
        "MONTH"
      ],
      "needCheckin": true,
      "disablePersonConflict": false,
      "enableFixedBooking": false,
      "enableAgentBooking": true
    },
    "assetFiles": [],
    "bookingDays": [
      "2026-10-03",
      "2026-10-04",
      "2026-10-05",
      "2026-10-06",
      "2026-10-07",
      "2026-10-08",
      "2026-10-09",
      "2026-10-10",
      "2026-10-11",
      "2026-10-12",
      "2026-10-13",
      "2026-10-14",
      "2026-10-15",
      "2026-10-16",
      "2026-10-17",
      "2026-10-18",
      "2026-10-19",
      "2026-10-20",
      "2026-10-21",
      "2026-10-22",
      "2026-10-23",
      "2026-10-24",
      "2026-10-25",
      "2026-10-26",
      "2026-10-27",
      "2026-10-28",
      "2026-10-29",
      "2026-10-30",
      "2026-10-31",
      "2026-11-01"
    ],
    "id": "KbuCBLACKv74KmiBqE51z6",
    "name": "B",
    "level": "FLOOR",
    "path": [
      {
        "id": "4N9ynVts4eU8toDS7qP6qk",
        "name": "智能信息中心智慧共享空间"
      }
    ],
    "shortName": "B",
    "showOrder": 59,
    "supportRoomTypes": [
      "SEAT"
    ],
    "parentId": "4N9ynVts4eU8toDS7qP6qk",
    "parentName": "智能信息中心智慧共享空间",
    "rooms": [
      {
        "id": "FGN6s7xPbFgpsCYonTpisF",
        "name": "7-1",
        "officeAreaId": "KbuCBLACKv74KmiBqE51z6",
        "disabled": false,
        "showOrder": 18,
        "isBusy": false,
        "isBooked": false,
        "abilities": [
          "booking"
        ]
      }
    ],
    "abilities": []
  }
}
```

**科学与艺术中心返回样例**，科学与艺术中心预约.har#22，00:35:46.254，HTTP 200 / JSON.code=0。

```json
{
  "code": 0,
  "data": {
    "totalResourceCount": 60,
    "bookedResourceCount": 1,
    "bookedMeetingCount": 1,
    "disabledResourceCount": 0,
    "bookableResourceCount": 60,
    "bookingTimes": {
      "timeBlockType": "FIXED_BLOCK",
      "supportAcrossDayBooking": false,
      "suggestStartTime": "09:00",
      "suggestEndTime": "14:00",
      "startHour": 8,
      "endHour": 22,
      "morningEndHour": 12,
      "afternoonStartHour": 12,
      "maxDuration": 480,
      "configMaxDuration": 480,
      "meetingInterval": 60,
      "bookingLimitDays": 30,
      "meetingHalfHours": [
        "08:00",
        "09:00",
        "10:00",
        "11:00",
        "12:00",
        "13:00",
        "14:00",
        "15:00",
        "16:00",
        "17:00",
        "18:00",
        "19:00",
        "20:00",
        "21:00"
      ],
      "timeBlocks": [
        {
          "key": "T_480_540",
          "start": "08:00",
          "end": "09:00",
          "startMinutes": 480,
          "endMinutes": 540,
          "disabled": false
        }
      ],
      "allMeetingDurations": [
        {
          "name": 60,
          "value": "1小时"
        }
      ],
      "allWeekDays": [
        {
          "name": 1,
          "value": "周一"
        }
      ],
      "meetingRepeatTypes": [
        "NONE",
        "WEEK",
        "MONTH"
      ],
      "needCheckin": true,
      "disablePersonConflict": false,
      "enableFixedBooking": false,
      "enableAgentBooking": true
    },
    "assetFiles": [],
    "bookingDays": [
      "2026-10-03",
      "2026-10-04",
      "2026-10-05",
      "2026-10-06",
      "2026-10-07",
      "2026-10-08",
      "2026-10-09",
      "2026-10-10",
      "2026-10-11",
      "2026-10-12",
      "2026-10-13",
      "2026-10-14",
      "2026-10-15",
      "2026-10-16",
      "2026-10-17",
      "2026-10-18",
      "2026-10-19",
      "2026-10-20",
      "2026-10-21",
      "2026-10-22",
      "2026-10-23",
      "2026-10-24",
      "2026-10-25",
      "2026-10-26",
      "2026-10-27",
      "2026-10-28",
      "2026-10-29",
      "2026-10-30",
      "2026-10-31",
      "2026-11-01"
    ],
    "id": "VQyeEokNwJnq7h8sVwmnfg",
    "name": "学生共享创作中心A",
    "level": "FLOOR",
    "path": [
      {
        "id": "WtgvL1bEPyVVjtdHDVtH4i",
        "name": "科学与艺术中心"
      }
    ],
    "shortName": "学生共享创作中心A",
    "showOrder": 3,
    "supportRoomTypes": [
      "CS_SEAT"
    ],
    "parentId": "WtgvL1bEPyVVjtdHDVtH4i",
    "parentName": "科学与艺术中心",
    "rooms": [
      {
        "id": "K8Qo3yidDGFJgY8tBhSyxg",
        "name": "A-1",
        "officeAreaId": "VQyeEokNwJnq7h8sVwmnfg",
        "disabled": false,
        "showOrder": 2,
        "isBusy": false,
        "isBooked": false,
        "abilities": [
          "booking"
        ]
      }
    ],
    "abilities": []
  }
}
```

来源：校本部图书馆预约.har#47、校本部图书馆预约.har#41、校本部图书馆预约.har#40、校本部图书馆预约.har#37、校本部图书馆预约.har#30、校本部图书馆预约.har#26、校本部图书馆预约.har#22、校本部图书馆预约.har#21、校本部图书馆预约.har#19、24H学习空间预约.har#21、24H学习空间预约.har#16、24H学习空间预约.har#15、24H学习空间预约.har#12、延长智能中心预约.har#32、延长智能中心预约.har#28、延长智能中心预约.har#27、延长智能中心预约.har#20、科学与艺术中心预约.har#38、科学与艺术中心预约.har#36、科学与艺术中心预约.har#35、科学与艺术中心预约.har#31、科学与艺术中心预约.har#29、科学与艺术中心预约.har#26、科学与艺术中心预约.har#22。

### 4.6 创建预约

**POST `/api/v3/bookings`**。抓包共 8 次：4 次成功、4 次业务拒绝；HTTP 均为 200。rooms 传入完整座位对象，未验证可缩减为仅 id。 本次调用 8 次，HTTP 状态 200，JSON.code 捕获值 0, 200。

本次没有查询参数。

**创建请求字段**

| 字段路径 | 观测类型 | 说明 |
| --- | --- | --- |
| `rooms` | `array<object>` | 取区域详情返回的完整座位对象；未验证只传 id。 |
| `rooms[]` | `object` | 捕获字段；未验证其在全部场景是否必返。 |
| `rooms[].id` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `rooms[].name` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `rooms[].officeAreaId` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `rooms[].disabled` | `boolean` | 捕获字段；未验证其在全部场景是否必返。 |
| `rooms[].showOrder` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `rooms[].isBusy` | `boolean` | 捕获字段；未验证其在全部场景是否必返。 |
| `rooms[].isBooked` | `boolean` | 捕获字段；未验证其在全部场景是否必返。 |
| `rooms[].abilities` | `array<string>` | 捕获字段；未验证其在全部场景是否必返。 |
| `times` | `array<object>` | 本次仅单时段，数组形状不证明支持多时段。 |
| `times[]` | `object` | 捕获字段；未验证其在全部场景是否必返。 |
| `times[].startDate` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `times[].startTime` | `string` | 本次格式 HH:mm，使用校园当地时间 Asia/Shanghai；未验证其他格式。 |
| `times[].endDate` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `times[].endTime` | `string` | 本次格式 HH:mm，使用校园当地时间 Asia/Shanghai；未验证其他格式。 |
| `subject` | `string` | 8 次请求均来自 profile.data.name。 |
| `meetingMembers` | `array<string>` | 8 次请求均为 [profile.data.id]，代预约及多成员未验证。 |

**校本部图书馆成功创建请求**，校本部图书馆预约.har#20。

```json
{
  "rooms": [
    {
      "id": "2RLARqe9egAFzej4ALBizj",
      "name": "2E015",
      "officeAreaId": "KRdcGiyK99gzrqCepi91Cv",
      "disabled": false,
      "showOrder": 15,
      "isBusy": false,
      "isBooked": false,
      "abilities": [
        "booking"
      ]
    }
  ],
  "times": [
    {
      "startDate": "2026-10-03",
      "startTime": "08:30",
      "endDate": "2026-10-03",
      "endTime": "09:30"
    }
  ],
  "subject": "<profile.data.name>",
  "meetingMembers": [
    "<profile.data.id>"
  ]
}
```

**24H学习空间成功创建请求**，24H学习空间预约.har#14。

```json
{
  "rooms": [
    {
      "id": "4q4z61HkGbJZnK89ejv9wU",
      "name": "B-034",
      "officeAreaId": "DsNjTXf8icSMh3SXB5HPge",
      "disabled": false,
      "showOrder": 34,
      "isBusy": false,
      "isBooked": false,
      "abilities": [
        "booking"
      ]
    }
  ],
  "times": [
    {
      "startDate": "2026-10-03",
      "startTime": "00:30",
      "endDate": "2026-10-03",
      "endTime": "01:30"
    }
  ],
  "subject": "<profile.data.name>",
  "meetingMembers": [
    "<profile.data.id>"
  ]
}
```

**延长智能中心成功创建请求**，延长智能中心预约.har#26。

```json
{
  "rooms": [
    {
      "id": "FLiAcmbCuHCEkRu5SH1rhX",
      "name": "11-3",
      "officeAreaId": "KbuCBLACKv74KmiBqE51z6",
      "disabled": false,
      "showOrder": 32,
      "isBusy": false,
      "isBooked": false,
      "abilities": [
        "booking"
      ]
    }
  ],
  "times": [
    {
      "startDate": "2026-10-03",
      "startTime": "09:30",
      "endDate": "2026-10-03",
      "endTime": "10:30"
    }
  ],
  "subject": "<profile.data.name>",
  "meetingMembers": [
    "<profile.data.id>"
  ]
}
```

**科学与艺术中心成功创建请求**，科学与艺术中心预约.har#25。

```json
{
  "rooms": [
    {
      "id": "ECsWTCtuEoMSq9DqD8ZAPV",
      "name": "A-27",
      "officeAreaId": "VQyeEokNwJnq7h8sVwmnfg",
      "disabled": false,
      "showOrder": 28,
      "isBusy": false,
      "isBooked": false,
      "abilities": [
        "booking"
      ]
    }
  ],
  "times": [
    {
      "startDate": "2026-10-03",
      "startTime": "09:00",
      "endDate": "2026-10-03",
      "endTime": "14:00"
    }
  ],
  "subject": "<profile.data.name>",
  "meetingMembers": [
    "<profile.data.id>"
  ]
}
```

**完整捕获返回字段**

| JSON 字段路径 | 捕获类型 | 说明 |
| --- | --- | --- |
| `code` | `integer` | HAR：0 为业务成功，200 为业务拒绝；与 HTTP 状态码不同。 |
| `warnMessage` | `string` | 业务拒绝提示；错误响应未必有 message。 |
| `message` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data` | `array<object>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[]` | `object` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].id` | `string` | recent/创建响应时是 bookingId；区域列表时是 areaId。 |
| `data[].subject` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].templateType` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].beforeNotify` | `boolean` | 捕获字段；未验证其在全部场景是否必返。 |
| `data[].abilities` | `array<unknown>` | 捕获字段；未验证其在全部场景是否必返。 |
| `noticeMessage` | `string` | 业务操作提示。 |

**校本部图书馆返回样例**，校本部图书馆预约.har#20，00:26:31.483，HTTP 200 / JSON.code=0。

```json
{
  "code": 0,
  "data": [
    {
      "id": "BOOKING_LIB",
      "subject": "<profile.data.name>",
      "templateType": "",
      "beforeNotify": false,
      "abilities": []
    }
  ],
  "noticeMessage": "创建预订成功"
}
```

**24H学习空间返回样例**，24H学习空间预约.har#14，00:32:24.484，HTTP 200 / JSON.code=0。

```json
{
  "code": 0,
  "data": [
    {
      "id": "BOOKING_STATION",
      "subject": "<profile.data.name>",
      "templateType": "",
      "beforeNotify": false,
      "abilities": []
    }
  ],
  "noticeMessage": "创建预订成功"
}
```

**延长智能中心返回样例**，延长智能中心预约.har#26，00:34:06.351，HTTP 200 / JSON.code=0。

```json
{
  "code": 0,
  "data": [
    {
      "id": "BOOKING_SEAT",
      "subject": "<redacted>",
      "templateType": "",
      "beforeNotify": false,
      "abilities": []
    }
  ],
  "noticeMessage": "创建预订成功"
}
```

**科学与艺术中心返回样例**，科学与艺术中心预约.har#25，00:35:44.954，HTTP 200 / JSON.code=0。

```json
{
  "code": 0,
  "data": [
    {
      "id": "BOOKING_CS",
      "subject": "<profile.data.name>",
      "templateType": "",
      "beforeNotify": false,
      "abilities": []
    }
  ],
  "noticeMessage": "创建meetingType.CS_SEAT成功"
}
```

**校本部图书馆返回样例**，校本部图书馆预约.har#39，00:26:04.232，HTTP 200 / JSON.code=200。

```json
{
  "code": 200,
  "warnMessage": "不能预订超过2天的预订"
}
```

**校本部图书馆返回样例**，校本部图书馆预约.har#34，00:26:13.569，HTTP 200 / JSON.code=200。

```json
{
  "code": 200,
  "warnMessage": "同一用户10秒只能提交一次",
  "message": "同一用户10秒只能提交一次"
}
```

**科学与艺术中心返回样例**，科学与艺术中心预约.har#34，00:35:20.934，HTTP 200 / JSON.code=200。

```json
{
  "code": 200,
  "warnMessage": "不能预订超过8小时的meetingtype.cs_seat"
}
```

**科学与艺术中心返回样例**，科学与艺术中心预约.har#28，00:35:29.615，HTTP 200 / JSON.code=200。

```json
{
  "code": 200,
  "warnMessage": "同一用户10秒只能提交一次",
  "message": "同一用户10秒只能提交一次"
}
```

来源：校本部图书馆预约.har#39、校本部图书馆预约.har#34、校本部图书馆预约.har#20、24H学习空间预约.har#14、延长智能中心预约.har#26、科学与艺术中心预约.har#34、科学与艺术中心预约.har#28、科学与艺术中心预约.har#25。

### 4.7 预约详情

**GET `/api/v3/bookings/{bookingId}`**。最终预约时间以此接口和 recent 返回值为准；abilities 用于判断可执行操作。 本次调用 4 次，HTTP 状态 200，JSON.code 捕获值 0。

| 位置 | 参数 | 类型 | 值或格式 | 来源与说明 |
| --- | --- | --- | --- | --- |
| path | `bookingId` | string | BOOKING_LIB | 来自创建响应 data[0].id 或 recent.data[].id，是预约 ID，不是座位资源 ID。示例为脱敏别名。 |
| query | `showChecks` | boolean | True | 图书馆、24H 的详情请求使用 true，另两类未使用。仅与 checkins 字段出现有关联，未验证独立效果。 |

**完整捕获返回字段**

| JSON 字段路径 | 捕获类型 | 说明 |
| --- | --- | --- |
| `code` | `integer` | HAR：0 为业务成功，200 为业务拒绝；与 HTTP 状态码不同。 |
| `data` | `object` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.success` | `boolean` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.id` | `string` | profile 时是用户 ID；区域详情时是 areaId；预约详情时是 bookingId。 |
| `data.subject` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.ownerId` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.ownerName` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.ownerMobile` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.ownerPhone` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.ownerPosition` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.ownerDeptId` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.clientType` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.meetingInfra` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.ownerDeptUpStreamId` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.ownerUpStreamId` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.ownerUpstreamId` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.ownerDeptName` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.ownerJobNumber` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.ownerUserNamePinYin` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingUserId` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingUsernamePinYin` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingUserUpStreamId` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingUserDeptUpStreamId` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingUserName` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.bookingUserShowName` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.beginTime` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.endTime` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.duration` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.roomId` | `string` | 座位资源 ID，不是预约 ID。 |
| `data.roomName` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.officeAreaId` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.officeAreaName` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.allOfficeAreaName` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.copyToMembers` | `array<unknown>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.roomNeedApproved` | `boolean` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.templateType` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.receptionId` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.receptionName` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.receptionMobile` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.memberNumbers` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.customFormIds` | `array<unknown>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.roomType` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.status` | `string` | OPEN 不等于已签到；finish 后捕获状态也可为 CANCEL。 |
| `data.workflow` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.statusLabel` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.needCheckin` | `boolean` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.joinStatus` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.checkinStatus` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.currentUserCheckinStatus` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.checkedStatus` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.meetingRepeatType` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.members` | `array<object>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.members[]` | `object` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.members[].id` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.members[].name` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.members[].namePinyin` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.members[].joinStatus` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.members[].joinAt` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.members[].checkinStatus` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.members[].checkAt` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.commentCount` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.meetingType` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.qrCodeUrl` | `string` | 二维码图片 URL，仅有引用，响应和方法未捕获。 |
| `data.qrCodeValue` | `string` | 签到页面 URL；含实际签到令牌，示例已脱敏。 |
| `data.qrCodeTitle` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.memberCount` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.busyCssName` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.events` | `array<unknown>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.meetingOrderLists` | `array<unknown>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.checkedInPeopleCount` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.confirmedPeopleCount` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.refusedPeopleCount` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.createdAt` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.updatedAt` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.meetingFiles` | `array<unknown>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.beforeNotify` | `boolean` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.facilityNames` | `array<unknown>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.nowAvailableDelayMinutes` | `integer` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.checkins` | `array<unknown>` | 图书馆/24H 出现空数组，元素结构未知。 |
| `data.form` | `array<string>` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.showExtras` | `boolean` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.showExtrasSwitch` | `boolean` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.abilities` | `array<string>` | 详情的操作能力，例如 cancel、waitOpen、close；不能用状态字段单独替代。 |
| `data.otherSeatList` | `array<unknown>` | 捕获字段；未验证其在全部场景是否必返。 |

**校本部图书馆返回样例**，校本部图书馆预约.har#12，00:26:33.553，HTTP 200 / JSON.code=0。

```json
{
  "code": 0,
  "data": {
    "success": true,
    "id": "BOOKING_LIB",
    "subject": "<profile.data.name>",
    "ownerId": "<profile.data.id>",
    "ownerName": "<profile.data.name>",
    "ownerMobile": "<redacted>",
    "ownerPhone": "<redacted>",
    "ownerPosition": "",
    "ownerDeptId": "<redacted>",
    "clientType": "SYS",
    "meetingInfra": "",
    "ownerDeptUpStreamId": "<redacted>",
    "ownerUpStreamId": "<redacted>",
    "ownerUpstreamId": "<redacted>",
    "ownerDeptName": "<redacted>",
    "ownerJobNumber": "<redacted>",
    "ownerUserNamePinYin": "<redacted>",
    "bookingUserId": "<profile.data.id>",
    "bookingUsernamePinYin": "<redacted>",
    "bookingUserUpStreamId": "<redacted>",
    "bookingUserDeptUpStreamId": "<redacted>",
    "bookingUserName": "<profile.data.name>",
    "bookingUserShowName": "<profile.data.name>",
    "beginTime": "2026-10-03 08:30:00",
    "endTime": "2026-10-03 09:30:00",
    "duration": 60,
    "roomId": "2RLARqe9egAFzej4ALBizj",
    "roomName": "2E015",
    "officeAreaId": "KRdcGiyK99gzrqCepi91Cv",
    "officeAreaName": "二楼东侧",
    "allOfficeAreaName": "校本部图书馆自修区-二楼东侧",
    "copyToMembers": [],
    "roomNeedApproved": false,
    "templateType": "",
    "receptionId": "",
    "receptionName": "",
    "receptionMobile": "",
    "memberNumbers": 1,
    "customFormIds": [],
    "roomType": "LIB_SEAT",
    "status": "OPEN",
    "workflow": "STAND",
    "statusLabel": "正常",
    "needCheckin": true,
    "joinStatus": "Y",
    "checkinStatus": "N",
    "currentUserCheckinStatus": "N",
    "checkedStatus": "N",
    "meetingRepeatType": "NONE",
    "members": [
      {
        "id": "<profile.data.id>",
        "name": "<profile.data.name>",
        "namePinyin": "<redacted>",
        "joinStatus": "Y",
        "joinAt": "2026-10-03 00:26:33",
        "checkinStatus": "N",
        "checkAt": ""
      }
    ],
    "commentCount": 0,
    "meetingType": "STANDARD",
    "qrCodeUrl": "/api/room/qrcode/meeting/{bookingId}.png?ts={ts}",
    "qrCodeValue": "/m/b/{bookingId}/c/{checkinToken}?corpAppId={corpAppId}",
    "qrCodeTitle": "微信扫码签到",
    "memberCount": 1,
    "busyCssName": "busy busy-for-me",
    "events": [],
    "meetingOrderLists": [],
    "checkedInPeopleCount": 0,
    "confirmedPeopleCount": 1,
    "refusedPeopleCount": 0,
    "createdAt": "2026-10-03 00:26:33",
    "updatedAt": "2026-10-03 00:26:33",
    "meetingFiles": [],
    "beforeNotify": false,
    "facilityNames": [],
    "nowAvailableDelayMinutes": 483,
    "checkins": [],
    "form": [
      "subject",
      "meetingPlace",
      "meetingStarTime",
      "meetingEndTime",
      "inviter",
      "inviterMobile",
      "joinMember",
      "copyUser"
    ],
    "showExtras": false,
    "showExtrasSwitch": false,
    "abilities": [
      "cancel",
      "comment",
      "edit",
      "edit-member",
      "set-not-public",
      "share",
      "view",
      "waitOpen"
    ]
  }
}
```

**24H学习空间返回样例**，24H学习空间预约.har#9，00:32:26.305，HTTP 200 / JSON.code=0。

```json
{
  "code": 0,
  "data": {
    "success": true,
    "id": "BOOKING_STATION",
    "subject": "<profile.data.name>",
    "ownerId": "<profile.data.id>",
    "ownerName": "<profile.data.name>",
    "ownerMobile": "<redacted>",
    "ownerPhone": "<redacted>",
    "ownerPosition": "",
    "ownerDeptId": "<redacted>",
    "clientType": "SYS",
    "meetingInfra": "",
    "ownerDeptUpStreamId": "<redacted>",
    "ownerUpStreamId": "<redacted>",
    "ownerUpstreamId": "<redacted>",
    "ownerDeptName": "<redacted>",
    "ownerJobNumber": "<redacted>",
    "ownerUserNamePinYin": "<redacted>",
    "bookingUserId": "<profile.data.id>",
    "bookingUsernamePinYin": "<redacted>",
    "bookingUserUpStreamId": "<redacted>",
    "bookingUserDeptUpStreamId": "<redacted>",
    "bookingUserName": "<profile.data.name>",
    "bookingUserShowName": "<profile.data.name>",
    "beginTime": "2026-10-03 00:33:00",
    "endTime": "2026-10-03 01:30:00",
    "duration": 57,
    "roomId": "4q4z61HkGbJZnK89ejv9wU",
    "roomName": "B-034",
    "officeAreaId": "DsNjTXf8icSMh3SXB5HPge",
    "officeAreaName": "B",
    "allOfficeAreaName": "图书馆24小时自习区-B",
    "copyToMembers": [],
    "roomNeedApproved": false,
    "templateType": "",
    "receptionId": "",
    "receptionName": "",
    "receptionMobile": "",
    "memberNumbers": 1,
    "customFormIds": [],
    "roomType": "STATION",
    "status": "OPEN",
    "workflow": "STAND",
    "statusLabel": "正常",
    "needCheckin": true,
    "joinStatus": "Y",
    "checkinStatus": "N",
    "currentUserCheckinStatus": "N",
    "checkedStatus": "N",
    "meetingRepeatType": "NONE",
    "members": [
      {
        "id": "<profile.data.id>",
        "name": "<profile.data.name>",
        "namePinyin": "<redacted>",
        "joinStatus": "Y",
        "joinAt": "2026-10-03 00:32:26",
        "checkinStatus": "N",
        "checkAt": ""
      }
    ],
    "commentCount": 0,
    "meetingType": "STANDARD",
    "qrCodeUrl": "/api/room/qrcode/meeting/{bookingId}.png?ts={ts}",
    "qrCodeValue": "/m/b/{bookingId}/c/{checkinToken}?corpAppId={corpAppId}",
    "qrCodeTitle": "微信扫码签到",
    "memberCount": 1,
    "busyCssName": "busy busy-for-me",
    "events": [],
    "meetingOrderLists": [],
    "checkedInPeopleCount": 0,
    "confirmedPeopleCount": 1,
    "refusedPeopleCount": 0,
    "createdAt": "2026-10-03 00:32:26",
    "updatedAt": "2026-10-03 00:32:26",
    "meetingFiles": [],
    "beforeNotify": false,
    "facilityNames": [],
    "nowAvailableDelayMinutes": 450,
    "checkins": [],
    "form": [
      "subject",
      "meetingPlace",
      "meetingStarTime",
      "meetingEndTime",
      "inviter",
      "inviterMobile",
      "joinMember",
      "copyUser"
    ],
    "showExtras": false,
    "showExtrasSwitch": false,
    "abilities": [
      "close",
      "comment",
      "edit",
      "edit-member",
      "set-not-public",
      "share",
      "show-checkin",
      "view"
    ]
  }
}
```

**延长智能中心返回样例**，延长智能中心预约.har#18，00:34:08.202，HTTP 200 / JSON.code=0。

```json
{
  "code": 0,
  "data": {
    "success": true,
    "id": "BOOKING_SEAT",
    "subject": "<redacted>",
    "ownerId": "<profile.data.id>",
    "ownerName": "<profile.data.name>",
    "ownerMobile": "<redacted>",
    "ownerPhone": "<redacted>",
    "ownerPosition": "",
    "ownerDeptId": "<redacted>",
    "clientType": "SYS",
    "meetingInfra": "",
    "ownerDeptUpStreamId": "<redacted>",
    "ownerUpStreamId": "<redacted>",
    "ownerUpstreamId": "<redacted>",
    "ownerDeptName": "<redacted>",
    "ownerJobNumber": "<redacted>",
    "ownerUserNamePinYin": "<redacted>",
    "bookingUserId": "<profile.data.id>",
    "bookingUsernamePinYin": "<redacted>",
    "bookingUserUpStreamId": "<redacted>",
    "bookingUserDeptUpStreamId": "<redacted>",
    "bookingUserName": "<profile.data.name>",
    "bookingUserShowName": "<profile.data.name>",
    "beginTime": "2026-10-03 09:30:00",
    "endTime": "2026-10-03 10:30:00",
    "duration": 60,
    "roomId": "FLiAcmbCuHCEkRu5SH1rhX",
    "roomName": "11-3",
    "officeAreaId": "KbuCBLACKv74KmiBqE51z6",
    "officeAreaName": "B",
    "allOfficeAreaName": "智能信息中心智慧共享空间-B",
    "copyToMembers": [],
    "roomNeedApproved": false,
    "templateType": "",
    "receptionId": "",
    "receptionName": "",
    "receptionMobile": "",
    "memberNumbers": 1,
    "customFormIds": [],
    "roomType": "SEAT",
    "status": "OPEN",
    "workflow": "STAND",
    "statusLabel": "正常",
    "needCheckin": true,
    "joinStatus": "Y",
    "checkinStatus": "N",
    "currentUserCheckinStatus": "N",
    "checkedStatus": "N",
    "meetingRepeatType": "NONE",
    "members": [
      {
        "id": "<profile.data.id>",
        "name": "<profile.data.name>",
        "namePinyin": "<redacted>",
        "joinStatus": "Y",
        "joinAt": "2026-10-03 00:34:07",
        "checkinStatus": "N",
        "checkAt": ""
      }
    ],
    "commentCount": 0,
    "meetingType": "STANDARD",
    "qrCodeUrl": "/api/room/qrcode/meeting/{bookingId}.png?ts={ts}",
    "qrCodeValue": "/m/b/{bookingId}/c/{checkinToken}?corpAppId={corpAppId}",
    "qrCodeTitle": "微信扫码签到",
    "memberCount": 1,
    "busyCssName": "busy busy-for-me",
    "events": [],
    "meetingOrderLists": [],
    "checkedInPeopleCount": 0,
    "confirmedPeopleCount": 1,
    "refusedPeopleCount": 0,
    "createdAt": "2026-10-03 00:34:07",
    "updatedAt": "2026-10-03 00:34:07",
    "otherSeatList": [],
    "meetingFiles": [],
    "beforeNotify": false,
    "facilityNames": [],
    "nowAvailableDelayMinutes": 535,
    "form": [
      "subject",
      "meetingPlace",
      "meetingStarTime",
      "meetingEndTime",
      "inviter",
      "inviterMobile",
      "joinMember",
      "copyUser"
    ],
    "showExtras": false,
    "showExtrasSwitch": false,
    "abilities": [
      "cancel",
      "comment",
      "edit",
      "edit-member",
      "set-not-public",
      "share",
      "view",
      "waitOpen"
    ]
  }
}
```

**科学与艺术中心返回样例**，科学与艺术中心预约.har#17，00:35:47.695，HTTP 200 / JSON.code=0。

```json
{
  "code": 0,
  "data": {
    "success": true,
    "id": "BOOKING_CS",
    "subject": "<profile.data.name>",
    "ownerId": "<profile.data.id>",
    "ownerName": "<profile.data.name>",
    "ownerMobile": "<redacted>",
    "ownerPhone": "<redacted>",
    "ownerPosition": "",
    "ownerDeptId": "<redacted>",
    "clientType": "SYS",
    "meetingInfra": "",
    "ownerDeptUpStreamId": "<redacted>",
    "ownerUpStreamId": "<redacted>",
    "ownerUpstreamId": "<redacted>",
    "ownerDeptName": "<redacted>",
    "ownerJobNumber": "<redacted>",
    "ownerUserNamePinYin": "<redacted>",
    "bookingUserId": "<profile.data.id>",
    "bookingUsernamePinYin": "<redacted>",
    "bookingUserUpStreamId": "<redacted>",
    "bookingUserDeptUpStreamId": "<redacted>",
    "bookingUserName": "<profile.data.name>",
    "bookingUserShowName": "<profile.data.name>",
    "beginTime": "2026-10-03 09:00:00",
    "endTime": "2026-10-03 14:00:00",
    "duration": 300,
    "roomId": "ECsWTCtuEoMSq9DqD8ZAPV",
    "roomName": "A-27",
    "officeAreaId": "VQyeEokNwJnq7h8sVwmnfg",
    "officeAreaName": "学生共享创作中心A",
    "allOfficeAreaName": "科学与艺术中心-学生共享创作中心A",
    "copyToMembers": [],
    "roomNeedApproved": false,
    "templateType": "",
    "receptionId": "",
    "receptionName": "",
    "receptionMobile": "",
    "memberNumbers": 1,
    "customFormIds": [],
    "roomType": "CS_SEAT",
    "status": "OPEN",
    "workflow": "STAND",
    "statusLabel": "正常",
    "needCheckin": true,
    "joinStatus": "Y",
    "checkinStatus": "N",
    "currentUserCheckinStatus": "N",
    "checkedStatus": "N",
    "meetingRepeatType": "NONE",
    "members": [
      {
        "id": "<profile.data.id>",
        "name": "<profile.data.name>",
        "namePinyin": "<redacted>",
        "joinStatus": "Y",
        "joinAt": "2026-10-03 00:35:46",
        "checkinStatus": "N",
        "checkAt": ""
      }
    ],
    "commentCount": 0,
    "meetingType": "STANDARD",
    "qrCodeUrl": "/api/room/qrcode/meeting/{bookingId}.png?ts={ts}",
    "qrCodeValue": "/m/b/{bookingId}/c/{checkinToken}?corpAppId={corpAppId}",
    "qrCodeTitle": "微信扫码签到",
    "memberCount": 1,
    "busyCssName": "busy busy-for-me",
    "events": [],
    "meetingOrderLists": [],
    "checkedInPeopleCount": 0,
    "confirmedPeopleCount": 1,
    "refusedPeopleCount": 0,
    "createdAt": "2026-10-03 00:35:46",
    "updatedAt": "2026-10-03 00:35:46",
    "meetingFiles": [],
    "beforeNotify": false,
    "facilityNames": [],
    "nowAvailableDelayMinutes": 504,
    "form": [
      "subject",
      "meetingPlace",
      "meetingStarTime",
      "meetingEndTime",
      "inviter",
      "inviterMobile",
      "joinMember",
      "copyUser"
    ],
    "showExtras": false,
    "showExtrasSwitch": false,
    "abilities": [
      "cancel",
      "comment",
      "edit",
      "edit-member",
      "set-not-public",
      "share",
      "view",
      "waitOpen"
    ]
  }
}
```

来源：校本部图书馆预约.har#12、24H学习空间预约.har#9、延长智能中心预约.har#18、科学与艺术中心预约.har#17。

### 4.8 取消预约

**DELETE `/api/v3/bookings/{bookingId}/cancel`**。图书馆、延长、科艺三段实际调用；随后 recent 的该预约为 CANCEL，abilities 为空。 本次调用 3 次，HTTP 状态 200，JSON.code 捕获值 0。

| 位置 | 参数 | 类型 | 值或格式 | 来源与说明 |
| --- | --- | --- | --- | --- |
| path | `bookingId` | string | BOOKING_LIB | 来自创建响应 data[0].id 或 recent.data[].id，是预约 ID，不是座位资源 ID。示例为脱敏别名。 |

**完整捕获返回字段**

| JSON 字段路径 | 捕获类型 | 说明 |
| --- | --- | --- |
| `code` | `integer` | HAR：0 为业务成功，200 为业务拒绝；与 HTTP 状态码不同。 |
| `data` | `object` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.success` | `boolean` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.templateType` | `string` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.beforeNotify` | `boolean` | 捕获字段；未验证其在全部场景是否必返。 |
| `data.abilities` | `array<unknown>` | 详情的操作能力，例如 cancel、waitOpen、close；不能用状态字段单独替代。 |
| `noticeMessage` | `string` | 业务操作提示。 |

**校本部图书馆返回样例**，校本部图书馆预约.har#5，00:26:46.228，HTTP 200 / JSON.code=0。

```json
{
  "code": 0,
  "data": {
    "success": true,
    "templateType": "",
    "beforeNotify": false,
    "abilities": []
  },
  "noticeMessage": "取消预订成功"
}
```

**延长智能中心返回样例**，延长智能中心预约.har#3，00:34:25.456，HTTP 200 / JSON.code=0。

```json
{
  "code": 0,
  "data": {
    "success": true,
    "templateType": "",
    "beforeNotify": false,
    "abilities": []
  },
  "noticeMessage": "取消预订成功"
}
```

**科学与艺术中心返回样例**，科学与艺术中心预约.har#3，00:35:57.264，HTTP 200 / JSON.code=0。

```json
{
  "code": 0,
  "data": {
    "success": true,
    "templateType": "",
    "beforeNotify": false,
    "abilities": []
  },
  "noticeMessage": "取消meetingType.CS_SEAT成功"
}
```

来源：校本部图书馆预约.har#5、延长智能中心预约.har#3、科学与艺术中心预约.har#3。

### 4.9 提前结束预约

**PUT `/api/v3/bookings/{bookingId}/finish`**。24H 实际调用；详情此前有 close 能力。最终 recent 为 CANCEL，duration=0，origEndAt 保留原结束时间。 本次调用 1 次，HTTP 状态 200，JSON.code 捕获值 0。

| 位置 | 参数 | 类型 | 值或格式 | 来源与说明 |
| --- | --- | --- | --- | --- |
| path | `bookingId` | string | BOOKING_LIB | 来自创建响应 data[0].id 或 recent.data[].id，是预约 ID，不是座位资源 ID。示例为脱敏别名。 |

**完整捕获返回字段**

| JSON 字段路径 | 捕获类型 | 说明 |
| --- | --- | --- |
| `code` | `integer` | HAR：0 为业务成功，200 为业务拒绝；与 HTTP 状态码不同。 |
| `noticeMessage` | `string` | 业务操作提示。 |
| `message` | `string` | 捕获字段；未验证其在全部场景是否必返。 |

**24H学习空间返回样例**，24H学习空间预约.har#2，00:32:35.607，HTTP 200 / JSON.code=0。

```json
{
  "code": 0,
  "noticeMessage": "提前结束预订成功",
  "message": "提前结束预订成功"
}
```

来源：24H学习空间预约.har#2。

## 5 四个场馆的区域 资源与规则

以下是选中区域详情配置，不能用 overview 的通用配置替代。座位数量代表本次访问的区域，不能当作整个场馆容量。

| 系统 | areaId | 区域 | 座位数 | 时段 | 间隔分钟 | 最长分钟 | bookingLimitDays | 日期项数 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 校本部图书馆 | `KRdcGiyK99gzrqCepi91Cv` | 二楼东侧 | 268 | 08:00—22:00 | 30 | 480 | 1 | 2 |
| 24H学习空间 | `DsNjTXf8icSMh3SXB5HPge` | B | 171 | 00:00—24:00 | 30 | 480 | 1 | 2 |
| 延长智能中心 | `KbuCBLACKv74KmiBqE51z6` | B | 18 | 09:00—18:00 | 15 | 480 | 365 | 30 |
| 科学与艺术中心 | `VQyeEokNwJnq7h8sVwmnfg` | 学生共享创作中心A | 60 | 08:00—22:00 | 60 | 480 | 30 | 30 |

四区域 supportAcrossDayBooking=false、needCheckin=true、enableFixedBooking=false、enableAgentBooking=true。图书馆另有 minDuration=30。24H disablePersonConflict=true，其余 false；其具体服务端效果未经单独验证。24H 和图书馆 bookingLimitDays=1 却可返回两天；延长值为 365 却只返回 30 个日期。图书馆选择 10-05 时数组曾包括 10-04/10-05，但创建仍被两天限制拒绝。日期数组和配置字段不能直接替代创建准入判断。

### 5.1 校本部图书馆选中区域记录

成功座位 `2E015`，roomId=`2RLARqe9egAFzej4ALBizj`，预约别名 `BOOKING_LIB`。最后区域快照证据 校本部图书馆预约.har#19，时间 2026-10-03T00:26:32.777+08:00。该查询发生在创建后、取消或结束前；不代表取消后的实时占用。四区域座位快照共 517 个。

**该系统捕获到的区域列表**

| areaId | 区域名称 | parentId | supportRoomTypes |
| --- | --- | --- | --- |
| `CvT5k6Aivz2riLTRTq2FxM` | 校本部图书馆自修区 |  | LIB_SEAT |
| `KRdcGiyK99gzrqCepi91Cv` | 二楼东侧 | CvT5k6Aivz2riLTRTq2FxM | LIB_SEAT |
| `8DWVvvMnMn6Kvg9qCbNPdi` | 二楼西侧 | CvT5k6Aivz2riLTRTq2FxM | LIB_SEAT |

**选中区域配置与日期**

```json
{
  "bookingTimes": {
    "timeBlockType": "FIXED_BLOCK",
    "supportAcrossDayBooking": false,
    "suggestStartTime": "08:30",
    "suggestEndTime": "09:30",
    "startHour": 8,
    "endHour": 22,
    "morningEndHour": 12,
    "afternoonStartHour": 12,
    "maxDuration": 480,
    "minDuration": 30,
    "configMaxDuration": 480,
    "meetingInterval": 30,
    "bookingLimitDays": 1,
    "needCheckin": true,
    "disablePersonConflict": false,
    "enableFixedBooking": false,
    "enableAgentBooking": true
  },
  "bookingDays": [
    "2026-10-03",
    "2026-10-04"
  ]
}
```

### 5.2 24H学习空间选中区域记录

成功座位 `B-034`，roomId=`4q4z61HkGbJZnK89ejv9wU`，预约别名 `BOOKING_STATION`。最后区域快照证据 24H学习空间预约.har#12，时间 2026-10-03T00:32:25.753+08:00。该查询发生在创建后、取消或结束前；不代表取消后的实时占用。四区域座位快照共 517 个。

**该系统捕获到的区域列表**

| areaId | 区域名称 | parentId | supportRoomTypes |
| --- | --- | --- | --- |
| `7pcMcUCRxXE6fzXhLp7za7` | 图书馆24小时自习区 |  | STATION |
| `WyN53UzbmRsLjpR1t1ttWL` | A | 7pcMcUCRxXE6fzXhLp7za7 | STATION |
| `DsNjTXf8icSMh3SXB5HPge` | B | 7pcMcUCRxXE6fzXhLp7za7 | STATION |
| `YLyBwnQ7frVRt49UMSCtnX` | C | 7pcMcUCRxXE6fzXhLp7za7 | STATION |

**选中区域配置与日期**

```json
{
  "bookingTimes": {
    "timeBlockType": "FIXED_BLOCK",
    "supportAcrossDayBooking": false,
    "suggestStartTime": "00:30",
    "suggestEndTime": "01:30",
    "startHour": 0,
    "endHour": 24,
    "morningEndHour": 12,
    "afternoonStartHour": 12,
    "maxDuration": 480,
    "configMaxDuration": 480,
    "meetingInterval": 30,
    "bookingLimitDays": 1,
    "needCheckin": true,
    "disablePersonConflict": true,
    "enableFixedBooking": false,
    "enableAgentBooking": true
  },
  "bookingDays": [
    "2026-10-03",
    "2026-10-04"
  ]
}
```

### 5.3 延长智能中心选中区域记录

成功座位 `11-3`，roomId=`FLiAcmbCuHCEkRu5SH1rhX`，预约别名 `BOOKING_SEAT`。最后区域快照证据 延长智能中心预约.har#20，时间 2026-10-03T00:34:07.898+08:00。该查询发生在创建后、取消或结束前；不代表取消后的实时占用。四区域座位快照共 517 个。

**该系统捕获到的区域列表**

| areaId | 区域名称 | parentId | supportRoomTypes |
| --- | --- | --- | --- |
| `4N9ynVts4eU8toDS7qP6qk` | 智能信息中心智慧共享空间 |  | SEAT |
| `KbuCBLACKv74KmiBqE51z6` | B | 4N9ynVts4eU8toDS7qP6qk | SEAT |
| `ENc2vCdpzppbt8zwf1gKJV` | C | 4N9ynVts4eU8toDS7qP6qk | SEAT |
| `77cFiM4BoAtYzzZSkv96PX` | D | 4N9ynVts4eU8toDS7qP6qk | SEAT |

**选中区域配置与日期**

```json
{
  "bookingTimes": {
    "timeBlockType": "FIXED_BLOCK",
    "supportAcrossDayBooking": false,
    "suggestStartTime": "09:30",
    "suggestEndTime": "10:30",
    "startHour": 9,
    "endHour": 18,
    "morningEndHour": 12,
    "afternoonStartHour": 12,
    "maxDuration": 480,
    "configMaxDuration": 480,
    "meetingInterval": 15,
    "bookingLimitDays": 365,
    "needCheckin": true,
    "disablePersonConflict": false,
    "enableFixedBooking": false,
    "enableAgentBooking": true
  },
  "bookingDays": [
    "2026-10-03",
    "2026-10-04",
    "2026-10-05",
    "2026-10-06",
    "2026-10-07",
    "2026-10-08",
    "2026-10-09",
    "2026-10-10",
    "2026-10-11",
    "2026-10-12",
    "2026-10-13",
    "2026-10-14",
    "2026-10-15",
    "2026-10-16",
    "2026-10-17",
    "2026-10-18",
    "2026-10-19",
    "2026-10-20",
    "2026-10-21",
    "2026-10-22",
    "2026-10-23",
    "2026-10-24",
    "2026-10-25",
    "2026-10-26",
    "2026-10-27",
    "2026-10-28",
    "2026-10-29",
    "2026-10-30",
    "2026-10-31",
    "2026-11-01"
  ]
}
```

### 5.4 科学与艺术中心选中区域记录

成功座位 `A-27`，roomId=`ECsWTCtuEoMSq9DqD8ZAPV`，预约别名 `BOOKING_CS`。最后区域快照证据 科学与艺术中心预约.har#22，时间 2026-10-03T00:35:46.254+08:00。该查询发生在创建后、取消或结束前；不代表取消后的实时占用。四区域座位快照共 517 个。

**该系统捕获到的区域列表**

| areaId | 区域名称 | parentId | supportRoomTypes |
| --- | --- | --- | --- |
| `WtgvL1bEPyVVjtdHDVtH4i` | 科学与艺术中心 |  | CS_SEAT |
| `VQyeEokNwJnq7h8sVwmnfg` | 学生共享创作中心A | WtgvL1bEPyVVjtdHDVtH4i | CS_SEAT |
| `SJHRB6yt6K4dWp5NVtrdmA` | 学生共享创作中心B | WtgvL1bEPyVVjtdHDVtH4i | CS_SEAT |
| `HEd61xB2ReQx5E2BkFXtKU` | 超高清技术与艺术创作空间 | WtgvL1bEPyVVjtdHDVtH4i | CS_SEAT |
| `Q6bR3uutP8ttFMQESk6CyB` | 超高清视景制作共享空间 | WtgvL1bEPyVVjtdHDVtH4i | CS_SEAT |

**选中区域配置与日期**

```json
{
  "bookingTimes": {
    "timeBlockType": "FIXED_BLOCK",
    "supportAcrossDayBooking": false,
    "suggestStartTime": "09:00",
    "suggestEndTime": "14:00",
    "startHour": 8,
    "endHour": 22,
    "morningEndHour": 12,
    "afternoonStartHour": 12,
    "maxDuration": 480,
    "configMaxDuration": 480,
    "meetingInterval": 60,
    "bookingLimitDays": 30,
    "needCheckin": true,
    "disablePersonConflict": false,
    "enableFixedBooking": false,
    "enableAgentBooking": true
  },
  "bookingDays": [
    "2026-10-03",
    "2026-10-04",
    "2026-10-05",
    "2026-10-06",
    "2026-10-07",
    "2026-10-08",
    "2026-10-09",
    "2026-10-10",
    "2026-10-11",
    "2026-10-12",
    "2026-10-13",
    "2026-10-14",
    "2026-10-15",
    "2026-10-16",
    "2026-10-17",
    "2026-10-18",
    "2026-10-19",
    "2026-10-20",
    "2026-10-21",
    "2026-10-22",
    "2026-10-23",
    "2026-10-24",
    "2026-10-25",
    "2026-10-26",
    "2026-10-27",
    "2026-10-28",
    "2026-10-29",
    "2026-10-30",
    "2026-10-31",
    "2026-11-01"
  ]
}
```

## 6 一次完整预约链路的客户端设计

### 6.1 状态与数据依赖

登录阶段按第 3 节完成 newsso 认证与 there 回调，再进入移动页面取得 sessionId。业务阶段遵循已捕获的依赖顺序；overview 和区域列表可相邻或并发，没有观测到强制串行依赖。

| 步骤 | 动作 | 输出与下一步依赖 | 判定 |
| --- | --- | --- | --- |
| 1 | 选择系统与入口，完成 SSO/本站会话 | 当前 Cookie jar、移动 HTML.sessionId、roomType | SSO 与本站 Cookie 分域；以当前页面为头来源。 |
| 2 | GET my/profile，再 GET my/bookings/recent | profile.id、profile.name、已有预约 | code=0；用户非匿名；已有列表按 status、时间、abilities 读取。 |
| 3 | overview?day=D 与 areas?begin=D&end=D | 候选日期与区域树 | 不能把 overview 配置覆盖实际区域配置。 |
| 4 | GET areas/{areaId}?begin=完整开始时间&end=完整结束时间 | 当前区间 rooms[]、bookingTimes、资源状态 | 取实际区域配置；选未禁用、可预约的座位。 |
| 5 | POST bookings，rooms/times/subject/meetingMembers | 成功时 data[0].id | HTTP 成功并 JSON.code=0 才进入成功分支。 |
| 6 | 刷新 recent、区域详情、overview；GET bookings/{bookingId} | 服务端最终开始/结束时间、状态、abilities | 服务端可能调整请求开始时间；刷新动作本身不表示创建成功。 |
| 7 | 按详情能力选择 cancel 或 finish | 操作响应与最终记录 | 只执行用户所选择的动作；finish 对应 close 能力的实测样本。 |
| 8 | GET recent 核对刚才 bookingId | 最终状态、时间、duration、origEndAt | 不能固定假设 finish 最终为 FINISHED。 |

参数来源链为 `areaId ← 区域列表.data[].id`、`rooms[] ← 区域详情.data.rooms[]`、`subject ← profile.data.name`、`meetingMembers ← [profile.data.id]`、`bookingId ← 成功创建.data[0].id`。四系统八次创建的个人字段映射已逐条一致；roomId 与 bookingId 不可互换。

![预约流程](assets/there-flow.svg)

### 6.2 图书馆实例的完整业务序列

以下固定采用捕获成功样本的日期和座位，仅用于解释接口衔接。运行时应重新查询当前规则、资源与可用日期，不能把 2026-10-03 的快照当作实时状态。

```http
GET /mobile/libseat
  → 保存 HTML.sessionId 及当前本站 Cookie
GET /api/v3/my/profile
GET /api/v3/my/bookings/recent
GET /api/v3/booking-status/overview?day=2026-10-03
GET /api/v3/booking-status/areas?begin=2026-10-03&end=2026-10-03
GET /api/v3/booking-status/areas/KRdcGiyK99gzrqCepi91Cv?begin=2026-10-03%2008%3A30&end=2026-10-03%2009%3A30
POST /api/v3/bookings
  → JSON.code=0 后取 data[0].id
GET /api/v3/my/bookings/recent
GET /api/v3/bookings/BOOKING_LIB?showChecks=true
  → 实际返回 cancel / waitOpen 能力
DELETE /api/v3/bookings/BOOKING_LIB/cancel
GET /api/v3/my/bookings/recent
  → BOOKING_LIB 最终 status=CANCEL
```

创建体如下，使用刚查询到的完整座位对象；占位符由当前 profile 填入。

```json
{
  "rooms": [
    {
      "id": "2RLARqe9egAFzej4ALBizj",
      "name": "2E015",
      "officeAreaId": "KRdcGiyK99gzrqCepi91Cv",
      "disabled": false,
      "showOrder": 15,
      "isBusy": false,
      "isBooked": false,
      "abilities": [
        "booking"
      ]
    }
  ],
  "times": [
    {
      "startDate": "2026-10-03",
      "startTime": "08:30",
      "endDate": "2026-10-03",
      "endTime": "09:30"
    }
  ],
  "subject": "<profile.data.name>",
  "meetingMembers": [
    "<profile.data.id>"
  ]
}
```

### 6.3 通用实现伪代码

下面是业务组织伪代码，不是已执行的客户端，也不增加新端点。api 函数负责附公共参数、标准 URL 编码和 Cookie；参数类型以第 4 节为准。

```python
ctx = login_newsso_and_redeem_there()       # 第 3 节，密码/二步或企微分支
page = open_selected_mobile_page(ctx)
ctx.session = page.sessionId
ctx.room_type = selected_system.room_type

profile = api("GET", "/api/v3/my/profile").data
assert profile.isAnonymous is False
recent = api("GET", "/api/v3/my/bookings/recent").data
overview = api("GET", "/api/v3/booking-status/overview", query={"day": day}).data
areas = api("GET", "/api/v3/booking-status/areas", query={"begin": day, "end": day}).data

area = api("GET", f"/api/v3/booking-status/areas/{selected_area_id}",
           query={"begin": begin_datetime, "end": end_datetime}).data
room = select_room_from(area.rooms)         # 当前查询对象，检查禁用与 booking 能力
payload = {"rooms": [room], "times": [{"startDate": start_date,
           "startTime": start_time, "endDate": end_date, "endTime": end_time}],
           "subject": profile.name, "meetingMembers": [profile.id]}

result = api("POST", "/api/v3/bookings", json=payload, check_business=False)
if result.code != 0:
    refresh_recent_and_show_server_message(result)
    stop_without_booking_id()
booking_id = result.data[0].id
refresh_recent_area_and_overview()
detail = api("GET", f"/api/v3/bookings/{booking_id}", query=detail_query_for_system()).data
show_actual_times_status_and_abilities(detail)

if user_action == "cancel" and "cancel" in detail.abilities:
    api("DELETE", f"/api/v3/bookings/{booking_id}/cancel")
elif user_action == "finish" and "close" in detail.abilities:
    api("PUT", f"/api/v3/bookings/{booking_id}/finish")
recent = api("GET", "/api/v3/my/bookings/recent").data
verify_this_booking_in(recent, booking_id)
```

### 6.4 失败与结果核对

创建业务失败保持 HTTP 200，JSON.code=200，可能仅有 warnMessage。样本中有两天限制、八小时限制和同用户十秒一次限制；拒绝后紧接重试也会触发频率错误。客户端设计应锁定并发提交、按服务端提示节流，避免无间隔自动重试。捕获数据未验证精确十秒边界、频率重置策略或幂等键。

网络超时或响应丢失时，创建结果可能未知；这时先查询 recent 核对时间、资源和状态，再决定是否重新提交。此为避免重复预约的客户端处理设计，服务端幂等能力未验证。日期与时长最终以服务端创建/详情为准；24H 样本已发生开始时间调整。

JS 公共客户端包含 401、403、404、502 错误分支：401 导航 /login，403 无权限，404 资源不存在，502 服务端问题。没有这些 HTTP 响应的 HAR 样本，返回正文未知。

实际签到不属于本次成功闭环验证范围。needCheckin=true 和 checkinStatus=N 不能证明已签到；OPEN 也不能证明已签到。只知道第 7 节的调用/URL 线索，不给出未捕获签到条件或签到成功返回体。

## 7 已有出处但未实际调用的路由与 URL

### 7.1 图书馆签到调用与移动入口

图书馆 HAR #7/#15/#49 的脚本直接声明 **POST `/api/v3/bookings/{bookingId}/checkInUse`**，使用 client.post(url)，没有第二个 body 参数。bookingId 来自创建或已有记录，登录上下文沿用当前客户端；真正入口条件、位置/时间校验、响应体和成功码均未知。只在图书馆 JS 中发现该调用，不能据此宣称四类型均可签到。

四移动入口的 GET 都有 HTML 请求响应，页面中的 loginUser/sessionId/onlyShowAreaId 与七类型配置可见。没有额外 query 参数证据，onlyShowAreaId="all" 是页面配置。HTML 不采用 JSON API 返回体。

### 7.2 只知道路径或 URL 的七项来源记录

以下不声明 HTTP 方法，不纳入 OpenAPI paths 的操作数量。它们来自源码字符串、响应 URL 或项目路径名，保留来源和 URL 参数；未提供的请求/返回体明确留空。

| 主机 | 路径或 URL 模式 | 已知 URL 参数 | 来源及未知项 |
| --- | --- | --- | --- |
| there.shu.edu.cn | `/api/room/qrcode/meeting/{bookingId}.png` | ts | 详情 qrCodeUrl；只知图片地址，未请求。 |
| there.shu.edu.cn | `/m/b/{bookingId}/c/{checkinToken}` | corpAppId | 详情 qrCodeValue；包含签到令牌，不能推定公开访问或签到效果。 |
| there.shu.edu.cn | `/api/v2.0/my-meetings` | 未知 | 项目 README 记载登录后的 Web 路径，方法/参数/返回未知。 |
| there.shu.edu.cn | `/api/v2.0/settings` | 未知 | 同上。 |
| there.shu.edu.cn | `/api/v2.0/my-stats` | 未知 | 同上。 |
| open.work.weixin.qq.com | `/wwopen/sso/qrImg` | key | 项目构造二维码图 URL，未实际 GET 或捕获响应。 |
| open.work.weixin.qq.com | `/wwopen/sso/confirm2` | k、notretry=yes | 项目构造确认页 URL，未实际请求或捕获响应。 |

v2 与 v3 均出现在 there 服务面资料中，但没有两个版本的字段、权限或操作映射证据，不能将 my-meetings 套用 v3 bookings 的 schema。脚本 apiServiceHost 的 hyshi.bayrand.com/api/v2.0 默认值不作为本站实际服务器。

### 7.3 能力字段与接口证据的边界

样本含 commentCount 以及编辑、成员、分享等 abilities，也有固定/代预约配置。这些字段保留在完整返回字段表，未给没有方法与路径证据的功能分配新端点。ROOM/SEAT2/STATION2 同样只保留配置来源。

## 8 四段实测预约链与全部创建尝试

下表全部为北京时间，括号中的 `#N` 是相应 HAR 的原始序号。创建阶段保留了失败和重试，后台资源及监控请求不混入业务步骤。

### 8.1 校本部图书馆

入口 `/mobile/libseat`，实际资源类型 `LIB_SEAT`。

| 时间 | 证据 | 行为 / 结果 | 请求 |
| --- | --- | --- | --- |
| 00:25:30.416 | #69 | 进入图书馆页面 | GET `/mobile/libseat` |
| 00:25:31.686 | #68 | 取当前用户 | GET `/api/v3/my/profile` |
| 00:25:31.897 | #66 | 取最近预约：空 | GET `/api/v3/my/bookings/recent` |
| 00:25:45.902 | #57 | 取区域列表 | GET `/api/v3/booking-status/areas` |
| 00:25:45.940 | #67 | 取日期概览 | GET `/api/v3/booking-status/overview` |
| 00:25:54.358 | #47 | 选择二楼东侧，日期 10-05 | GET `/api/v3/booking-status/areas/KRdcGiyK99gzrqCepi91Cv` |
| 00:26:01.216 | #40 | 查询 10-05 09:00—12:00 | GET `/api/v3/booking-status/areas/KRdcGiyK99gzrqCepi91Cv` |
| 00:26:04.232 | #39 | 提交 2E009：日期限制拒绝 | POST `/api/v3/bookings` |
| 00:26:13.569 | #34 | 9.337 秒后再次提交：10 秒限制拒绝 | POST `/api/v3/bookings` |
| 00:26:24.391 | #26 | 切换到 10-03 | GET `/api/v3/booking-status/areas/KRdcGiyK99gzrqCepi91Cv` |
| 00:26:28.739 | #21 | 查询 08:30—09:30 | GET `/api/v3/booking-status/areas/KRdcGiyK99gzrqCepi91Cv` |
| 00:26:31.483 | #20 | 提交 2E015：成功 BOOKING_LIB | POST `/api/v3/bookings` |
| 00:26:32.778 | #17 | 最近预约出现 OPEN | GET `/api/v3/my/bookings/recent` |
| 00:26:33.553 | #12 | 预约详情：cancel / waitOpen 能力 | GET `/api/v3/bookings/BOOKING_LIB` |
| 00:26:46.228 | #5 | 取消：成功 | DELETE `/api/v3/bookings/BOOKING_LIB/cancel` |
| 00:26:47.377 | #4 | 刷新最近预约：CANCEL | GET `/api/v3/my/bookings/recent` |

图书馆两次失败不会生成预约 ID。最终成功的是 10-03 08:30—09:30 的 2E015，而不是 10-05 的 2E009。首次失败与第二次失败之间为 9.337 秒，与“同一用户10秒只能提交一次”一致。

### 8.2 24H学习空间

入口 `/mobile/seat2021`，实际资源类型 `STATION`。

| 时间 | 证据 | 行为 / 结果 | 请求 |
| --- | --- | --- | --- |
| 00:32:07.160 | #39 | 进入 24H 页面 | GET `/mobile/seat2021` |
| 00:32:08.477 | #36 | 取当前用户 | GET `/api/v3/my/profile` |
| 00:32:08.743 | #35 | 取最近预约：空 | GET `/api/v3/my/bookings/recent` |
| 00:32:12.413 | #27 | 取日期概览 | GET `/api/v3/booking-status/overview` |
| 00:32:12.449 | #38 | 取区域列表 | GET `/api/v3/booking-status/areas` |
| 00:32:16.290 | #21 | 选择 B 区 | GET `/api/v3/booking-status/areas/DsNjTXf8icSMh3SXB5HPge` |
| 00:32:21.363 | #15 | 查询 00:30—01:30 | GET `/api/v3/booking-status/areas/DsNjTXf8icSMh3SXB5HPge` |
| 00:32:24.484 | #14 | 提交 B-034：成功 BOOKING_STATION | POST `/api/v3/bookings` |
| 00:32:25.751 | #13 | 最近预约出现 OPEN | GET `/api/v3/my/bookings/recent` |
| 00:32:26.305 | #9 | 详情：实际开始时间 00:33，有 close 能力 | GET `/api/v3/bookings/BOOKING_STATION` |
| 00:32:35.607 | #2 | 提前结束：成功 | PUT `/api/v3/bookings/BOOKING_STATION/finish` |
| 00:32:36.707 | #1 | 刷新最近预约：CANCEL，时长 0 | GET `/api/v3/my/bookings/recent` |

请求体是 00:30—01:30，但创建时已在 00:32 左右，服务器返回的开始时间是 00:33，时长 57 分钟。只能确认发生了开始时间调整，不能凭一个样本断言其取整算法。提前结束后 beginTime=endTime=00:33、duration=0、origEndAt=01:30，且最终状态是 CANCEL；因此不能预设 finish 一定返回 FINISHED 状态。

### 8.3 延长智能中心

入口 `/mobile/seat-mgr`，实际资源类型 `SEAT`。

| 时间 | 证据 | 行为 / 结果 | 请求 |
| --- | --- | --- | --- |
| 00:33:41.760 | #67 | 进入延长入口 | GET `/mobile/seat-mgr` |
| 00:33:48.303 | #63 | 取当前用户 | GET `/api/v3/my/profile` |
| 00:33:48.998 | #64 | 取最近预约：空 | GET `/api/v3/my/bookings/recent` |
| 00:33:52.175 | #52 | 取区域列表 | GET `/api/v3/booking-status/areas` |
| 00:33:52.175 | #53 | 取日期概览 | GET `/api/v3/booking-status/overview` |
| 00:33:54.466 | #45 | 切换到 10-04 | GET `/api/v3/booking-status/areas` |
| 00:33:55.324 | #42 | 切换到 10-05 | GET `/api/v3/booking-status/areas` |
| 00:33:58.794 | #32 | 回到 10-03，选择 B 区 | GET `/api/v3/booking-status/areas/KbuCBLACKv74KmiBqE51z6` |
| 00:34:00.964 | #27 | 查询 09:30—10:30 | GET `/api/v3/booking-status/areas/KbuCBLACKv74KmiBqE51z6` |
| 00:34:06.351 | #26 | 提交 11-3：成功 BOOKING_SEAT | POST `/api/v3/bookings` |
| 00:34:07.746 | #25 | 最近预约出现 OPEN | GET `/api/v3/my/bookings/recent` |
| 00:34:08.202 | #18 | 预约详情：cancel / waitOpen 能力 | GET `/api/v3/bookings/BOOKING_SEAT` |
| 00:34:25.456 | #3 | 取消：成功 | DELETE `/api/v3/bookings/BOOKING_SEAT/cancel` |
| 00:34:26.686 | #2 | 刷新最近预约：CANCEL | GET `/api/v3/my/bookings/recent` |

业务响应中的完整区域名称是“智能信息中心智慧共享空间-B”。成功时段为 10-03 09:30—10:30，座位 11-3，随后取消。切换日期后的部分查询属于浏览过程，没有生成对应日期的预约。

### 8.4 科学与艺术中心

入口 `/mobile/csseat`，实际资源类型 `CS_SEAT`。

| 时间 | 证据 | 行为 / 结果 | 请求 |
| --- | --- | --- | --- |
| 00:35:05.694 | #64 | 进入科艺入口 | GET `/mobile/csseat` |
| 00:35:07.011 | #62 | 取当前用户 | GET `/api/v3/my/profile` |
| 00:35:07.230 | #60 | 取最近预约：空 | GET `/api/v3/my/bookings/recent` |
| 00:35:10.300 | #51 | 取日期概览 | GET `/api/v3/booking-status/overview` |
| 00:35:10.336 | #61 | 取区域列表 | GET `/api/v3/booking-status/areas` |
| 00:35:14.202 | #38 | 选择学生共享创作中心A | GET `/api/v3/booking-status/areas/VQyeEokNwJnq7h8sVwmnfg` |
| 00:35:20.934 | #34 | 提交 A-10：9 小时超限 | POST `/api/v3/bookings` |
| 00:35:22.088 | #31 | 查询 09:00—18:00 | GET `/api/v3/booking-status/areas/VQyeEokNwJnq7h8sVwmnfg` |
| 00:35:27.759 | #29 | 改为 09:00—14:00 | GET `/api/v3/booking-status/areas/VQyeEokNwJnq7h8sVwmnfg` |
| 00:35:29.615 | #28 | 8.681 秒后提交 A-21：10 秒限制拒绝 | POST `/api/v3/bookings` |
| 00:35:44.954 | #25 | 15.339 秒后提交 A-27：成功 BOOKING_CS | POST `/api/v3/bookings` |
| 00:35:46.254 | #24 | 最近预约出现 OPEN | GET `/api/v3/my/bookings/recent` |
| 00:35:47.695 | #17 | 预约详情：cancel / waitOpen 能力 | GET `/api/v3/bookings/BOOKING_CS` |
| 00:35:57.264 | #3 | 取消：成功 | DELETE `/api/v3/bookings/BOOKING_CS/cancel` |
| 00:35:58.331 | #2 | 刷新最近预约：CANCEL | GET `/api/v3/my/bookings/recent` |

最初选择的 09:00—18:00 为 9 小时，即使区域查询显示座位可选，创建仍因超过 8 小时被拒绝。8.681 秒后的 5 小时请求又触发频率限制；最后换 A-27 成功。拒绝的请求也处于后续提交频率判断之内，与本次样本一致。

### 8.5 全部八次创建尝试

| 场馆 | 证据 | 提交时间 | 座位 | 申请时段 | code | 结果 |
| --- | --- | --- | --- | --- | --- | --- |
| 校本部图书馆 | #39 | 00:26:04.232 | 2E009 | 2026-10-05 09:00—12:00 | 200 | 不能预订超过2天的预订 |
| 校本部图书馆 | #34 | 00:26:13.569 | 2E009 | 2026-10-05 09:00—12:00 | 200 | 同一用户10秒只能提交一次 |
| 校本部图书馆 | #20 | 00:26:31.483 | 2E015 | 2026-10-03 08:30—09:30 | 0 | 创建预订成功 |
| 24H学习空间 | #14 | 00:32:24.484 | B-034 | 2026-10-03 00:30—01:30 | 0 | 创建预订成功 |
| 延长智能中心 | #26 | 00:34:06.351 | 11-3 | 2026-10-03 09:30—10:30 | 0 | 创建预订成功 |
| 科学与艺术中心 | #34 | 00:35:20.934 | A-10 | 2026-10-03 09:00—18:00 | 200 | 不能预订超过8小时的meetingtype.cs_seat |
| 科学与艺术中心 | #28 | 00:35:29.615 | A-21 | 2026-10-03 09:00—14:00 | 200 | 同一用户10秒只能提交一次 |
| 科学与艺术中心 | #25 | 00:35:44.954 | A-27 | 2026-10-03 09:00—14:00 | 0 | 创建meetingType.CS_SEAT成功 |

对客户端流程的实际影响：需要单用户提交节流，不能失败后立刻连续提交；出错后核对最近预约，避免把不确定的创建结果当作无订单；最终日期和时长验证以服务端响应为准。本样本只证实 10 秒频率限制的错误提示，未探测精确边界、重置机制或幂等实现。

### 8.6 24H HAR 中的超星支线

24H 文件还记录 selfreport.shu.edu.cn → cxxz.shu.edu.cn → cv-p.chaoxing.com → office.chaoxing.com 的另一座位系统入口。它不是 there 登录链；本次没有那条支线的预约创建，不能合并其 roomId、fidEnc 或接口到 there schema。

| 顺序 | 原始证据 | 主机与路由 | 状态 |
| --- | --- | --- | --- |
| 1 | 24H学习空间预约.har#104 | selfreport.shu.edu.cn/QYWXRedirect.ashx | 302 |
| 2 | #103 | cxxz.shu.edu.cn/auth-shu/auth | 302 |
| 3 | #102 | cv-p.chaoxing.com/auth-shu/authJump | 302 |
| 4 | #101 | office.chaoxing.com/front/apps/seat/index | 302 |
| 5 | #100 | office.chaoxing.com/front/third/apps/seat/index | 200 |

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
