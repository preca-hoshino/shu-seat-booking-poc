# there 四入口 API

> [文档索引](README.md) · [预约流程](booking.md) · [OpenAPI](openapi/there.openapi.yaml)

`https://there.shu.edu.cn/api/v3` 为四类座位资源共用的业务地址。移动入口决定 `x-room-type` 与当前页面会话：

| 资源 | 移动入口 | `x-room-type` |
| --- | --- | --- |
| 校本部图书馆 | `/mobile/libseat` | `LIB_SEAT` |
| 24H 学习空间 | `/mobile/seat2021` | `STATION` |
| 延长智能中心 | `/mobile/seat-mgr` | `SEAT` |
| 科学与艺术中心 | `/mobile/csseat` | `CS_SEAT` |

客户端使用同一 Cookie jar 打开移动页面，读取页面中的 `sessionId` 作为 `x-hys-session`，并携带对应的 `x-room-type` 与 Referer。身份凭据来自登录流程，详见 [登录](login.md)。HTTP 成功不等于业务成功；应检查响应 JSON 中的 `code` 与具体数据。

## 业务端点与字段

以下字段表描述接口响应可能包含的字段；是否必返和具体值均以当前服务端为准。

### 4.1 当前用户

GET `/api/v3/my/profile`；无业务 query。创建预约使用当前用户的 `data.id` 和 `data.name`。

| JSON 字段路径 | 字段类型 | 说明 |
| --- | --- | --- |
| `code` | `integer` | 0 为业务成功，200 为业务拒绝；与 HTTP 状态码不同。 |
| `data` | `object` | 已知字段；是否必返以服务端为准。 |
| `data.id` | `string` | profile 时是用户 ID；区域详情时是 areaId；预约详情时是 bookingId。 |
| `data.loginName` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.name` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.namePinyin` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.jobNumber` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.cardNo` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.nickName` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.sex` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.headImgUrl` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.mobile` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.position` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.deptId` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.deptName` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.corp` | `object` | 已知字段；是否必返以服务端为准。 |
| `data.corp.id` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.corp.name` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.corp.meetingRoomCount` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.corp.abilities` | `array<unknown>` | 已知字段；是否必返以服务端为准。 |
| `data.corpName` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.roles` | `array<string>` | 已知字段；是否必返以服务端为准。 |
| `data.status` | `string` | OPEN 不等于已签到；finish 后最终状态也可为 CANCEL。 |
| `data.statusLabel` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.deptIds` | `array<string>` | 已知字段；是否必返以服务端为准。 |
| `data.depts` | `array<object>` | 已知字段；是否必返以服务端为准。 |
| `data.depts[]` | `object` | 已知字段；是否必返以服务端为准。 |
| `data.depts[].id` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.depts[].name` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.depts[].shortName` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.depts[].fullName` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.depts[].parentId` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.depts[].parentName` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.depts[].showOrder` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.depts[].labelName` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.depts[].userCount` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.depts[].userCountWithNew` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.depts[].upstreamId` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.depts[].isSett` | `boolean` | 已知字段；是否必返以服务端为准。 |
| `data.isAnonymous` | `boolean` | 已知字段；是否必返以服务端为准。 |
| `data.disableBooking` | `boolean` | 已知字段；是否必返以服务端为准。 |
| `data.defaultArea` | `object` | 已知字段；是否必返以服务端为准。 |
| `data.defaultArea.id` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.defaultArea.name` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.defaultArea.level` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.defaultArea.shortName` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.defaultArea.supportRoomTypes` | `array<string>` | 已知字段；是否必返以服务端为准。 |
| `data.defaultArea.validRoomCount` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.defaultArea.abilities` | `array<unknown>` | 已知字段；是否必返以服务端为准。 |
| `data.officeAreaResponse` | `object` | 已知字段；是否必返以服务端为准。 |
| `data.officeAreaResponse.id` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.officeAreaResponse.name` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.officeAreaResponse.level` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.officeAreaResponse.shortName` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.officeAreaResponse.supportRoomTypes` | `array<string>` | 已知字段；是否必返以服务端为准。 |
| `data.officeAreaResponse.validRoomCount` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.officeAreaResponse.abilities` | `array<unknown>` | 已知字段；是否必返以服务端为准。 |
| `data.permissions` | `array<string>` | 已知字段；是否必返以服务端为准。 |
| `data.receiveMeetingMail` | `boolean` | 已知字段；是否必返以服务端为准。 |
| `data.receiveNotify` | `boolean` | 已知字段；是否必返以服务端为准。 |
| `data.upstreamId` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.createdAt` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.updatedAt` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.isAdmin` | `boolean` | 已知字段；是否必返以服务端为准。 |
| `data.abilities` | `array<string>` | 详情的操作能力，例如 cancel、waitOpen、close；不能用状态字段单独替代。 |

### 4.2 最近预约

GET `/api/v3/my/bookings/recent`；无业务 query。返回近期预约列表，需按状态判断是否仍有效。

| JSON 字段路径 | 字段类型 | 说明 |
| --- | --- | --- |
| `code` | `integer` | 0 为业务成功，200 为业务拒绝；与 HTTP 状态码不同。 |
| `data` | `array<object>` | 已知字段；是否必返以服务端为准。 |
| `data[]` | `object` | 已知字段；是否必返以服务端为准。 |
| `data[].id` | `string` | recent/创建响应时是 bookingId；区域列表时是 areaId。 |
| `data[].subject` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].ownerId` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].ownerName` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].ownerMobile` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].ownerPhone` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].ownerPosition` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].ownerDeptId` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].clientType` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].meetingInfra` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].ownerUpStreamId` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].ownerUpstreamId` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].ownerDeptName` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].ownerJobNumber` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].ownerUserNamePinYin` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingUserId` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingUsernamePinYin` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingUserUpStreamId` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingUserName` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingUserShowName` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].beginTime` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].endTime` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].duration` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data[].roomId` | `string` | 座位资源 ID，不是预约 ID。 |
| `data[].roomName` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].officeAreaId` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].officeAreaName` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].allOfficeAreaName` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].roomNeedApproved` | `boolean` | 已知字段；是否必返以服务端为准。 |
| `data[].templateType` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].receptionId` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].receptionName` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].receptionMobile` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].memberNumbers` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data[].customFormIds` | `array<unknown>` | 已知字段；是否必返以服务端为准。 |
| `data[].roomType` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].status` | `string` | recent 可含 CANCEL 历史记录，非空不等于存在有效预约。 |
| `data[].workflow` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].statusLabel` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].needCheckin` | `boolean` | 已知字段；是否必返以服务端为准。 |
| `data[].checkedStatus` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].meetingRepeatType` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].meetingType` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].busyCssName` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].createdAt` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].updatedAt` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].beforeNotify` | `boolean` | 已知字段；是否必返以服务端为准。 |
| `data[].facilityNames` | `array<unknown>` | 已知字段；是否必返以服务端为准。 |
| `data[].abilities` | `array<string>` | 已知字段；是否必返以服务端为准。 |
| `data[].origEndAt` | `string` | 提前结束后保留原结束时间。 |

### 4.3 日期概览

GET `/api/v3/booking-status/overview?day=<YYYY-MM-DD>`；`day` 为目标日期。

| JSON 字段路径 | 字段类型 | 说明 |
| --- | --- | --- |
| `code` | `integer` | 0 为业务成功，200 为业务拒绝；与 HTTP 状态码不同。 |
| `data` | `object` | 已知字段；是否必返以服务端为准。 |
| `data.currentOfficeArea` | `object` | 已知字段；是否必返以服务端为准。 |
| `data.currentOfficeArea.id` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.currentOfficeArea.name` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.currentOfficeArea.shortName` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.currentOfficeArea.supportRoomTypes` | `array<string>` | 已知字段；是否必返以服务端为准。 |
| `data.currentOfficeArea.abilities` | `array<unknown>` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes` | `object` | 当前响应的时间配置；须区分概览通用配置和选中区域配置。 |
| `data.bookingTimes.timeBlockType` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.startHour` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.endHour` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.morningEndHour` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.afternoonStartHour` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.maxDuration` | `integer` | 当前按分钟使用；所选四区域均为 480。 |
| `data.bookingTimes.configMaxDuration` | `integer` | 当前按分钟使用；所选四区域均为 480。 |
| `data.bookingTimes.meetingInterval` | `integer` | 当前按分钟使用，四区域分别为 30、30、15、60。 |
| `data.bookingTimes.meetingHalfHours` | `array<string>` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.timeBlocks` | `array<object>` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.timeBlocks[]` | `object` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.timeBlocks[].key` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.timeBlocks[].start` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.timeBlocks[].end` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.timeBlocks[].startMinutes` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.timeBlocks[].endMinutes` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.allMeetingDurations` | `array<object>` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.allMeetingDurations[]` | `object` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.allMeetingDurations[].name` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.allMeetingDurations[].value` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.allWeekDays` | `array<object>` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.allWeekDays[]` | `object` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.allWeekDays[].name` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.allWeekDays[].value` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.meetingRepeatTypes` | `array<string>` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.needCheckin` | `boolean` | 具体值以当前区域为准；签到条件尚需服务端确认。 |
| `data.bookingTimes.disablePersonConflict` | `boolean` | 冲突校验配置，以当前区域返回值为准。 |
| `data.bookingTimes.enableFixedBooking` | `boolean` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.enableAgentBooking` | `boolean` | 已知字段；是否必返以服务端为准。 |
| `data.bookingDays` | `array<object>` | 服务端返回的候选日期数组，不等同于服务端准入边界。 |
| `data.bookingDays[]` | `object` | 已知字段；是否必返以服务端为准。 |
| `data.bookingDays[].day` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.bookingDays[].workDay` | `boolean` | 已知字段；是否必返以服务端为准。 |
| `data.bookingDays[].lawDay` | `boolean` | 已知字段；是否必返以服务端为准。 |
| `data.bookingDays[].weekDay` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.bookingDays[].meetingCount` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.bookingDays[].roomCount` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.bookingDays[].bookingRoomCount` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.bookingDays[].bookingRate` | `number` | 已知字段；是否必返以服务端为准。 |
| `data.bookingDays[].meetingMinutes` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.bookingDays[].rooms` | `array<unknown>` | 已知字段；是否必返以服务端为准。 |

### 4.4 区域列表

GET `/api/v3/booking-status/areas?begin=...&end=...`；`begin`、`end` 为查询区间。

| JSON 字段路径 | 字段类型 | 说明 |
| --- | --- | --- |
| `code` | `integer` | 0 为业务成功，200 为业务拒绝；与 HTTP 状态码不同。 |
| `data` | `array<object>` | 已知字段；是否必返以服务端为准。 |
| `data[]` | `object` | 已知字段；是否必返以服务端为准。 |
| `data[].disabledResourceCount` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingTimes` | `object` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingTimes.timeBlockType` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingTimes.startHour` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingTimes.endHour` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingTimes.morningEndHour` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingTimes.afternoonStartHour` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingTimes.maxDuration` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingTimes.minDuration` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingTimes.configMaxDuration` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingTimes.meetingInterval` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingTimes.bookingLimitDays` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingTimes.meetingHalfHours` | `array<string>` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingTimes.timeBlocks` | `array<object>` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingTimes.timeBlocks[]` | `object` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingTimes.timeBlocks[].key` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingTimes.timeBlocks[].start` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingTimes.timeBlocks[].end` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingTimes.timeBlocks[].startMinutes` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingTimes.timeBlocks[].endMinutes` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingTimes.allMeetingDurations` | `array<object>` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingTimes.allMeetingDurations[]` | `object` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingTimes.allMeetingDurations[].name` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingTimes.allMeetingDurations[].value` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingTimes.allWeekDays` | `array<object>` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingTimes.allWeekDays[]` | `object` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingTimes.allWeekDays[].name` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingTimes.allWeekDays[].value` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingTimes.meetingRepeatTypes` | `array<string>` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingTimes.needCheckin` | `boolean` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingTimes.disablePersonConflict` | `boolean` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingTimes.enableFixedBooking` | `boolean` | 已知字段；是否必返以服务端为准。 |
| `data[].bookingTimes.enableAgentBooking` | `boolean` | 已知字段；是否必返以服务端为准。 |
| `data[].id` | `string` | recent/创建响应时是 bookingId；区域列表时是 areaId。 |
| `data[].name` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].level` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].path` | `array<object>` | 已知字段；是否必返以服务端为准。 |
| `data[].path[]` | `object` | 已知字段；是否必返以服务端为准。 |
| `data[].path[].id` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].path[].name` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].shortName` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].showOrder` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data[].supportRoomTypes` | `array<string>` | 已知字段；是否必返以服务端为准。 |
| `data[].abilities` | `array<unknown>` | 已知字段；是否必返以服务端为准。 |
| `data[].totalResourceCount` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data[].bookedResourceCount` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data[].bookedMeetingCount` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data[].bookableResourceCount` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data[].busyResourceCount` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data[].freeResourceCount` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data[].parentId` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].parentName` | `string` | 已知字段；是否必返以服务端为准。 |

### 4.5 区域座位与规则

GET `/api/v3/booking-status/areas/{areaId}?begin=...&end=...`；`areaId` 来自区域列表。

| JSON 字段路径 | 字段类型 | 说明 |
| --- | --- | --- |
| `code` | `integer` | 0 为业务成功，200 为业务拒绝；与 HTTP 状态码不同。 |
| `data` | `object` | 已知字段；是否必返以服务端为准。 |
| `data.totalResourceCount` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.bookedResourceCount` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.bookedMeetingCount` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.disabledResourceCount` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.bookableResourceCount` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes` | `object` | 当前响应的时间配置；须区分概览通用配置和选中区域配置。 |
| `data.bookingTimes.timeBlockType` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.supportAcrossDayBooking` | `boolean` | 是否允许跨日预约，以当前区域返回值为准。 |
| `data.bookingTimes.suggestStartTime` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.suggestEndTime` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.startHour` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.endHour` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.morningEndHour` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.afternoonStartHour` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.maxDuration` | `integer` | 当前按分钟使用；所选四区域均为 480。 |
| `data.bookingTimes.minDuration` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.configMaxDuration` | `integer` | 当前按分钟使用；所选四区域均为 480。 |
| `data.bookingTimes.meetingInterval` | `integer` | 当前按分钟使用，四区域分别为 30、30、15、60。 |
| `data.bookingTimes.meetingHalfHours` | `array<string>` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.timeBlocks` | `array<object>` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.timeBlocks[]` | `object` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.timeBlocks[].key` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.timeBlocks[].start` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.timeBlocks[].end` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.timeBlocks[].startMinutes` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.timeBlocks[].endMinutes` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.timeBlocks[].disabled` | `boolean` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.allMeetingDurations` | `array<object>` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.allMeetingDurations[]` | `object` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.allMeetingDurations[].name` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.allMeetingDurations[].value` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.allWeekDays` | `array<object>` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.allWeekDays[]` | `object` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.allWeekDays[].name` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.allWeekDays[].value` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.meetingRepeatTypes` | `array<string>` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.needCheckin` | `boolean` | 具体值以当前区域为准；签到条件尚需服务端确认。 |
| `data.bookingTimes.disablePersonConflict` | `boolean` | 冲突校验配置，以当前区域返回值为准。 |
| `data.bookingTimes.enableFixedBooking` | `boolean` | 已知字段；是否必返以服务端为准。 |
| `data.bookingTimes.enableAgentBooking` | `boolean` | 已知字段；是否必返以服务端为准。 |
| `data.assetFiles` | `array<object>` | 已知字段；是否必返以服务端为准。 |
| `data.assetFiles[]` | `object` | 已知字段；是否必返以服务端为准。 |
| `data.assetFiles[].id` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.assetFiles[].uid` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.assetFiles[].title` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.assetFiles[].url` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.assetFiles[].thumbnailUrl` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.assetFiles[].name` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.assetFiles[].fileName` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.bookingDays` | `array<string>` | 服务端返回的候选日期数组，不等同于服务端准入边界。 |
| `data.id` | `string` | profile 时是用户 ID；区域详情时是 areaId；预约详情时是 bookingId。 |
| `data.name` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.level` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.path` | `array<object>` | 已知字段；是否必返以服务端为准。 |
| `data.path[]` | `object` | 已知字段；是否必返以服务端为准。 |
| `data.path[].id` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.path[].name` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.shortName` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.showOrder` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.supportRoomTypes` | `array<string>` | 已知字段；是否必返以服务端为准。 |
| `data.parentId` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.parentName` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.rooms` | `array<object>` | 已知字段；是否必返以服务端为准。 |
| `data.rooms[]` | `object` | 已知字段；是否必返以服务端为准。 |
| `data.rooms[].id` | `string` | 座位资源 ID，创建请求 rooms[].id 的来源。 |
| `data.rooms[].name` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.rooms[].officeAreaId` | `string` | 所属区域 ID。 |
| `data.rooms[].disabled` | `boolean` | 座位禁用状态。 |
| `data.rooms[].showOrder` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.rooms[].isBusy` | `boolean` | 当前查询区间的状态；不保证提交时仍可用。 |
| `data.rooms[].isBooked` | `boolean` | 当前查询返回的预约状态。 |
| `data.rooms[].abilities` | `array<string>` | 前端可执行能力；创建候选通常包含 booking。 |
| `data.rooms[].currentBooking` | `object` | 已知字段；是否必返以服务端为准。 |
| `data.rooms[].currentBooking.id` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.rooms[].currentBooking.subject` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.rooms[].currentBooking.ownerId` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.rooms[].currentBooking.beginTime` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.rooms[].currentBooking.endTime` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.rooms[].currentBooking.templateType` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.rooms[].currentBooking.beforeNotify` | `boolean` | 已知字段；是否必返以服务端为准。 |
| `data.rooms[].currentBooking.abilities` | `array<unknown>` | 已知字段；是否必返以服务端为准。 |
| `data.abilities` | `array<unknown>` | 详情的操作能力，例如 cancel、waitOpen、close；不能用状态字段单独替代。 |
| `data.busyResourceCount` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.freeResourceCount` | `integer` | 已知字段；是否必返以服务端为准。 |

### 4.6 创建预约

POST `/api/v3/bookings`；JSON 使用当前 profile、座位对象和目标时间组装。成功后从 `data[0].id` 取得预约 ID。

**创建请求字段**

| 字段路径 | 类型 | 说明 |
| --- | --- | --- |
| `rooms` | `array<object>` | 取区域详情返回的完整座位对象；未验证只传 id。 |
| `rooms[]` | `object` | 已知字段；是否必返以服务端为准。 |
| `rooms[].id` | `string` | 已知字段；是否必返以服务端为准。 |
| `rooms[].name` | `string` | 已知字段；是否必返以服务端为准。 |
| `rooms[].officeAreaId` | `string` | 已知字段；是否必返以服务端为准。 |
| `rooms[].disabled` | `boolean` | 已知字段；是否必返以服务端为准。 |
| `rooms[].showOrder` | `integer` | 已知字段；是否必返以服务端为准。 |
| `rooms[].isBusy` | `boolean` | 已知字段；是否必返以服务端为准。 |
| `rooms[].isBooked` | `boolean` | 已知字段；是否必返以服务端为准。 |
| `rooms[].abilities` | `array<string>` | 已知字段；是否必返以服务端为准。 |
| `times` | `array<object>` | 当前仅单时段，数组形状不证明支持多时段。 |
| `times[]` | `object` | 已知字段；是否必返以服务端为准。 |
| `times[].startDate` | `string` | 已知字段；是否必返以服务端为准。 |
| `times[].startTime` | `string` | 当前格式 HH:mm，使用校园当地时间 Asia/Shanghai；未验证其他格式。 |
| `times[].endDate` | `string` | 已知字段；是否必返以服务端为准。 |
| `times[].endTime` | `string` | 当前格式 HH:mm，使用校园当地时间 Asia/Shanghai；未验证其他格式。 |
| `subject` | `string` | 8 次请求均来自 profile.data.name。 |
| `meetingMembers` | `array<string>` | 8 次请求均为 [profile.data.id]，代预约及多成员未验证。 |
| JSON 字段路径 | 字段类型 | 说明 |
| --- | --- | --- |
| `code` | `integer` | 0 为业务成功，200 为业务拒绝；与 HTTP 状态码不同。 |
| `warnMessage` | `string` | 业务拒绝提示；错误响应未必有 message。 |
| `message` | `string` | 已知字段；是否必返以服务端为准。 |
| `data` | `array<object>` | 已知字段；是否必返以服务端为准。 |
| `data[]` | `object` | 已知字段；是否必返以服务端为准。 |
| `data[].id` | `string` | recent/创建响应时是 bookingId；区域列表时是 areaId。 |
| `data[].subject` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].templateType` | `string` | 已知字段；是否必返以服务端为准。 |
| `data[].beforeNotify` | `boolean` | 已知字段；是否必返以服务端为准。 |
| `data[].abilities` | `array<unknown>` | 已知字段；是否必返以服务端为准。 |
| `noticeMessage` | `string` | 业务操作提示。 |

### 4.7 预约详情

GET `/api/v3/bookings/{bookingId}`；可传 `showChecks=true`。预约 ID 来自创建结果或近期预约。

| JSON 字段路径 | 字段类型 | 说明 |
| --- | --- | --- |
| `code` | `integer` | 0 为业务成功，200 为业务拒绝；与 HTTP 状态码不同。 |
| `data` | `object` | 已知字段；是否必返以服务端为准。 |
| `data.success` | `boolean` | 已知字段；是否必返以服务端为准。 |
| `data.id` | `string` | profile 时是用户 ID；区域详情时是 areaId；预约详情时是 bookingId。 |
| `data.subject` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.ownerId` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.ownerName` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.ownerMobile` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.ownerPhone` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.ownerPosition` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.ownerDeptId` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.clientType` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.meetingInfra` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.ownerDeptUpStreamId` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.ownerUpStreamId` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.ownerUpstreamId` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.ownerDeptName` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.ownerJobNumber` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.ownerUserNamePinYin` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.bookingUserId` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.bookingUsernamePinYin` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.bookingUserUpStreamId` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.bookingUserDeptUpStreamId` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.bookingUserName` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.bookingUserShowName` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.beginTime` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.endTime` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.duration` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.roomId` | `string` | 座位资源 ID，不是预约 ID。 |
| `data.roomName` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.officeAreaId` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.officeAreaName` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.allOfficeAreaName` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.copyToMembers` | `array<unknown>` | 已知字段；是否必返以服务端为准。 |
| `data.roomNeedApproved` | `boolean` | 已知字段；是否必返以服务端为准。 |
| `data.templateType` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.receptionId` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.receptionName` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.receptionMobile` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.memberNumbers` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.customFormIds` | `array<unknown>` | 已知字段；是否必返以服务端为准。 |
| `data.roomType` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.status` | `string` | OPEN 不等于已签到；finish 后最终状态也可为 CANCEL。 |
| `data.workflow` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.statusLabel` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.needCheckin` | `boolean` | 已知字段；是否必返以服务端为准。 |
| `data.joinStatus` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.checkinStatus` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.currentUserCheckinStatus` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.checkedStatus` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.meetingRepeatType` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.members` | `array<object>` | 已知字段；是否必返以服务端为准。 |
| `data.members[]` | `object` | 已知字段；是否必返以服务端为准。 |
| `data.members[].id` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.members[].name` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.members[].namePinyin` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.members[].joinStatus` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.members[].joinAt` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.members[].checkinStatus` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.members[].checkAt` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.commentCount` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.meetingType` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.qrCodeUrl` | `string` | 二维码图片 URL，仅有引用，响应和方法尚未确认。 |
| `data.qrCodeValue` | `string` | 签到页面 URL；可能包含敏感令牌，输出时应脱敏。 |
| `data.qrCodeTitle` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.memberCount` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.busyCssName` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.events` | `array<unknown>` | 已知字段；是否必返以服务端为准。 |
| `data.meetingOrderLists` | `array<unknown>` | 已知字段；是否必返以服务端为准。 |
| `data.checkedInPeopleCount` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.confirmedPeopleCount` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.refusedPeopleCount` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.createdAt` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.updatedAt` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.meetingFiles` | `array<unknown>` | 已知字段；是否必返以服务端为准。 |
| `data.beforeNotify` | `boolean` | 已知字段；是否必返以服务端为准。 |
| `data.facilityNames` | `array<unknown>` | 已知字段；是否必返以服务端为准。 |
| `data.nowAvailableDelayMinutes` | `integer` | 已知字段；是否必返以服务端为准。 |
| `data.checkins` | `array<unknown>` | 图书馆/24H 出现空数组，元素结构未知。 |
| `data.form` | `array<string>` | 已知字段；是否必返以服务端为准。 |
| `data.showExtras` | `boolean` | 已知字段；是否必返以服务端为准。 |
| `data.showExtrasSwitch` | `boolean` | 已知字段；是否必返以服务端为准。 |
| `data.abilities` | `array<string>` | 详情的操作能力，例如 cancel、waitOpen、close；不能用状态字段单独替代。 |
| `data.otherSeatList` | `array<unknown>` | 已知字段；是否必返以服务端为准。 |

### 4.8 取消预约

DELETE `/api/v3/bookings/{bookingId}/cancel`；操作后重新查询预约。

| JSON 字段路径 | 字段类型 | 说明 |
| --- | --- | --- |
| `code` | `integer` | 0 为业务成功，200 为业务拒绝；与 HTTP 状态码不同。 |
| `data` | `object` | 已知字段；是否必返以服务端为准。 |
| `data.success` | `boolean` | 已知字段；是否必返以服务端为准。 |
| `data.templateType` | `string` | 已知字段；是否必返以服务端为准。 |
| `data.beforeNotify` | `boolean` | 已知字段；是否必返以服务端为准。 |
| `data.abilities` | `array<unknown>` | 详情的操作能力，例如 cancel、waitOpen、close；不能用状态字段单独替代。 |
| `noticeMessage` | `string` | 业务操作提示。 |

### 4.9 提前结束预约

PUT `/api/v3/bookings/{bookingId}/finish`；操作后重新查询预约。

| JSON 字段路径 | 字段类型 | 说明 |
| --- | --- | --- |
| `code` | `integer` | 0 为业务成功，200 为业务拒绝；与 HTTP 状态码不同。 |
| `noticeMessage` | `string` | 业务操作提示。 |
| `message` | `string` | 已知字段；是否必返以服务端为准。 |
