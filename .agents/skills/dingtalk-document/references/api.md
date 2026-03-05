# 钉钉文档 API 参考

基础地址：`https://api.dingtalk.com`

认证请求头：`x-acs-dingtalk-access-token: <accessToken>`

> **重要**：Wiki 相关所有接口均需传 `operatorId`（用户 unionId），缺少则返回 `MissingoperatorId` 错误。

---

## 知识库（Workspace）

### 查询知识库列表
```
GET /v2.0/wiki/workspaces
Query 参数：operatorId（必填，unionId）、maxResults（默认20）、nextToken（分页）
```

返回示例：
```json
{
  "workspaces": [
    {
      "workspaceId": "QXvd5SLN2AxOQz0Z",
      "name": "团队知识库",
      "description": "...",
      "rootNodeId": "P0MALyR8kl3qpB7qTkM1xn3mW3bzYmDO",
      "type": "TEAM",
      "url": "https://alidocs.dingtalk.com/i/spaces/.../overview",
      "createTime": "2024-01-01T00:00Z",
      "modifiedTime": "2024-06-01T00:00Z"
    }
  ],
  "nextToken": "..."
}
```

---

### 查询知识库信息
```
GET /v2.0/wiki/workspaces/{workspaceId}
Query 参数：operatorId（必填）
```

返回：单个 workspace 对象（同列表结构）

---

## 文档节点（Node）

### 查询节点列表
```
GET /v2.0/wiki/nodes
Query 参数：parentNodeId（必填，传根节点 rootNodeId 可列出顶层内容）、operatorId（必填）、maxResults、nextToken
```

返回示例：
```json
{
  "nodes": [
    {
      "nodeId": "LeBq413JAw31yaz1fB0BBdLGWDOnGvpb",
      "name": "send.sh 钉钉消息发送使用文档.adoc",
      "type": "FILE",
      "category": "ALIDOC",
      "extension": "adoc",
      "workspaceId": "QXvd5SnBnzmZdZ0Z",
      "url": "https://alidocs.dingtalk.com/i/nodes/LeBq413JAw31yaz1fB0BBdLGWDOnGvpb",
      "createTime": "2026-03-04T16:58Z",
      "modifiedTime": "2026-03-04T17:51Z"
    }
  ],
  "nextToken": "..."
}
```

`type`：`FILE`（文档/文件）| `FOLDER`（文件夹）

---

### 查询单个节点（通过 nodeId）
```
GET /v2.0/wiki/nodes/{nodeId}
Query 参数：operatorId（必填）
```

返回：`{ "node": { nodeId, name, type, category, workspaceId, url, ... } }`

---

### 通过 URL 查询节点
```
POST /v2.0/wiki/nodes/queryByUrl?operatorId=<unionId>
请求体：
{
  "url": "https://alidocs.dingtalk.com/i/nodes/<nodeId>",
  "operatorId": "<unionId>"
}
```

返回与 GET 单个节点相同的 node 结构。

---

### 创建文档
```
POST /v1.0/doc/workspaces/{workspaceId}/docs
请求体：
{
  "operatorId": "<unionId>"（必填），
  "docType": "DOC"（固定值，ALIDOC 富文本格式），
  "name": string（文档标题，必填）
}
```

返回：
```json
{
  "nodeId": "xxx",    // 知识库节点 ID（用于删除）
  "docKey": "yyy",   // 文档内容 Key（用于内容读写，≠ nodeId）
  "workspaceId": "zzz",  // 实际所在知识库（可能与请求不同，删除须使用此值）
  "url": "https://..."
}
```

### 删除文档
```
DELETE /v1.0/doc/workspaces/{workspaceId}/docs/{nodeId}
Query 参数：operatorId（必填）
```

`workspaceId` 和 `nodeId` 均使用创建文档响应中的值。成功返回 `200 {}`。

---

## 文档正文内容

> 读取/写入内容时使用 `docKey`（来自创建文档响应或 wiki nodes 响应的 `nodeId`）。
> 注意：通过 wiki nodes API 获取的节点，其 `nodeId` 即为 `docKey`；
> 通过创建文档 API 新建的文档，`docKey` 与 `nodeId` **是不同的值**，须使用响应中的 `docKey`。

### 读取文档 Block 内容
```
GET /v1.0/doc/suites/documents/{docKey}/blocks
Query 参数：operatorId（必填）
所需权限：Storage.File.Read
```

返回示例：
```json
{
  "result": {
    "data": [
      { "blockType": "heading", "heading": { "level": "heading-2", "text": "快速开始" }, "index": 0, "id": "mmbtk3u2nsn5gclyyu" },
      { "blockType": "paragraph", "paragraph": { "text": "每次发送前脚本会显示确认框..." }, "index": 1, "id": "mmbtk3u3vv0xa7jo5mf" },
      { "blockType": "table", "table": { "colSize": 2, "rowSize": 10 }, "index": 2, "id": "xxx" },
      { "blockType": "unknown", "index": 3, "id": "yyy", "unknown": {} }
    ]
  },
  "success": true
}
```

`blockType` 枚举：`heading`、`paragraph`、`unorderedList`、`orderedList`、`table`、`blockquote`、`unknown`（代码块/图片等）

---

### 覆盖写入文档内容
```
POST /v1.0/doc/suites/documents/{docKey}/overwriteContent
请求体：
{
  "operatorId": "<unionId>"（必填），
  "docContent": string（Markdown 格式正文），
  "contentType": "markdown"
}
```

⚠️ 此操作**全量覆盖**文档内容，不可撤销。

---

### 追加文本到段落
```
POST /v1.0/doc/suites/documents/{docKey}/blocks/{blockId}/paragraph/appendText
请求体：{ "operatorId": "<unionId>", "text": "追加的文字" }
```

---

## 成员管理

### 添加文档成员
```
POST /v1.0/doc/workspaces/{workspaceId}/docs/{nodeId}/members
请求体：
{
  "operatorId": "<unionId>",
  "members": [
    { "id": "<userId>", "roleType": "viewer" | "editor" }
  ]
}
```

---

### 更新文档成员权限
```
PUT /v1.0/doc/workspaces/{workspaceId}/docs/{nodeId}/members/{memberId}
请求体：{ "operatorId": "<unionId>", "roleType": "viewer" | "editor" }
```

---

### 移除文档成员
```
DELETE /v1.0/doc/workspaces/{workspaceId}/docs/{nodeId}/members/{memberId}
Query 参数：operatorId（必填）
```

---

## 常见错误码

| HTTP | 错误码 | 说明 | 处理 |
|---|---|---|---|
| 400 | `MissingoperatorId` | operatorId 未传 | 补充 operatorId（unionId）|
| 400 | `paramError` | 参数类型错误 | operatorId 必须是 unionId，非 userId |
| 403 | `Forbidden.AccessDenied.AccessTokenPermissionDenied` | 应用缺少权限 | 错误中有 `requiredScopes`，开通对应权限 |
| 404 | `InvalidAction.NotFound` | 接口路径不存在 | 检查版本号和路径 |
| 429 | — | QPS 限流 | 1 秒后重试 |

---

## 所需应用权限

| 功能 | 权限 scope |
|---|---|
| 查询知识库/节点 | `Wiki.Node.Read` |
| 读取文档正文（blocks）| `Storage.File.Read` |
| 写入文档正文 | `Storage.File.Write` |
| 查询用户 unionId | `Contact.User.Read` |
