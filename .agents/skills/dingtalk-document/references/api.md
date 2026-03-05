# 钉钉文档 API 参考

基础地址：`https://api.dingtalk.com/v1.0`

认证请求头：`x-acs-dingtalk-access-token: <accessToken>`

---

## 知识库（Space）

### 查询知识库列表
```
GET /doc/spaces
Query 参数：maxResults（默认 20）、nextToken（分页）
```

返回示例：
```json
{
  "spaces": [
    {
      "spaceId": "xxx",
      "name": "团队知识库",
      "description": "",
      "createTime": "2024-01-01T00:00:00Z",
      "modifyTime": "2024-06-01T00:00:00Z"
    }
  ],
  "nextToken": "..."
}
```

---

### 创建知识库
```
POST /doc/spaces
请求体：{ "name": string（必填）, "description": string（可选）}
```

返回：`{ "spaceId": "xxx" }`

---

### 查询知识库信息
```
GET /doc/spaces/{spaceId}
```

返回：知识库详情对象（同列表中单个 space 结构）

---

## 文档节点（Node）

### 查询目录/节点列表
```
GET /doc/spaces/{spaceId}/nodes
Query 参数：parentNodeId（可选）、maxResults、nextToken
```

返回示例：
```json
{
  "nodes": [
    {
      "nodeId": "xxx",
      "title": "产品文档",
      "nodeType": "FOLDER",
      "url": "https://alidocs.dingtalk.com/...",
      "createTime": "...",
      "modifyTime": "..."
    }
  ],
  "nextToken": "..."
}
```

`nodeType`：`DOC`（文档）| `FOLDER`（文件夹）

---

### 查询单个节点
```
GET /doc/spaces/{spaceId}/nodes/{nodeId}
```

---

### 创建节点（文档或文件夹）
```
POST /doc/spaces/{spaceId}/nodes
请求体：
{
  "parentNodeId": string（可选，省略则在根目录），
  "nodeType": "DOC" | "FOLDER",
  "title": string,
  "templateType": "BLANK"（nodeType 为 DOC 时）
}
```

返回：`{ "nodeId": "xxx", "url": "https://..." }`

---

## 文档正文内容（DocContent）

> `workbookId` 即节点的 `nodeId`（`nodeType: DOC`）。

### 读取文档内容
```
GET /doc/workbooks/{workbookId}/docContent
```

返回示例：
```json
{
  "docContent": "# 标题\n\n正文内容...",
  "contentType": "MARKDOWN"
}
```

`contentType` 固定为 `MARKDOWN`，`docContent` 为完整的 Markdown 文本。

---

### 写入/覆盖文档内容
```
PUT /doc/workbooks/{workbookId}/docContent
请求体：
{
  "docContent": string（Markdown 格式正文，必填），
  "contentType": "MARKDOWN"
}
```

⚠️ 此操作**全量覆盖**文档内容，不可撤销。

返回：`200 OK`（无响应体）

---

## 成员权限

### 添加知识库成员
```
POST /doc/spaces/{spaceId}/members
请求体：
{
  "members": [
    { "id": "<userId>", "roleType": "viewer" | "editor" | "admin" }
  ]
}
```

---

### 更新知识库成员权限
```
PUT /doc/spaces/{spaceId}/members/{memberId}
请求体：{ "roleType": "viewer" | "editor" | "admin" }
```

---

### 移除知识库成员
```
DELETE /doc/spaces/{spaceId}/members/{memberId}
```

---

### 添加文档节点成员
```
POST /doc/spaces/{spaceId}/nodes/{nodeId}/members
请求体：
{
  "members": [
    { "id": "<userId>", "roleType": "viewer" | "editor" }
  ]
}
```

---

### 更新文档节点成员权限
```
PUT /doc/spaces/{spaceId}/nodes/{nodeId}/members/{memberId}
请求体：{ "roleType": "viewer" | "editor" }
```

---

### 移除文档节点成员
```
DELETE /doc/spaces/{spaceId}/nodes/{nodeId}/members/{memberId}
```

---

## 常见错误码

| 错误码 | 说明 |
|---|---|
| `Forbidden.AccessDenied` | 应用缺少权限或用户未授权 |
| `InvalidParameter` | 请求字段缺失或格式不正确 |
| `NotFound.Space` | spaceId 不存在 |
| `NotFound.Node` | nodeId 不存在 |
| `LimitExceeded.Qps` | 触发 QPS 限流，1 秒后重试 |

---

## 所需应用权限

在钉钉开放平台 → 应用 → 权限管理中开通：
- 读取文档内容（docContent 读取必须）
- 写入文档内容（docContent 写入必须）
- 管理知识库
