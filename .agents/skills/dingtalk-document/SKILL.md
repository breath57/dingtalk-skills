---
name: dingtalk-document
description: 钉钉知识库和文档管理操作。当用户提到"钉钉文档"、"知识库"、"新建文档"、"查看文档目录"、"文档成员"、"dingtalk doc"、"knowledge base"时使用此技能。支持：创建知识库、查询知识库列表、新建文档/文件夹、管理成员权限等全部文档类操作。
---

# 钉钉文档技能

负责钉钉知识库和文档的所有操作，通过钉钉开放平台 API 实现。

API 详情见 `references/api.md`。

---

## 认证

所有接口需要先获取 `accessToken`：

```
POST https://api.dingtalk.com/v1.0/oauth2/accessToken
Content-Type: application/json

{
  "appKey": "<应用 appKey>",
  "appSecret": "<应用 appSecret>"
}
```

返回示例：
```json
{ "accessToken": "xxx", "expireIn": 7200 }
```

所有后续请求均需携带请求头：
```
x-acs-dingtalk-access-token: <accessToken>
```

若用户未提供 `appKey`/`appSecret`，主动询问。凭证不可硬编码。

---

## 核心操作

### 1. 查询用户知识库列表

用户想查看有哪些知识库时：

```
GET https://api.dingtalk.com/v1.0/doc/spaces?maxResults=20&nextToken=<分页令牌>
x-acs-dingtalk-access-token: <accessToken>
```

如有 `nextToken` 则继续翻页，直到无 `nextToken` 为止。

---

### 2. 创建知识库

```
POST https://api.dingtalk.com/v1.0/doc/spaces
x-acs-dingtalk-access-token: <accessToken>
Content-Type: application/json

{
  "name": "<知识库名称>",
  "description": "<描述（可选）>"
}
```

返回 `spaceId`，后续操作需要保存此值。

---

### 3. 查询知识库信息

```
GET https://api.dingtalk.com/v1.0/doc/spaces/{spaceId}
x-acs-dingtalk-access-token: <accessToken>
```

---

### 4. 查询目录结构

用户想看知识库里有哪些文档/文件夹时：

```
GET https://api.dingtalk.com/v1.0/doc/spaces/{spaceId}/nodes?maxResults=50&nextToken=<令牌>
x-acs-dingtalk-access-token: <accessToken>
```

查询指定文件夹的子节点，追加 `?parentNodeId=<nodeId>`。

每个节点包含：`nodeId`、`title`、`nodeType`（`DOC`/`FOLDER`）、`url`。

---

### 5. 查询单个节点信息

```
GET https://api.dingtalk.com/v1.0/doc/spaces/{spaceId}/nodes/{nodeId}
x-acs-dingtalk-access-token: <accessToken>
```

---

### 6. 创建文档或文件夹

```
POST https://api.dingtalk.com/v1.0/doc/spaces/{spaceId}/nodes
x-acs-dingtalk-access-token: <accessToken>
Content-Type: application/json

{
  "parentNodeId": "<父节点 ID，根目录可省略>",
  "nodeType": "DOC",
  "title": "<文档标题>",
  "templateType": "BLANK"
}
```

`nodeType` 可选值：
- `DOC`：普通文档
- `FOLDER`：文件夹

返回 `nodeId` 和 `url`（文档链接）。

---

### 7. 知识库成员管理

**添加成员：**
```
POST https://api.dingtalk.com/v1.0/doc/spaces/{spaceId}/members
Content-Type: application/json

{
  "members": [
    { "id": "<userId>", "roleType": "editor" }
  ]
}
```

`roleType` 可选：`viewer`（可见）、`editor`（可编辑）、`admin`（管理员）

**更新成员权限：**
```
PUT https://api.dingtalk.com/v1.0/doc/spaces/{spaceId}/members/{memberId}
{ "roleType": "viewer" }
```

**移除成员：**
```
DELETE https://api.dingtalk.com/v1.0/doc/spaces/{spaceId}/members/{memberId}
```

---

## 典型场景

### "帮我在钉钉创建一个文档"
1. 询问放到哪个知识库（列出知识库或让用户说名称）
2. 调用 `POST /doc/spaces/{spaceId}/nodes`，`nodeType: DOC`
3. 返回文档链接给用户

### "查看知识库 X 下有哪些文档"
1. 通过列表查到对应 `spaceId`
2. 调用 `GET /doc/spaces/{spaceId}/nodes`
3. 整理成目录树展示

### "把用户 xxx 加到知识库 Y"
1. 确认知识库的 `spaceId`
2. 调用 `POST /doc/spaces/{spaceId}/members`，指定 `roleType`

---

## 错误处理

| HTTP 状态码 | 含义 | 处理方式 |
|---|---|---|
| 401 | token 过期 | 重新获取 accessToken 后重试 |
| 403 | 权限不足 | 提示用户检查应用权限配置 |
| 404 | 知识库或节点不存在 | 请用户确认 ID 是否正确 |
| 429 | 触发限流 | 等待 1 秒后重试 |

发生错误时，将响应体中的 `code` 和 `message` 展示给用户辅助排查。
