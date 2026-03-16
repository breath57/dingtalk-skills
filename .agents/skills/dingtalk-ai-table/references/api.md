# dingtalk-ai-table API 参考

> 所有接口均已验证可用。钉钉 AI 表格（`.able` 文件）使用 **Notable API**，与普通电子表格 API 完全不同。
> `NEW_TOKEN` = 新版 token（`api.dingtalk.com` 用），获取方式 `bash scripts/dt_helper.sh --token`
> `OPERATOR_ID` = 用户 unionId，获取方式 `bash scripts/dt_helper.sh --get DINGTALK_MY_OPERATOR_ID`
> `{base_id}` = AI 表格文件的 nodeId（从分享链接 `/nodes/<nodeId>` 提取）

---

## 1. 列出工作表

```
GET https://api.dingtalk.com/v1.0/notable/bases/{base_id}/sheets?operatorId={OPERATOR_ID}
Header: x-acs-dingtalk-access-token: {NEW_TOKEN}
```

无请求体。

响应：
```json
{
  "value": [
    { "id": "HAcL4SD", "name": "项目" },
    { "id": "nr2iEiW", "name": "任务" }
  ]
}
```

---

## 2. 查询单个工作表

```
GET https://api.dingtalk.com/v1.0/notable/bases/{base_id}/sheets/{sheet_id}?operatorId={OPERATOR_ID}
Header: x-acs-dingtalk-access-token: {NEW_TOKEN}
```

无请求体。

响应：
```json
{ "id": "HAcL4SD", "name": "项目" }
```

---

## 3. 创建工作表

```
POST https://api.dingtalk.com/v1.0/notable/bases/{base_id}/sheets?operatorId={OPERATOR_ID}
Header: x-acs-dingtalk-access-token: {NEW_TOKEN}
```

请求体：
```json
{
  "name": "新工作表",
  "fields": [
    { "name": "标题", "type": "text" },
    { "name": "数量", "type": "number" }
  ]
}
```

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | string | ✅ | 工作表名称 |
| `fields` | array | ❌ | 初始字段定义，省略则创建空工作表 |

响应：
```json
{ "id": "zHTWNlh", "name": "新工作表" }
```

---

## 4. 删除工作表

```
DELETE https://api.dingtalk.com/v1.0/notable/bases/{base_id}/sheets/{sheet_id}?operatorId={OPERATOR_ID}
Header: x-acs-dingtalk-access-token: {NEW_TOKEN}
```

无请求体。

响应：`{ "success": true }`

> ⚠️ 不可恢复，执行前需用户确认。

---

## 5. 列出字段

```
GET https://api.dingtalk.com/v1.0/notable/bases/{base_id}/sheets/{sheet_id}/fields?operatorId={OPERATOR_ID}
Header: x-acs-dingtalk-access-token: {NEW_TOKEN}
```

无请求体。

响应：
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

## 6. 创建字段

```
POST https://api.dingtalk.com/v1.0/notable/bases/{base_id}/sheets/{sheet_id}/fields?operatorId={OPERATOR_ID}
Header: x-acs-dingtalk-access-token: {NEW_TOKEN}
```

请求体：
```json
{
  "name": "字段名称",
  "type": "number"
}
```

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | string | ✅ | 字段名称 |
| `type` | string | ✅ | 字段类型：`text`（文本）、`number`（数字）、`date`（日期） |

响应：
```json
{
  "id": "mr8APlG",
  "name": "字段名称",
  "type": "number",
  "property": { "formatter": "INT" }
}
```

---

## 7. 更新字段

```
PUT https://api.dingtalk.com/v1.0/notable/bases/{base_id}/sheets/{sheet_id}/fields/{field_id}?operatorId={OPERATOR_ID}
Header: x-acs-dingtalk-access-token: {NEW_TOKEN}
```

请求体：
```json
{ "name": "新字段名称" }
```

响应：`{ "id": "fieldId" }`

> 仅返回 id，通过重新查询字段列表确认名称已变更。

---

## 8. 删除字段

```
DELETE https://api.dingtalk.com/v1.0/notable/bases/{base_id}/sheets/{sheet_id}/fields/{field_id}?operatorId={OPERATOR_ID}
Header: x-acs-dingtalk-access-token: {NEW_TOKEN}
```

无请求体。

响应：`{ "success": true }`

> ⚠️ 删除字段会同时删除该列所有数据，执行前需用户确认。

---

## 9. 新增记录

```
POST https://api.dingtalk.com/v1.0/notable/bases/{base_id}/sheets/{sheet_id}/records?operatorId={OPERATOR_ID}
Header: x-acs-dingtalk-access-token: {NEW_TOKEN}
```

请求体：
```json
{
  "records": [
    { "fields": { "标题": "任务一", "数量": 3 } },
    { "fields": { "标题": "任务二", "数量": 5 } }
  ]
}
```

> `fields` 中使用**字段名称**（非 ID）作为键。先用「5. 列出字段」确认现有字段名。

响应：
```json
{
  "value": [
    { "id": "RNXU1Vm2L2" },
    { "id": "LK0kdIxCQU" }
  ]
}
```

---

## 10. 查询记录列表

```
POST https://api.dingtalk.com/v1.0/notable/bases/{base_id}/sheets/{sheet_id}/records/list?operatorId={OPERATOR_ID}
Header: x-acs-dingtalk-access-token: {NEW_TOKEN}
```

请求体：
```json
{
  "maxResults": 20,
  "nextToken": ""
}
```

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `maxResults` | int | ❌ | 每页数量，默认 20 |
| `nextToken` | string | ❌ | 分页令牌，首次为空 |

响应：
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

> 翻页：`hasMore=true` 时，将 `nextToken` 传入下次请求继续获取。

---

## 11. 更新记录

```
PUT https://api.dingtalk.com/v1.0/notable/bases/{base_id}/sheets/{sheet_id}/records?operatorId={OPERATOR_ID}
Header: x-acs-dingtalk-access-token: {NEW_TOKEN}
```

请求体：
```json
{
  "records": [
    { "id": "RNXU1Vm2L2", "fields": { "标题": "新标题" } }
  ]
}
```

> 只传需要修改的字段，未传字段保持不变。

响应：`{ "value": [{ "id": "RNXU1Vm2L2" }] }`

---

## 12. 删除记录

```
POST https://api.dingtalk.com/v1.0/notable/bases/{base_id}/sheets/{sheet_id}/records/delete?operatorId={OPERATOR_ID}
Header: x-acs-dingtalk-access-token: {NEW_TOKEN}
```

请求体：
```json
{ "recordIds": ["RNXU1Vm2L2", "LK0kdIxCQU"] }
```

响应：`{ "success": true }`

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
