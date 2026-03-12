---
name: dingtalk-ai-table
description: 钉钉 AI 表格（多维表格）操作。当用户提到"钉钉AI表格"、"AI表格"、"多维表格"、"工作表"、"字段"、"记录"、"新增记录"、"查询记录"、"更新记录"、"删除记录"、"新建字段"、"删除字段"、"dingtalk AI table"、"dingtalk notable"、"able文件"时使用此技能。支持工作表管理、字段管理、记录的增删改查等全部操作。
---

# 钉钉 AI 表格技能

负责钉钉 AI 表格（`.able` 格式多维表格）的所有操作，通过钉钉开放平台 Notable API 实现。

**核心概念：**
- **AI 表格**（`.able` 文件）：多维表格，使用 Notable API（`/v1.0/notable`），**不是**普通电子表格
- **base_id**：AI 表格文件的 nodeId，是表格在钉钉文档系统中的唯一标识
- **工作表（Sheet）**：AI 表格内的单张表，包含字段和记录
- **字段（Field）**：列定义，有名称和类型（`text`、`number`、`date` 等）
- **记录（Record）**：数据行，包含各字段的值

API 详情见 `references/api.md`。

---

## 配置管理（每次开始前必读）

### 配置文件路径

`~/.dingtalk-skills/config`（跨会话保留，所有 dingtalk-skills 共用同一文件）

### 本技能需要的配置说明

| 键 | 说明 | 来源 |
|---|---|---|
| `DINGTALK_APP_KEY` | 钉钉应用 appKey | 开放平台 → 应用管理 → 凭证信息 |
| `DINGTALK_APP_SECRET` | 钉钉应用 appSecret | 同上 |
| `DINGTALK_USER_ID` | 当前用户的企业员工 ID（userId） | 管理后台 → 通讯录 → 成员管理 → 点击姓名查看（不是手机号、不是 unionId） |
| `DINGTALK_OPERATOR_ID` | 当前用户的 unionId | 首次由脚本自动通过 userId 转换获取并写入 |
| `DINGTALK_AI_TABLE_BASE_ID` | AI 表格的 nodeId | 从 AI 表格分享链接提取 |

### 启动流程（每次执行任务前）

1. **读取配置**：检查 `~/.dingtalk-skills/config` 是否存在，解析已有键值
2. **识别缺失项**：找出上表中尚未配置的键
3. **一次性收集**：将所有缺失项合并为一条提问，**不要逐条询问**，例如：
   > 需要以下信息才能继续（已有的无需再填）：
   > - 钉钉应用 appKey（钉钉开放平台 → 应用管理 → 凭证信息）
   > - 钉钉应用 appSecret
   > - AI 表格链接（用于提取 base_id）
   > - 你的钉钉 userId（管理后台 → 通讯录 → 成员管理 → 点击姓名查看）
4. **持久化**：将用户提供的值追加写入 config，后续直接读取，无需再问
5. **执行任务**：配置完整后开始操作

> **注意**：`APP_KEY`/`APP_SECRET`/`OPERATOR_ID` 属于凭证，禁止在输出中完整打印，确认时仅显示前 4 位 + `****`。

---

## 认证

每次调用 API 前，用 appKey/appSecret 获取当次的 accessToken（有效期 2 小时）：

```
POST https://api.dingtalk.com/v1.0/oauth2/accessToken
Content-Type: application/json

{ "appKey": "<应用 appKey>", "appSecret": "<应用 appSecret>" }
```

所有请求需携带：
- 请求头：`x-acs-dingtalk-access-token: <accessToken>`
- 查询参数：`operatorId=<用户 unionId>`（所有写操作及部分读操作必须）

---

## 为什么需要 base_id

钉钉文档系统中每个文件（文档、表格、AI 表格）都有一个全局唯一的 **nodeId**，即 `base_id`。它的作用类似数据库主键——API 通过它定位到具体是哪个 AI 表格文件，因为账号下可能有多个 `.able` 文件。

**从链接提取 base_id：**

```
https://alidocs.dingtalk.com/i/nodes/<base_id>?...
                                     ↑ 这一段就是 base_id
```

请用户提供 AI 表格的分享链接，从 `/nodes/` 后截取 ID 片段。首次获取后写入 config，后续无需再问。

---

## 为什么需要 operatorId（unionId）

钉钉开放平台要求所有**写操作**必须代表一个真实用户身份执行，而不是以匿名应用身份操作。`operatorId` 就是声明"这个操作是谁做的"——它会被记录到变更日志、触发对应用户的通知，并用于权限校验。

- AI 表格 API 的 `operatorId` 参数使用 **unionId**（跨组织唯一），**不是** userId
- 配置中优先收集 `userId`（管理后台直接查看），系统自动转换为 `unionId`

### 身份标识说明

| 标识 | 说明 | 如何获取 |
|---|---|---|
| `userId`（= `staffId`） | 企业内部员工 ID，**最容易获取** | 管理后台 → 通讯录 → 成员管理 → 点击姓名查看 |
| `unionId` | 跨企业/跨应用唯一 | 通过 userId 调用 API 转换获取 |

### userId → unionId 自动转换

当配置中有 `DINGTALK_USER_ID` 但缺少 `DINGTALK_OPERATOR_ID` 时，自动执行转换：

```bash
# 1. 获取旧版 token
OLD_TOKEN=$(curl -s "https://oapi.dingtalk.com/gettoken?appkey=${APP_KEY}&appsecret=${APP_SECRET}" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

# 2. userId → unionId
UNION_ID=$(curl -s -X POST "https://oapi.dingtalk.com/topapi/v2/user/get?access_token=${OLD_TOKEN}" \
  -H 'Content-Type: application/json' \
  -d "{\"userid\":\"${USER_ID}\"}" | grep -o '"unionid":"[^"]*"' | cut -d'"' -f4)

# 3. 写入配置文件
echo "DINGTALK_OPERATOR_ID=$UNION_ID" >> ~/.dingtalk-skills/config
```

> ⚠️ 注意：返回体中 `result.unionid`（无下划线）有值，`result.union_id`（有下划线）可能为空。

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
