---
name: dingtalk-ai-table
description: 钉钉 AI 表格（多维表格）操作。当用户提到"钉钉AI表格"、"AI表格"、"多维表格"、"工作表"、"字段"、"记录"、"新增记录"、"查询记录"、"更新记录"、"删除记录"、"新建字段"、"删除字段"、"dingtalk AI table"、"dingtalk notable"、"able文件"时使用此技能。支持工作表管理、字段管理、记录的增删改查等全部操作。
---

# 钉钉 AI 表格技能

负责钉钉 AI 表格（`.able` 格式多维表格）的所有操作，通过钉钉开放平台 Notable API 实现。

**核心概念：**
- **AI 表格**（`.able` 文件）：多维表格，使用 Notable API（`/v1.0/notable`），**不是**普通电子表格
- **base_id**：AI 表格文件的 nodeId，从分享链接提取
- **工作表（Sheet）**：AI 表格内的单张表，包含字段和记录
- **字段（Field）**：列定义，有名称和类型（`text`、`number`、`date` 等）
- **记录（Record）**：数据行，包含各字段的值

API 详情见 `references/api.md`。

---

## 认证

```
POST https://api.dingtalk.com/v1.0/oauth2/accessToken
Content-Type: application/json

{ "appKey": "<应用 appKey>", "appSecret": "<应用 appSecret>" }
```

所有请求需携带：
- 请求头：`x-acs-dingtalk-access-token: <accessToken>`
- 查询参数：`operatorId=<用户 unionId>`（所有写操作及部分读操作必须）

若用户未提供 `appKey`、`appSecret`、`base_id`（AI 表格链接），主动询问。

---

## operatorId 说明

所有接口都**强制要求** `operatorId` 参数，值为操作人的 **`unionId`**（不是 `userId`，两者不同）。

### 方法一：已知 userId → 查 unionId（最常用）

**第一步：** 用 appKey/appSecret 获取旧式 `access_token`（与新版 accessToken 不同，单独获取）：
```
GET https://oapi.dingtalk.com/gettoken?appkey=<appKey>&appsecret=<appSecret>
```
返回：`{ "access_token": "xxx", "expires_in": 7200 }`

**第二步：** 用 userId 查询用户详情，取出 unionId：
```
POST https://oapi.dingtalk.com/topapi/v2/user/get?access_token=<旧式token>
Content-Type: application/json

{ "userid": "<钉钉 userId>" }
```
返回：`result.unionid` 字段即为 unionId。

> 专属钉钉组织：使用 `result.unionid`（无下划线），`result.union_id`（有下划线）可能为空。

### 方法二：机器人/消息场景

用户通过钉钉机器人或消息触发时，消息体中直接包含 `senderUnionId` 字段，可直接作为 `operatorId` 使用。

### 方法三：请用户告知

若上述方式不可用，可让用户提供自己的 userId（个人信息页可查），再按方法一转换。若用户不知道 userId，也可让其直接提供 unionId（在个人名片链接或开放平台用户详情中可见）。

---

## 如何获取 base_id

`base_id` 就是 AI 表格文件的 nodeId，存在于分享链接中：

```
https://alidocs.dingtalk.com/i/nodes/<base_id>?...
```

请用户提供 AI 表格链接，从中提取 `/nodes/` 后面的 ID 片段。

---

## 核心操作

### 1. 列出工作表

```
GET https://api.dingtalk.com/v1.0/notable/bases/{base_id}/sheets?operatorId={operatorId}
x-acs-dingtalk-access-token: <accessToken>
```

返回：
```json
{
  "value": [
    { "id": "HAcL4SD", "name": "项目" },
    { "id": "nr2iEiW", "name": "任务" }
  ]
}
```

---

### 2. 查询单个工作表

```
GET https://api.dingtalk.com/v1.0/notable/bases/{base_id}/sheets/{sheet_id}?operatorId={operatorId}
```

返回：`{ "id": "HAcL4SD", "name": "项目" }`

---

### 3. 新建工作表

```
POST https://api.dingtalk.com/v1.0/notable/bases/{base_id}/sheets?operatorId={operatorId}
Content-Type: application/json

{
  "name": "新工作表名称",
  "fields": [
    { "name": "标题", "type": "text" },
    { "name": "数量", "type": "number" }
  ]
}
```

`fields` 可选（不传则创建空工作表）。  
返回：`{ "id": "新sheetId", "name": "新工作表名称" }`

---

### 4. 删除工作表

```
DELETE https://api.dingtalk.com/v1.0/notable/bases/{base_id}/sheets/{sheet_id}?operatorId={operatorId}
```

返回：`{ "success": true }`  
⚠️ 不可恢复，执行前需用户确认。

---

### 5. 列出字段

```
GET https://api.dingtalk.com/v1.0/notable/bases/{base_id}/sheets/{sheet_id}/fields?operatorId={operatorId}
```

返回：
```json
{
  "value": [
    { "id": "6mNRNHb", "name": "标题", "type": "text" },
    { "id": "BDGLCo2", "name": "截止日期", "type": "date", "property": { "formatter": "YYYY-MM-DD" } },
    { "id": "mr8APlG", "name": "数量", "type": "number", "property": { "formatter": "INT" } }
  ]
}
```

---

### 6. 新建字段

```
POST https://api.dingtalk.com/v1.0/notable/bases/{base_id}/sheets/{sheet_id}/fields?operatorId={operatorId}
Content-Type: application/json

{
  "name": "字段名称",
  "type": "number"
}
```

`type` 常用值：`text`（文本）、`number`（数字）、`date`（日期）  
返回：`{ "id": "新fieldId", "name": "字段名称", "type": "number", "property": { "formatter": "INT" } }`

---

### 7. 更新字段

```
PUT https://api.dingtalk.com/v1.0/notable/bases/{base_id}/sheets/{sheet_id}/fields/{field_id}?operatorId={operatorId}
Content-Type: application/json

{
  "name": "新字段名称"
}
```

返回：`{ "id": "fieldId" }`（通过重新查询列表确认名称已变更）

---

### 8. 删除字段

```
DELETE https://api.dingtalk.com/v1.0/notable/bases/{base_id}/sheets/{sheet_id}/fields/{field_id}?operatorId={operatorId}
```

返回：`{ "success": true }`  
⚠️ 删除字段会同时删除该列所有数据，执行前需用户确认。

---

### 9. 新增记录（最常用操作）

```
POST https://api.dingtalk.com/v1.0/notable/bases/{base_id}/sheets/{sheet_id}/records?operatorId={operatorId}
Content-Type: application/json

{
  "records": [
    { "fields": { "标题": "任务一", "数量": 3 } },
    { "fields": { "标题": "任务二", "数量": 5 } }
  ]
}
```

`fields` 中使用**字段名称**（非 ID）作为键。  
返回：`{ "value": [{ "id": "记录ID1" }, { "id": "记录ID2" }] }`

---

### 10. 查询记录列表

```
POST https://api.dingtalk.com/v1.0/notable/bases/{base_id}/sheets/{sheet_id}/records/list?operatorId={operatorId}
Content-Type: application/json

{
  "maxResults": 20,
  "nextToken": ""
}
```

返回：
```json
{
  "records": [
    {
      "id": "RNXU1Vm2L2",
      "fields": { "标题": "任务一", "数量": 3 },
      "createdTime": 1772723541439,
      "createdBy": { "unionId": "xxx" },
      "lastModifiedTime": 1772723541439,
      "lastModifiedBy": { "unionId": "xxx" }
    }
  ],
  "hasMore": false,
  "nextToken": ""
}
```

翻页：上次响应 `hasMore=true` 时，将 `nextToken` 传入下次请求。

---

### 11. 更新记录

```
PUT https://api.dingtalk.com/v1.0/notable/bases/{base_id}/sheets/{sheet_id}/records?operatorId={operatorId}
Content-Type: application/json

{
  "records": [
    { "id": "记录ID", "fields": { "标题": "新标题" } }
  ]
}
```

返回：`{ "value": [{ "id": "记录ID" }] }`  
只传需要修改的字段，未传字段保持不变。

---

### 12. 删除记录

```
POST https://api.dingtalk.com/v1.0/notable/bases/{base_id}/sheets/{sheet_id}/records/delete?operatorId={operatorId}
Content-Type: application/json

{
  "recordIds": ["记录ID1", "记录ID2"]
}
```

返回：`{ "success": true }`

---

## 典型场景

### "查看 AI 表格里有哪些工作表"
1. 询问 AI 表格链接，提取 base_id
2. `GET /sheets` 获取工作表列表
3. 展示工作表名称和 ID

### "往 AI 表格的'任务'工作表添加几条记录"
1. `GET /sheets` 找到目标工作表的 sheet_id
2. `GET /fields` 了解现有字段名称和类型
3. `POST /records` 批量插入，fields 中用字段名称作键
4. 告知写入成功及记录 ID

### "查询'任务'表中所有记录"
1. `GET /sheets` 找到 sheet_id
2. `POST /records/list` 翻页获取所有记录
3. 整理为表格形式展示

### "删除某条记录"
1. 先 `POST /records/list` 定位目标记录（让用户确认）
2. `POST /records/delete` 传入 recordId
3. 告知删除成功

### "给工作表新增一个'备注'文本字段"
1. `GET /sheets` 找到 sheet_id
2. `POST /fields`，`{ "name": "备注", "type": "text" }`
3. 返回新字段 ID 并告知成功

---

## 字段类型参考

| type | 含义 |
|---|---|
| `text` | 纯文本 |
| `number` | 数字（含 `property.formatter`：`INT`、`PERCENT` 等） |
| `date` | 日期（含 `property.formatter`：如 `YYYY-MM-DD`） |

---

## 错误处理

| HTTP 状态码 / code | 含义 | 处理方式 |
|---|---|---|
| 401 | token 过期 | 重新获取 accessToken |
| 403 | 权限不足 | 检查应用是否开通 Notable 相关权限 |
| `invalidRequest.document.notFound` | base_id 无效或无权访问 | 确认 AI 表格 nodeId 正确且已授权 |
| 404 | 工作表或字段不存在 | 确认 sheet_id / field_id 正确 |
| 429 | 触发限流 | 等待 1 秒后重试 |
