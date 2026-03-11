# 钉钉消息 API 参考

> 本文档覆盖三类消息发送方式：群自定义 Webhook 机器人、企业内部应用机器人、工作通知。

---

## 一、群自定义 Webhook 机器人

基础地址：群设置中获取的 Webhook URL  
认证：无需 accessToken，URL 中自带 `access_token` 参数  
限制：每个机器人每分钟最多 20 条消息

---

### 发送消息

```
POST https://oapi.dingtalk.com/robot/send?access_token=<WEBHOOK_TOKEN>
Content-Type: application/json
```

> 若配置了加签安全模式，还需附加 `&timestamp=<ms>&sign=<签名>`

---

#### 文本消息

```json
{
  "msgtype": "text",
  "text": {
    "content": "项目 v2.1 已上线，请验收。"
  },
  "at": {
    "atMobiles": ["138xxxx1234"],
    "atUserIds": ["user123"],
    "isAtAll": false
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `msgtype` | string | ✅ | 固定 `"text"` |
| `text.content` | string | ✅ | 消息内容 |
| `at.atMobiles` | string[] | ❌ | 按手机号 @ 人 |
| `at.atUserIds` | string[] | ❌ | 按 userId @ 人 |
| `at.isAtAll` | boolean | ❌ | 是否 @所有人 |

返回示例：
```json
{ "errcode": 0, "errmsg": "ok" }
```

---

#### Markdown 消息

```json
{
  "msgtype": "markdown",
  "markdown": {
    "title": "部署通知",
    "text": "## v2.1 部署完成\n\n- **环境**：production\n- **时间**：2026-03-10 15:00\n- **状态**：✅ 成功"
  },
  "at": {
    "isAtAll": false
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `markdown.title` | string | ✅ | 推送通知展示标题 |
| `markdown.text` | string | ✅ | Markdown 正文 |

支持的 Markdown 语法：标题（`#`~`######`）、加粗、链接、图片、有序/无序列表、引用。

---

#### ActionCard（整体跳转）

```json
{
  "msgtype": "actionCard",
  "actionCard": {
    "title": "技术评审邀请",
    "text": "## 技术评审\n\n请参加明天 14:00 的架构评审会议",
    "singleTitle": "查看详情",
    "singleURL": "https://example.com/review"
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `actionCard.title` | string | ✅ | 消息标题 |
| `actionCard.text` | string | ✅ | Markdown 正文 |
| `actionCard.singleTitle` | string | ✅ | 单按钮文字 |
| `actionCard.singleURL` | string | ✅ | 按钮跳转链接 |

---

#### ActionCard（多按钮）

```json
{
  "msgtype": "actionCard",
  "actionCard": {
    "title": "选择操作",
    "text": "## 审批请求\n\n张三提交了报销申请",
    "btnOrientation": "0",
    "btns": [
      { "title": "同意", "actionURL": "https://example.com/approve" },
      { "title": "拒绝", "actionURL": "https://example.com/reject" }
    ]
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `actionCard.btnOrientation` | string | ❌ | `"0"` 竖排（默认）、`"1"` 横排 |
| `actionCard.btns` | array | ✅ | 按钮列表 |
| `btns[].title` | string | ✅ | 按钮文字 |
| `btns[].actionURL` | string | ✅ | 按钮跳转链接 |

---

#### Link 消息

```json
{
  "msgtype": "link",
  "link": {
    "title": "版本发布公告",
    "text": "v2.1 正式发布，包含性能优化和安全修复。",
    "messageUrl": "https://example.com/release",
    "picUrl": "https://example.com/logo.png"
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `link.title` | string | ✅ | 消息标题 |
| `link.text` | string | ✅ | 消息摘要 |
| `link.messageUrl` | string | ✅ | 点击跳转链接 |
| `link.picUrl` | string | ❌ | 缩略图 URL |

---

#### FeedCard 消息

```json
{
  "msgtype": "feedCard",
  "feedCard": {
    "links": [
      {
        "title": "需求评审会议纪要",
        "messageURL": "https://example.com/doc/1",
        "picURL": "https://example.com/img1.png"
      },
      {
        "title": "技术方案设计文档",
        "messageURL": "https://example.com/doc/2",
        "picURL": "https://example.com/img2.png"
      }
    ]
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `feedCard.links` | array | ✅ | FeedCard 链接列表 |
| `links[].title` | string | ✅ | 单条标题 |
| `links[].messageURL` | string | ✅ | 点击跳转链接 |
| `links[].picURL` | string | ❌ | 缩略图 URL |

---

### 加签计算（HMAC-SHA256）

适用于配置了"加签"安全模式的自定义机器人。**开启加签后，所有请求都必须带签名**，否则返回 `310000 sign not match`。

**签名算法：**

1. `timestamp` = 当前毫秒级时间戳
2. `string_to_sign` = `timestamp + "\n" + secret`
3. `sign` = URL-Safe Base64 编码（HMAC-SHA256(`secret`, `string_to_sign`）的二进制结果）

**最终请求 URL：**
```
https://oapi.dingtalk.com/robot/send?access_token=<TOKEN>&timestamp=<timestamp>&sign=<sign>
```

> timestamp 与钉钉服务器时差不能超过 1 小时，否则签名验证失败。

---

## 二、企业内部应用机器人

基础地址：`https://api.dingtalk.com/v1.0/robot`  
认证：请求头 `x-acs-dingtalk-access-token: <accessToken>`

`robotCode` 等于应用的 `appKey`（完全一致）。

#### 钉钉身份标识体系

钉钉有三种用户 ID，使用场景各不相同：

| 标识 | 说明 | 作用域 | 消息 API 支持 |
|---|---|---|---|
| `userId`（也叫 `staffId`） | 企业内部的用户 ID | 单个企业内唯一 | ✅ 机器人和工作通知 API 均只接受此 ID |
| `unionId` | 跨企业/跨应用的用户 ID | 同一法人跨组织唯一 | ❌ 不能直接用于发送消息 |
| `openId` | 第三方应用作用域的用户 ID | 单个第三方应用内唯一 | 企业内部应用不涉及 |

**重要**：所有消息发送 API（机器人单聊、群聊、工作通知）均**只接受 userId**，传入 unionId 会被判定为无效用户。

#### userId 获取方式

1. **机器人回调**（最常用）：消息体中 `senderStaffId` 字段即为发送者的 userId
2. **unionId → userId 转换**：`POST /topapi/user/getbyunionid?access_token=<旧版token>`，body: `{"unionid": "<unionId>"}`
3. **钉钉管理后台**：PC 端钉钉 → 工作台 → 管理后台 → 通讯录 → 成员详情
4. **API 查询**：`POST /topapi/v2/user/getbymobile`（按手机号查），或遍历部门成员

#### userId ↔ unionId 互转

| 方向 | API | 请求 body | 返回值 |
|---|---|---|---|
| userId → unionId | `POST /topapi/v2/user/get?access_token=<旧版token>` | `{"userid": "<userId>"}` | `result.unionid`（**注意**：无下划线的 `unionid` 有值，`union_id` 可能为空） |
| unionId → userId | `POST /topapi/user/getbyunionid?access_token=<旧版token>` | `{"unionid": "<unionId>"}` | `result.userid` |

#### openConversationId 获取方式

群聊 API 需要 `openConversationId`（以 `cid` 开头），获取方式：

1. **机器人回调**（推荐）：在群中 @机器人，回调消息体的 `conversationId` 字段即为该值
2. 调用 IM 接口创建群时返回

> 回调中 `conversationType: "2"` 表示群聊，`"1"` 表示单聊

---

### 批量发送单聊消息

```
POST /v1.0/robot/oToMessages/batchSend
Content-Type: application/json

{
  "robotCode": "<appKey>",
  "userIds": ["user001", "user002"],
  "msgKey": "sampleText",
  "msgParam": "{\"content\": \"你好，这是机器人消息\"}"
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `robotCode` | string | ✅ | 机器人 robotCode，通常等于 appKey |
| `userIds` | string[] | ✅ | 用户 staffId（userId）列表，最多 20 个 |
| `msgKey` | string | ✅ | 消息类型 key（见下方消息类型表） |
| `msgParam` | string | ✅ | 消息参数 **JSON 字符串** |

返回示例：
```json
{
  "processQueryKey": "abc123",
  "invalidStaffIdList": [],
  "flowControlledStaffIdList": []
}
```

---

### 发送群聊消息

```
POST /v1.0/robot/groupMessages/send
Content-Type: application/json

{
  "robotCode": "<appKey>",
  "openConversationId": "<群 openConversationId>",
  "msgKey": "sampleText",
  "msgParam": "{\"content\": \"群通知：明天 10:00 开周会\"}"
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `robotCode` | string | ✅ | 机器人 robotCode |
| `openConversationId` | string | ✅ | 群会话 ID |
| `msgKey` | string | ✅ | 消息类型 key |
| `msgParam` | string | ✅ | 消息参数 JSON 字符串 |

返回：`{ "processQueryKey": "xxx" }`

---

### 查询单聊消息已读状态

```
GET /v1.0/robot/oToMessages/readStatus?robotCode=<appKey>&processQueryKey=<processQueryKey>
```

> **注意**：此接口为 **GET** 方法，参数通过 query string 传递，不是 POST body。

返回示例：
```json
{
  "messageReadInfoList": [
    {
      "name": "张三",
      "userId": "user001",
      "readStatus": "read",
      "readTimestamp": 1710000000000
    }
  ]
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `readStatus` | string | `read`（已读）或 `unread`（未读） |
| `readTimestamp` | long | 阅读时间戳（毫秒），未读时为 0 |

---

### 撤回单聊消息

```
POST /v1.0/robot/otoMessages/batchRecall
Content-Type: application/json

{
  "robotCode": "<appKey>",
  "processQueryKeys": ["<processQueryKey1>"]
}
```

返回示例：
```json
{
  "successResult": ["processQueryKey1"],
  "failedResult": {}
}
```

---

### 撤回群聊消息

```
POST /v1.0/robot/groupMessages/recall
Content-Type: application/json

{
  "robotCode": "<appKey>",
  "openConversationId": "<openConversationId>",
  "processQueryKeys": ["<processQueryKey>"]
}
```

返回示例：
```json
{
  "successResult": ["processQueryKey"],
  "failedResult": {}
}
```

---

### 消息类型（msgKey & msgParam）

| msgKey | 类型 | msgParam 示例 |
|---|---|---|
| `sampleText` | 文本 | `{"content": "消息内容"}` |
| `sampleMarkdown` | Markdown | `{"title": "标题", "text": "# 正文\n内容"}` |
| `sampleActionCard` | ActionCard（整体跳转） | `{"title": "标题", "text": "正文", "singleTitle": "按钮", "singleURL": "https://..."}` |
| `sampleActionCard2` | ActionCard（按钮竖排） | `{"title": "标题", "text": "正文", "actionTitle1": "按钮1", "actionURL1": "url1", "actionTitle2": "按钮2", "actionURL2": "url2"}` |
| `sampleActionCard3` | ActionCard（按钮横排） | 同上 |
| `sampleLink` | 链接 | `{"title": "标题", "text": "描述", "messageUrl": "url", "picUrl": "图片url"}` |
| `sampleImageMsg` | 图片 | `{"photoURL": "https://..."}` |
| `sampleAudio` | 语音 | `{"mediaId": "xxx", "duration": "3000"}` |

> `msgParam` 必须是 **JSON 字符串**，而非 JSON 对象。

---

## 三、工作通知

基础地址：`https://oapi.dingtalk.com`  
认证：查询参数 `access_token=<旧版 access_token>`（通过 `/gettoken` 获取）

---

### 发送工作通知

```
POST /topapi/message/corpconversation/asyncsend_v2?access_token=<token>
Content-Type: application/json

{
  "agent_id": "<agentId>",
  "userid_list": "user001,user002",
  "to_all_user": false,
  "msg": {
    "msgtype": "text",
    "text": { "content": "你的报销申请已审批通过" }
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `agent_id` | long | ✅ | 应用 agentId |
| `userid_list` | string | 条件 | 逗号分隔的 userId（最多 100 个），与 `dept_id_list` 二选一 |
| `dept_id_list` | string | 条件 | 逗号分隔的部门 ID |
| `to_all_user` | boolean | ❌ | 是否推送全员（true 时忽略 userid_list/dept_id_list）|
| `msg` | object | ✅ | 消息体 |

返回示例：
```json
{ "errcode": 0, "errmsg": "ok", "task_id": 123456 }
```

---

### 工作通知消息类型

**文本：**
```json
{ "msgtype": "text", "text": { "content": "消息内容" } }
```

**Markdown：**
```json
{ "msgtype": "markdown", "markdown": { "title": "标题", "text": "## 正文\n内容" } }
```

**ActionCard（整体跳转）：**
```json
{
  "msgtype": "action_card",
  "action_card": {
    "title": "标题",
    "markdown": "## 正文内容",
    "single_title": "查看详情",
    "single_url": "https://example.com"
  }
}
```

**ActionCard（多按钮）：**
```json
{
  "msgtype": "action_card",
  "action_card": {
    "title": "标题",
    "markdown": "## 正文内容",
    "btn_orientation": "0",
    "btn_json_list": [
      { "title": "同意", "action_url": "https://example.com/approve" },
      { "title": "拒绝", "action_url": "https://example.com/reject" }
    ]
  }
}
```

**OA 消息：**
```json
{
  "msgtype": "oa",
  "oa": {
    "message_url": "https://example.com/detail",
    "head": { "bgcolor": "FFBBBBBB", "text": "正文标题" },
    "body": {
      "title": "报销审批",
      "form": [
        { "key": "申请人", "value": "张三" },
        { "key": "金额", "value": "¥3,200" }
      ],
      "content": "请尽快处理"
    }
  }
}
```

---

### 查询工作通知发送结果

```
POST /topapi/message/corpconversation/getsendresult?access_token=<token>
Content-Type: application/json

{
  "agent_id": "<agentId>",
  "task_id": 123456
}
```

返回示例：
```json
{
  "errcode": 0,
  "send_result": {
    "invalid_user_id_list": [],
    "forbidden_user_id_list": [],
    "read_user_id_list": ["user001"],
    "unread_user_id_list": ["user002"],
    "failed_user_id_list": []
  }
}
```

---

### 撤回工作通知

```
POST /topapi/message/corpconversation/recall?access_token=<token>
Content-Type: application/json

{
  "agent_id": "<agentId>",
  "msg_task_id": 123456
}
```

返回：`{ "errcode": 0, "errmsg": "ok" }`

---

## 四、sessionWebhook（回调临时回复通道）

当机器人收到用户消息回调时，消息体中包含 `sessionWebhook` 字段。这是一个**临时 Webhook URL**，可直接 POST 回复消息，无需 accessToken。

### 回调消息体关键字段

```json
{
  "conversationId": "cidXXXXX==",
  "conversationType": "2",
  "senderStaffId": "25262904",
  "senderUnionId": "K1mxiiGFgkVfWYR5tNM04lAiEiE",
  "senderNick": "张三",
  "senderCorpId": "dingxxxxx",
  "robotCode": "dingxxxxxx",
  "text": { "content": " 用户发送的内容" },
  "msgtype": "text",
  "atUsers": [
    { "dingtalkId": "xxx", "staffId": "25262904", "unionId": "K1mxiiGFgkVfWYR5tNM04lAiEiE" }
  ],
  "sessionWebhook": "https://oapi.dingtalk.com/robot/sendBySession?session=xxxxx",
  "sessionWebhookExpiredTime": 1773216797267
}
```

| 字段 | 说明 |
|---|---|
| `conversationId` | 会话 ID，群聊时即 `openConversationId` |
| `conversationType` | `"1"` 单聊、`"2"` 群聊 |
| `senderStaffId` | 发送者的 userId（企业内部群始终存在；外部群中的外部用户可能为空） |
| `senderUnionId` | 发送者的 unionId（跨组织通用，始终存在） |
| `senderCorpId` | 发送者所在企业的 corpId |
| `atUsers[].staffId` | 被@用户的 userId（外部群中的外部用户此字段为空） |
| `atUsers[].unionId` | 被@用户的 unionId（始终存在） |
| `robotCode` | 机器人 robotCode（= appKey） |
| `sessionWebhook` | 临时回复 URL（约 1.5 小时有效） |
| `sessionWebhookExpiredTime` | 过期时间戳（毫秒） |

### 通过 sessionWebhook 回复

```
POST <sessionWebhook>
Content-Type: application/json

{
  "msgtype": "text",
  "text": { "content": "收到，正在处理..." }
}
```

支持所有 Webhook 消息格式（text/markdown/actionCard/link/feedCard），返回：

```json
{ "errcode": 0, "errmsg": "ok" }
```

> 无需加签、无需 accessToken，是机器人回复消息最简单的方式。

---

## 错误码

### Webhook 错误码

| errcode | 说明 | 处理建议 |
|---|---|---|
| `0` | 成功 | — |
| `310000` | `keywords not in content` | 消息内容须包含自定义关键词 |
| `310000` | `sign not match` | 检查签名计算或 timestamp 是否过期（±1h）|
| `310000` | `token is not exist` | Webhook URL 无效或已被删除 |
| `302033` | `send too fast` | 超过 20 条/分钟限制，等待后重试 |

### 机器人错误码

| 错误 | 说明 | 处理建议 |
|---|---|---|
| 401 | accessToken 过期 | 重新获取 |
| 403 | 权限不足 | 开通 `Robot.Message.Send` 等权限 |
| `invalidStaffIdList` 非空 | userId 无效 | 确认用户在组织内 |
| `flowControlledStaffIdList` 非空 | 被限流 | 稍候重试 |

### 工作通知错误码

| errcode | 说明 | 处理建议 |
|---|---|---|
| `0` | 成功 | — |
| `33` | access_token 过期 | 重新调用 `/gettoken` |
| `40035` | 参数不合法 | 检查 agent_id、userid_list 格式 |
| `88` | agent_id 不存在 | 确认应用 agentId |
| `90018` | userid_list 超过 100 | 分批发送 |

---

## 所需应用权限

| 功能 | 权限 |
|---|---|
| 机器人单聊消息 | `Robot.Message.Send` |
| 机器人群聊消息 | `Robot.GroupMessage.Send` |
| 消息已读查询 | `Robot.Message.Query` |
| 消息撤回 | `Robot.Message.Recall` |
| 工作通知发送 | `Message.CorpConversation.AsyncSend` |
| 工作通知撤回 | `Message.CorpConversation.Recall` |
| Webhook | 无需应用权限 |
| sessionWebhook | 无需应用权限（回调消息自带） |
