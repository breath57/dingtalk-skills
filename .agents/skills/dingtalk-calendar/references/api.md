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

## 错误码

| HTTP / 业务 | 说明 | 处理建议 |
|---|---|---|
| 400 `InvalidParameter.ParsedISO8601TimestampError` | 时间字符串格式不符 | 使用 `yyyy-MM-ddTHH:mm:ss.000Z` |
| 401 | Token 无效或过期 | 重新获取 `accessToken`，必要时 `--nocache` |
| 403 `AccessDenied` | 缺少权限 | 开放平台为应用开通日历/日程相关权限 |

---

## 所需应用权限

在钉钉开放平台 → 应用管理 → 权限管理中开通与 **日历（Calendar）** 相关的读/写能力（具体权限点名称以控制台为准，常见包含日程查询、日程写入、闲忙查询等）。未开通时接口返回 403，响应体中的 `requiredScopes` / `message` 会提示需申请的权限标识。
