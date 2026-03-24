# 钉钉日程（Calendar）API 参考

> 基础 URL：`https://api.dingtalk.com`  
> 公共请求头：`x-acs-dingtalk-access-token: <新版 accessToken>`、`Content-Type: application/json`  
> 路径中的 `{unionId}` 为操作者或目标用户的 **unionId**（不是 staffId）。主日历 ID 使用 **`primary`**。

---

## 身份标识与 userId → unionId

日程接口路径 `.../users/{unionId}/...` 使用 **unionId**。若仅有 userId，使用**旧版** token：

```
GET https://oapi.dingtalk.com/gettoken?appkey=<AppKey>&appsecret=<AppSecret>
POST https://oapi.dingtalk.com/topapi/v2/user/get?access_token=<旧版token>
Body: {"userid":"<userId>"}
→ result.unionid（无下划线字段）
```

---

## 1. 创建日程

**POST** `/v1.0/calendar/users/{unionId}/calendars/primary/events`

### 请求体

```json
{
  "summary": "项目周会",
  "description": "讨论排期",
  "start": {
    "dateTime": "2026-03-25T02:00:00.000Z",
    "timeZone": "UTC"
  },
  "end": {
    "dateTime": "2026-03-25T03:00:00.000Z",
    "timeZone": "UTC"
  }
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `summary` | ✅ | 标题 |
| `start` / `end` | ✅ | `dateTime` 为 UTC ISO8601 **含毫秒**；`timeZone` 如 `UTC` |

### 响应（节选）

```json
{
  "id": "xxxxxxxx",
  "summary": "项目周会",
  "start": { "dateTime": "2026-03-25T02:00:00Z", "timeZone": "UTC" },
  "end": { "dateTime": "2026-03-25T03:00:00Z", "timeZone": "UTC" },
  "requestId": "..."
}
```

---

## 2. 查询单个日程

**GET** `/v1.0/calendar/users/{unionId}/calendars/primary/events/{eventId}`

可选 Query：`maxAttendees`

### 响应

返回完整事件对象，含 `id`、`summary`、`start`、`end`、`organizer` 等。

---

## 3. 查询日程列表

**GET** `/v1.0/calendar/users/{unionId}/calendars/primary/events`

### Query 参数

| 参数 | 说明 |
|---|---|
| `timeMin` | 范围开始（UTC ISO8601，建议含毫秒） |
| `timeMax` | 范围结束 |
| `maxResults` | 每页条数，如 `50` |
| `nextToken` | 分页 |

### 响应（节选）

```json
{
  "events": [
    {
      "id": "...",
      "summary": "...",
      "start": { "dateTime": "...", "timeZone": "UTC" },
      "end": { "dateTime": "...", "timeZone": "UTC" }
    }
  ],
  "nextToken": null
}
```

---

## 4. 更新日程

**PUT** `/v1.0/calendar/users/{unionId}/calendars/primary/events/{eventId}`

（SDK 中方法名为 PatchEvent，HTTP 为 PUT。）

### 请求体

```json
{
  "id": "<与路径中 eventId 相同>",
  "summary": "项目周会（已改）"
}
```

可携带 `start`/`end`/`description` 等字段做修改。

### 响应

返回更新后的完整事件对象。

---

## 5. 删除日程

**DELETE** `/v1.0/calendar/users/{unionId}/calendars/primary/events/{eventId}`

可选 Query：`pushNotification`（boolean）

### 响应

```json
{ "requestId": "..." }
```

---

## 6. 查询闲忙

**POST** `/v1.0/calendar/users/{unionId}/querySchedule`

### 请求体

```json
{
  "startTime": "2026-03-24T00:00:00.000Z",
  "endTime": "2026-03-25T00:00:00.000Z",
  "userIds": ["<unionId1>", "<unionId2>"]
}
```

| 字段 | 说明 |
|---|---|
| `startTime` / `endTime` | UTC ISO8601 **含毫秒** |
| `userIds` | 要查询闲忙的用户的 **unionId** 列表 |

---

## 7. 视频会议（钉钉会议）

创建日程时在请求体中增加：

```json
"onlineMeetingInfo": { "type": "dingtalk" }
```

成功时响应含 `onlineMeetingInfo.url`、`conferenceId`、`extraInfo`（如网页入会链接、会议号）等。

---

## 8. 查询会议室忙闲

**POST** `/v1.0/calendar/users/{unionId}/meetingRooms/schedules/query`

### 请求体

```json
{
  "startTime": "2026-03-24T00:00:00.000Z",
  "endTime": "2026-03-25T00:00:00.000Z",
  "roomIds": ["<会议室 roomId>", "<roomId2>"]
}
```

| 字段 | 说明 |
|---|---|
| `startTime` / `endTime` | UTC ISO8601，**建议含毫秒**（与闲忙接口一致） |
| `roomIds` | 会议室 ID 列表（企业内会议室资源 ID，非 unionId） |

返回各会议室在时间窗内的占用情况（结构以实际响应为准）。

---

## 9. 添加与移除会议室

**添加** — **POST** `/v1.0/calendar/users/{unionId}/calendars/primary/events/{eventId}/meetingRooms`

```json
{
  "meetingRoomsToAdd": [{ "roomId": "<会议室ID>" }]
}
```

**批量移除** — **POST** `/v1.0/calendar/users/{unionId}/calendars/primary/events/{eventId}/meetingRooms/batchRemove`

```json
{
  "meetingRoomsToRemove": [{ "roomId": "<会议室ID>" }]
}
```

---

## 10. 签到与签退链接

**GET** `/v1.0/calendar/users/{unionId}/calendars/primary/events/{eventId}/signInLinks`  
**GET** `/v1.0/calendar/users/{unionId}/calendars/primary/events/{eventId}/signOutLinks`

### 响应（节选）

```json
{ "signInLink": "https://..." }
```

```json
{ "signOutLink": "https://..." }
```

---

## 11. 签到与签退详情列表

**GET** `/v1.0/calendar/users/{unionId}/calendars/primary/events/{eventId}/signin`  
**GET** `/v1.0/calendar/users/{unionId}/calendars/primary/events/{eventId}/signOut`

可选 Query：`maxResults`、`nextToken`、`type`（以开放平台说明为准）。

---

## 12. 签到与签退操作

**POST** `/v1.0/calendar/users/{unionId}/calendars/primary/events/{eventId}/signin` — 签到（无 body）  
**POST** `/v1.0/calendar/users/{unionId}/calendars/primary/events/{eventId}/signOut` — 签退（无 body）

成功时响应可含 `checkInTime` 等字段。重复签到、未开放签到等场景可能返回业务错误码，需按返回提示处理。

---

## 13. 循环日程

创建日程时在请求体中增加 `recurrence`，包含 `pattern`（重复规则）与 `range`（结束条件）。以下为示例，**具体 `type` 取值以钉钉开放平台文档为准**：

```json
{
  "summary": "每日站会",
  "start": { "dateTime": "2026-03-24T01:00:00.000Z", "timeZone": "UTC" },
  "end": { "dateTime": "2026-03-24T01:15:00.000Z", "timeZone": "UTC" },
  "recurrence": {
    "pattern": { "type": "daily", "interval": 1 },
    "range": { "type": "endDate", "endDate": "2026-04-24T00:00:00.000Z" }
  }
}
```

循环系列删除、修改单实例等可使用 `listEventsInstances` 等接口（SDK 中另有方法）。

---

## 14. 订阅日历

创建/删除/更新**订阅日历**、订阅**公共日历**等接口路径在 `.../subscribedCalendars...`，需开放平台开通 **Calendar.Calendar.Write**（及对应读权限）。本技能主流程以主日历 `primary` 为主；订阅能力按需查阅 SDK `create_subscribed_calendar` 等。

---

## 错误码

| HTTP / 业务 | 说明 | 处理建议 |
|---|---|---|
| 400 `InvalidParameter.ParsedISO8601TimestampError` | 时间字符串格式不符 | 使用 `yyyy-MM-ddTHH:mm:ss.000Z` |
| 401 | Token 无效或过期 | 重新获取 `accessToken`，必要时 `--nocache` |
| 403 `AccessDenied` | 缺少权限 | 开放平台为应用开通日历/日程相关权限 |

---

## 所需应用权限

在钉钉开放平台 → 应用管理 → 权限管理中开通与 **日历（Calendar）** 相关的读/写能力。常见对应关系（**以控制台实际名称为准**）：

| 能力 | 典型权限标识 |
|---|---|
| 日程增删改查、会议室绑定、签到签退等 | `Calendar.Event.Read` / `Calendar.Event.Write` |
| 用户闲忙（querySchedule） | `Calendar.EventSchedule.Read` |
| 会议室忙闲查询 | 一般含在日程读能力或单独会议室相关说明中 |
| 订阅日历、公共日历 | `Calendar.Calendar.Write`（及 `Calendar.Calendar.Read`） |

未开通时接口返回 403，响应体中的 `requiredScopes` / `message` 会提示需申请的权限标识。
