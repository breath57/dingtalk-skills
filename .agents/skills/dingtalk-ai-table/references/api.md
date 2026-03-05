# 钉钉 AI 表格 API 参考

> **重要：** 钉钉 AI 表格（`.able` 文件）使用 **Notable API**，  
> 路径前缀为 `/v1.0/notable`，与普通电子表格 API（`/v1.0/doc/workbooks`）完全不同。

基础地址：`https://api.dingtalk.com/v1.0/notable`

认证：
- 请求头：`x-acs-dingtalk-access-token: <accessToken>`
- 所有接口均需查询参数：`operatorId=<用户 unionId>`

`{base_id}` = AI 表格文件的 **nodeId**（从分享链接 `/nodes/<nodeId>` 提取）

---

## 工作表（Sheet）

### 查询所有工作表
```
GET /notable/bases/{base_id}/sheets?operatorId={operatorId}
```

返回示例：
```json
{
  "value": [
    { "id": "HAcL4SD", "name": "项目" },
    { "id": "nr2iEiW", "name": "任务" }
  ]
}
```

---

### 查询单个工作表
```
GET /notable/bases/{base_id}/sheets/{sheet_id}?operatorId={operatorId}
```

返回示例：
```json
{ "id": "HAcL4SD", "name": "项目" }
```

---

### 创建工作表
```
POST /notable/bases/{base_id}/sheets?operatorId={operatorId}
Content-Type: application/json

{
  "name": "新工作表",
  "fields": [
    { "name": "标题", "type": "text" },
    { "name": "数量", "type": "number" }
  ]
}
```

`fields` 为可选，省略则创建空工作表。  
返回：`{ "id": "zHTWNlh", "name": "新工作表" }`

---

### 删除工作表
```
DELETE /notable/bases/{base_id}/sheets/{sheet_id}?operatorId={operatorId}
```

返回：`{ "success": true }`

---

## 字段（Field）

### 查询所有字段
```
GET /notable/bases/{base_id}/sheets/{sheet_id}/fields?operatorId={operatorId}
```

返回示例：
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

### 创建字段
```
POST /notable/bases/{base_id}/sheets/{sheet_id}/fields?operatorId={operatorId}
Content-Type: application/json

{
  "name": "字段名称",
  "type": "number"
}
```

常用 `type` 值：`text`、`number`、`date`  
返回示例：
```json
{
  "id": "mr8APlG",
  "name": "字段名称",
  "type": "number",
  "property": { "formatter": "INT" }
}
```

---

### 更新字段
```
PUT /notable/bases/{base_id}/sheets/{sheet_id}/fields/{field_id}?operatorId={operatorId}
Content-Type: application/json

{ "name": "新字段名称" }
```

返回：`{ "id": "fieldId" }`（仅返回 id，通过 GET /fields 确认名称变更）

---

### 删除字段
```
DELETE /notable/bases/{base_id}/sheets/{sheet_id}/fields/{field_id}?operatorId={operatorId}
```

返回：`{ "success": true }`

---

## 记录（Record）

### 新增记录
```
POST /notable/bases/{base_id}/sheets/{sheet_id}/records?operatorId={operatorId}
Content-Type: application/json

{
  "records": [
    { "fields": { "标题": "任务一", "数量": 3 } },
    { "fields": { "标题": "任务二", "数量": 5 } }
  ]
}
```

`fields` 中使用**字段名称**（非 ID）作为键。  
返回示例：
```json
{
  "value": [
    { "id": "RNXU1Vm2L2" },
    { "id": "LK0kdIxCQU" }
  ]
}
```

---

### 查询记录列表
```
POST /notable/bases/{base_id}/sheets/{sheet_id}/records/list?operatorId={operatorId}
Content-Type: application/json

{
  "maxResults": 20,
  "nextToken": ""
}
```

返回示例：
```json
{
  "records": [
    {
      "id": "RNXU1Vm2L2",
      "fields": { "标题": "任务一", "数量": 3 },
      "createdTime": 1772723541439,
      "createdBy": { "unionId": "K1mxiiGFgkVfWYR5tNM04lAiEiE" },
      "lastModifiedTime": 1772723541439,
      "lastModifiedBy": { "unionId": "K1mxiiGFgkVfWYR5tNM04lAiEiE" }
    }
  ],
  "hasMore": false,
  "nextToken": ""
}
```

翻页：当 `hasMore=true` 时，将 `nextToken` 传入下次请求继续获取。

---

### 更新记录
```
PUT /notable/bases/{base_id}/sheets/{sheet_id}/records?operatorId={operatorId}
Content-Type: application/json

{
  "records": [
    { "id": "RNXU1Vm2L2", "fields": { "标题": "新标题" } }
  ]
}
```

只传需要修改的字段，未传字段保持不变。  
返回：`{ "value": [{ "id": "RNXU1Vm2L2" }] }`

---

### 删除记录
```
POST /notable/bases/{base_id}/sheets/{sheet_id}/records/delete?operatorId={operatorId}
Content-Type: application/json

{ "recordIds": ["RNXU1Vm2L2", "LK0kdIxCQU"] }
```

返回：`{ "success": true }`

---

## 错误码

| code | 说明 | 处理建议 |
|---|---|---|
| `invalidRequest.document.notFound` | base_id 无效或无访问权限 | 确认 AI 表格 nodeId 正确，且 operatorId 对应用户有权限 |
| `Forbidden.AccessDenied` | 应用未开通所需权限 | 在开发者后台开通 Notable 相关权限 |
| `InvalidParameter` | 请求参数格式有误 | 检查 fields key 是字段名称而非 ID |
| `429 TooManyRequests` | 触发限流 | 等待 1s 后重试 |

---

## 所需应用权限

| 权限名称 | 说明 |
|---|---|
| `Document.Notable.Read` | 读取 AI 表格数据 |
| `Document.Notable.Write` | 写入 / 修改 AI 表格数据 |
