# dingtalk-document API 参考

> 所有接口均已验证可用。
> `NEW_TOKEN` = 新版 token（`api.dingtalk.com` 用），获取方式 `bash scripts/dt_helper.sh --token`
> `OPERATOR_ID` = 用户 unionId，获取方式 `bash scripts/dt_helper.sh --get DINGTALK_MY_OPERATOR_ID`
> ⚠️ **重要**：所有接口均需传 `operatorId`（unionId），缺少则返回 `MissingoperatorId` 错误。

---

## 1. 查询知识库列表

```
GET https://api.dingtalk.com/v2.0/wiki/workspaces?operatorId={OPERATOR_ID}&maxResults=20&nextToken=
Header: x-acs-dingtalk-access-token: {NEW_TOKEN}
```

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `operatorId` | string | ✅ | 用户 unionId |
| `maxResults` | int | ❌ | 每页数量，默认 20 |
| `nextToken` | string | ❌ | 分页令牌，首次为空 |

响应：
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

> 翻页：`nextToken` 非空时传入下次请求继续获取。

---

## 2. 查询知识库信息

```
GET https://api.dingtalk.com/v2.0/wiki/workspaces/{workspaceId}?operatorId={OPERATOR_ID}
Header: x-acs-dingtalk-access-token: {NEW_TOKEN}
```

响应：单个 workspace 对象（结构同列表项）

---

## 3. 查询节点列表

```
GET https://api.dingtalk.com/v2.0/wiki/nodes?parentNodeId={nodeId}&operatorId={OPERATOR_ID}&maxResults=50&nextToken=
Header: x-acs-dingtalk-access-token: {NEW_TOKEN}
```

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `parentNodeId` | string | ✅ | 父节点 ID，传知识库的 `rootNodeId` 可列出顶层内容 |
| `operatorId` | string | ✅ | 用户 unionId |
| `maxResults` | int | ❌ | 每页数量，默认 20 |
| `nextToken` | string | ❌ | 分页令牌 |

响应：
```json
{
  "nodes": [
    {
      "nodeId": "LeBq413JAw31yaz1fB0BBdLGWDOnGvpb",
      "name": "使用文档.adoc",
      "type": "FILE",
      "category": "ALIDOC",
      "extension": "adoc",
      "workspaceId": "QXvd5SnBnzmZdZ0Z",
      "url": "https://alidocs.dingtalk.com/i/nodes/...",
      "createTime": "2026-03-04T16:58Z",
      "modifiedTime": "2026-03-04T17:51Z"
    }
  ],
  "nextToken": "..."
}
```

> `type`：`FILE`（文档/文件）| `FOLDER`（文件夹）

---

## 4. 查询单个节点

```
GET https://api.dingtalk.com/v2.0/wiki/nodes/{nodeId}?operatorId={OPERATOR_ID}
Header: x-acs-dingtalk-access-token: {NEW_TOKEN}
```

响应：`{ "node": { nodeId, name, type, category, workspaceId, url, ... } }`

---

## 5. 通过 URL 查询节点

```
POST https://api.dingtalk.com/v2.0/wiki/nodes/queryByUrl?operatorId={OPERATOR_ID}
Header: x-acs-dingtalk-access-token: {NEW_TOKEN}
```

请求体：
```json
{
  "url": "https://alidocs.dingtalk.com/i/nodes/<nodeId>",
  "operatorId": "{OPERATOR_ID}"
}
```

响应：与 GET 单个节点相同的 node 结构。

---

## 6. 创建文档

```
POST https://api.dingtalk.com/v1.0/doc/workspaces/{workspaceId}/docs
Header: x-acs-dingtalk-access-token: {NEW_TOKEN}
```

请求体：
```json
{
  "operatorId": "{OPERATOR_ID}",
  "docType": "DOC",
  "name": "文档标题"
}
```

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `operatorId` | string | ✅ | 用户 unionId |
| `docType` | string | ✅ | 固定填 `"DOC"`（ALIDOC 富文本格式） |
| `name` | string | ✅ | 文档标题 |

响应：
```json
{
  "dentryUuid": "aaa",
  "nodeId": "xxx",
  "docKey": "yyy",
  "workspaceId": "zzz",
  "url": "https://..."
}
```

> **重要**：
> - `docKey` / `dentryUuid`：用于 `/v1.0/doc/suites/documents/{id}` 内容读写
> - `nodeId`：用于 `/v1.0/doc/workspaces/{workspaceId}/docs/{nodeId}` 删除/管理

---

## 7. 删除文档

```
DELETE https://api.dingtalk.com/v1.0/doc/workspaces/{workspaceId}/docs/{nodeId}?operatorId={OPERATOR_ID}
Header: x-acs-dingtalk-access-token: {NEW_TOKEN}
```

> `workspaceId` 和 `nodeId` 均使用创建文档响应中的值。成功返回 `200 {}`。

---

## 8. 读取文档内容（Block 结构）

```
GET https://api.dingtalk.com/v1.0/doc/suites/documents/{docKey}/blocks?operatorId={OPERATOR_ID}
Header: x-acs-dingtalk-access-token: {NEW_TOKEN}
```

> **docKey 的来源**：
> - 通过 wiki nodes 接口查到的 `nodeId` 本质是 `dentryUuid`，可直接用于正文读写
> - 通过创建文档接口新建的文档：可使用响应中的 `docKey` 或 `dentryUuid`
> - 创建响应中的 `nodeId`（通常出现在 `/docs/<nodeId>` 链接中）不能直接用于正文读写

响应：
```json
{
  "result": {
    "data": [
      { "blockType": "heading", "heading": { "level": "heading-2", "text": "快速开始" }, "index": 0, "id": "xxx" },
      { "blockType": "paragraph", "paragraph": { "text": "正文内容..." }, "index": 1, "id": "yyy" },
      { "blockType": "table", "table": { "colSize": 2, "rowSize": 10 }, "index": 2, "id": "zzz" },
      { "blockType": "unknown", "index": 3, "id": "aaa", "unknown": {} }
    ]
  },
  "success": true
}
```

`blockType` 枚举：`heading`、`paragraph`、`unorderedList`、`orderedList`、`table`、`blockquote`、`unknown`（代码块/图片等）

---

## 9. 覆盖写入文档内容

```
POST https://api.dingtalk.com/v1.0/doc/suites/documents/{docKey}/overwriteContent?operatorId={OPERATOR_ID}
Header: x-acs-dingtalk-access-token: {NEW_TOKEN}
```

> ⚠️ `operatorId` 必须**同时**作为 query param 和请求体字段传入，缺一会报 `Missingcontent` 错误。

请求体：
```json
{
  "operatorId": "{OPERATOR_ID}",
  "content": "# 新标题\n\n新的正文内容，支持 Markdown 格式。",
  "contentType": "markdown"
}
```

> ⚠️ 此操作**全量覆盖**文档内容，不可撤销。

---

## 10. 追加文本到段落

```
POST https://api.dingtalk.com/v1.0/doc/suites/documents/{docKey}/blocks/{blockId}/paragraph/appendText
Header: x-acs-dingtalk-access-token: {NEW_TOKEN}
```

请求体：
```json
{ "operatorId": "{OPERATOR_ID}", "text": "追加的文字" }
```

---

## 11. 添加文档成员

```
POST https://api.dingtalk.com/v1.0/doc/workspaces/{workspaceId}/docs/{nodeId}/members
Header: x-acs-dingtalk-access-token: {NEW_TOKEN}
```

请求体：
```json
{
  "operatorId": "{OPERATOR_ID}",
  "members": [
    { "id": "<userId>", "roleType": "viewer" }
  ]
}
```

| 参数 | 说明 |
|---|---|
| `id` | 用户 userId（**注意**：这里用 userId，不是 unionId）|
| `roleType` | `viewer`（只读）| `editor`（可编辑）|

---

## 12. 更新文档成员权限

```
PUT https://api.dingtalk.com/v1.0/doc/workspaces/{workspaceId}/docs/{nodeId}/members/{memberId}
Header: x-acs-dingtalk-access-token: {NEW_TOKEN}
```

请求体：
```json
{ "operatorId": "{OPERATOR_ID}", "roleType": "viewer" }
```

---

## 13. 移除文档成员

```
DELETE https://api.dingtalk.com/v1.0/doc/workspaces/{workspaceId}/docs/{nodeId}/members/{memberId}?operatorId={OPERATOR_ID}
Header: x-acs-dingtalk-access-token: {NEW_TOKEN}
```

---

## 14. 搜索文档（用于找回可读写 ID）

```
GET https://api.dingtalk.com/v1.0/doc/docs?operatorId={OPERATOR_ID}&workspaceId={workspaceId}&keyword={keyword}&maxResults=20&nextToken=
Header: x-acs-dingtalk-access-token: {NEW_TOKEN}
```

说明：
- 需要权限：`Document.WorkspaceDocument.Read`
- 返回结果中的 `docs[].nodeBO.nodeId` 即可用于 `/v1.0/doc/suites/documents/{id}` 的读写（该值是 `dentryUuid` 风格 ID）

示例响应（节选）：
```json
{
  "docs": [
    {
      "nodeBO": {
        "name": "测试创建.adoc",
        "nodeId": "np9zOoBVBYwB2OZBIn4y0G1vW1DK0g6l",
        "url": "https://alidocs.dingtalk.com/i/nodes/np9zOoBVBYwB2OZBIn4y0G1vW1DK0g6l"
      },
      "workspaceBO": {
        "workspaceId": "QXvd5SLN2AxOQz0Z"
      }
    }
  ],
  "hasMore": false
}
```

---

## 错误码

| HTTP状态码 | 错误码 | 说明 | 处理建议 |
|---|---|---|---|
| 400 | `MissingoperatorId` | operatorId 未传 | 补充 operatorId（unionId）|
| 400 | `paramError` | 参数类型错误 | operatorId 必须是 unionId，不是 userId |
| 403 | `Forbidden.AccessDenied.AccessTokenPermissionDenied` | 应用缺少权限 | 错误中有 `requiredScopes`，开通对应权限 |
| 404 | `InvalidAction.NotFound` | 接口路径不存在 | 检查版本号（v1.0/v2.0）和路径 |
| 429 | — | QPS 限流 | 1 秒后重试 |

---

## 所需应用权限

| 功能 | 权限 scope |
|---|---|
| 查询知识库/节点 | `Wiki.Node.Read` |
| 读取文档正文 | `Storage.File.Read` |
| 写入文档正文 | `Storage.File.Write` |
| 创建/删除文档 | `Storage.File.Write` |
| 查询用户 unionId | `Contact.User.Read` |
