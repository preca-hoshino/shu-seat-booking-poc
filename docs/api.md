# API：四系统端点、参数与返回体

> 返回 [项目 README](../README.md) · [文档索引](README.md)

资料依据 2026-10-03 的四个用户 HAR 与固定提交的 `shu-sso-poc`。以下保留完整捕获字段、脱敏样例与来源边界；章节编号沿用[完整研究记录](research.md)，方便交叉引用。接口章节见 [api.md](api.md)，认证章节见 [login.md](login.md)，预约设计与四条实测链见 [booking.md](booking.md)，来源及九十条时间线见 [evidence.md](evidence.md)。

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
| authJump | there 成功落地 /web 的查询参数（另见 /main → /web 形态） | 不是 API 的 x-hys-session。 |
| HTML.sessionId | /mobile/* 的页面引导数据 | 是业务头 x-hys-session 的来源。 |

离线检查显示，90 次请求的 SPHYS_SESSION 中 utoken 和 x-hys-session 均为声明 HS512、DEF 压缩的 JWT 形状；解码字段名为 sub/aud/exp，两者 sub 均对应 profile.data.id，但令牌字符串不同。本次没有验证签名、输出实际 claims 或调用令牌。该关系支持同用户关联，不能把 utoken 直接填到 x-hys-session。

已捕获的 JS 分块包含公共 HTTP 客户端模块，可核对请求头、401 跳登录等行为；主 app.js 的响应正文缺失，因此无法恢复全部页面交互。

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
