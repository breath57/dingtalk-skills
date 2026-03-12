# 钉钉待办 API 参考

> 接口基础 URL：`https://api.dingtalk.com`  
> 公共请求头：`x-acs-dingtalk-access-token: <token>` + `Content-Type: application/json`  
> 所有 `{unionId}` 替换为操作者的 unionId（从 userId 转换获得，见下方「身份标识」章节）

---

## 身份标识与 userId ↔ unionId 转换

待办 API 的路径参数 `{unionId}`、查询参数 `operatorId`、以及 `executorIds` / `participantIds` **均使用 unionId**。  
但 unionId 无法直接在管理后台查看，需要通过 userId 调用 API 转换。

### 钉钉用户 ID 体系

| 标识 | 说明 | 作用域 | 待办 API 支持 |
|---|---|---|---|
| `userId`（= `staffId`） | 企业内部员工 ID | 单个企业内唯一 | ❌ 不能直接用于待办 API |
| `unionId` | 跨企业/跨应用的用户 ID | 同一法人跨组织唯一 | ✅ 路径参数和 operatorId 均使用此 ID |

### userId 获取方式

1. **管理后台**（最简单）：PC 端钉钉 → 工作台 → 管理后台 → 通讯录 → 成员管理 → 点击姓名查看
2. **手机号查询**：`POST /topapi/v2/user/getbymobile?access_token=<旧版token>`
3. **机器人回调**：消息体中 `senderStaffId` 字段

### userId ↔ unionId 互转

以下 API 使用**旧版 access_token**（`GET https://oapi.dingtalk.com/gettoken?appkey=&appsecret=`）：

| 方向 | API | 请求 body | 返回值 |
|---|---|---|---|
| userId → unionId | `POST /topapi/v2/user/get?access_token=<旧版token>` | `{"userid": "<userId>"}` | `result.unionid`（**注意**：无下划线的 `unionid` 有值，`union_id` 可能为空） |
| unionId → userId | `POST /topapi/user/getbyunionid?access_token=<旧版token>` | `{"unionid": "<unionId>"}` | `result.userid` |

---

## 1. 创建待办

**POST** `/v1.0/todo/users/{unionId}/tasks?operatorId={unionId}`

### 请求体

```json
{
  "subject": "完成需求评审（必填）",
  "description": "详细说明（选填）",
  "dueTime": 1700000000000,
  "reminderTimeStamp": 1699990000000,
  "priority": 10,
  "executorIds": ["unionId1", "unionId2"],
  "participantIds": ["unionId3"]
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `subject` | string | ✅ | 待办标题 |
| `description` | string | — | 描述 |
| `dueTime` | long | — | 截止时间（毫秒时间戳，0 表示无截止） |
| `reminderTimeStamp` | long | — | 提醒时间（毫秒时间戳） |
| `priority` | int | — | 优先级（10=高, 20=中默认, 30=低） |
| `executorIds` | string[] | — | 执行者 unionId 列表 |
| `participantIds` | string[] | — | 参与者 unionId 列表 |

### 响应

```json
{
  "id": "taskXXXXXXXXXXXXXXXX",
  "subject": "完成需求评审",
  "done": false,
  "dueTime": 1700000000000,
  "priority": 20,
  "creatorId": "unionId",
  "bizTag": "teambition",
  "createdTime": 1700000000000,
  "modifiedTime": 1700000000000
}
```

> ⚠️ 返回的任务 ID 字段名为 `id`，不是 `taskId`

---

## 2. 获取待办详情

**GET** `/v1.0/todo/users/{unionId}/tasks/{taskId}`

无请求体。

### 响应

```json
{
  "id": "taskXXXXXXXXXXXXXXXX",
  "subject": "完成需求评审",
  "description": "详细说明",
  "done": false,
  "dueTime": 1700000000000,
  "priority": 20,
  "creatorId": "unionId",
  "executorIds": ["unionId1"],
  "participantIds": ["unionId2"],
  "detailUrl": {
    "appUrl": "dingtalk://...",
    "pcUrl": "https://..."
  }
}
```

> 删除后调用 GET 会返回 HTTP 400，body 包含 `"task not exist"`

---

## 3. 查询待办列表

**POST** `/v1.0/todo/users/{unionId}/tasks/list?operatorId={unionId}`

> ⚠️ 需要应用权限：`Todo.Todo.Read` 或 `Custom.Todo.Read`（查询三方/自建应用待办）

### 请求体

```json
{
  "isDone": false,
  "nextToken": "",
  "fromDueTime": 0,
  "toDueTime": 0
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `isDone` | bool | true=已完成，false=未完成 |
| `nextToken` | string | 分页游标，首次传空字符串 |
| `fromDueTime` | long | 截止时间起始过滤（毫秒） |
| `toDueTime` | long | 截止时间结束过滤（毫秒） |

### 响应

```json
{
  "todoCards": [
    {
      "id": "taskXXXXXXXXXXXXXXXX",
      "subject": "完成需求评审",
      "done": false,
      "dueTime": 1700000000000,
      "priority": 20
    }
  ],
  "nextToken": "下一页游标（末页时为空）"
}
```

---

## 4. 更新待办

**PUT** `/v1.0/todo/users/{unionId}/tasks/{taskId}?operatorId={unionId}`

### 请求体（所有字段均可选）

```json
{
  "subject": "新标题",
  "description": "新描述",
  "done": true,
  "dueTime": 1700000000000
}
```

### 响应

```json
{
  "requestId": "xxxxxxxx",
  "result": true
}
```

---

## 5. 删除待办

**DELETE** `/v1.0/todo/users/{unionId}/tasks/{taskId}?operatorId={unionId}`

无请求体。

### 响应

```json
{
  "requestId": "xxxxxxxx",
  "result": true
}
```

---

## 错误码

| HTTP 状态码 | code | 说明 | 处理建议 |
|---|---|---|---|
| 400 | `ResourceNotFound.TaskNotExist` | 任务不存在（含已删除） | 确认 taskId 是否正确 |
| 403 | `Forbidden.AccessDenied.*` | 缺少对应权限 | 在开放平台申请 `Todo.Todo.Write`、`Todo.Todo.Read` 或 `Custom.Todo.Read` |
| 401 | `Unauthorized` | token 无效或过期 | 重新获取 accessToken |

---

## 所需应用权限

| 权限 | 操作范围 |
|---|---|
| `Todo.Todo.Write` | 创建 / 更新 / 删除待办 |
| `Todo.Todo.Read` | 查询企业下用户待办列表 |
| `Custom.Todo.Read` | 查询用户企业类型待办列表（含三方/自建应用产生的待办） |

申请地址：开放平台 → 应用管理 → 权限管理 → 搜索对应权限名称
