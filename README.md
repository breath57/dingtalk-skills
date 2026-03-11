# 钉钉 Agent 技能库（dingtalk-skills）

[English](README_EN.md) | 中文

---

让 AI Agent 直接操作钉钉——无需手写 API 调用，无需手动管理 Token，对话即操作。

基于 [Anthropic skills 规范](https://github.com/anthropics/skills) 构建，**仅依赖 `curl`**，无需安装 Python、SDK 或任何第三方库。安装一行命令，Agent 即可理解"什么时候该调钉钉 API、该调哪个、参数怎么填"，并**自动管理配置**、错误处理。

## 为什么用这个

- **对话即操作**："帮我在任务表里加三条记录" → Agent 自动完成，无需你知道任何 API
- **零依赖**：仅使用 `curl` 发起 HTTP 请求，无需安装 Python、SDK 或任何第三方库
- **一次配置，永久生效**：首次使用时 Agent 统一询问 appKey/appSecret/operatorId，写入 `~/.dingtalk-skills/config`，后续所有技能直接复用，不再重复问

## 技能列表

### ✅ 已上线

#### [dingtalk-document](.agents/skills/dingtalk-document/) — 钉钉知识库 & 文档

```bash
npx skills add breath57/dingtalk-skills@dingtalk-document
```

| 能力 | 说明 |
|---|---|
| 查询知识库列表 | 获取当前用户有权访问的全部知识库 |
| 查询知识库信息 | 按 workspaceId 获取知识库详情 |
| 浏览目录结构 | 列出知识库下的文档/文件夹节点树 |
| 查询节点信息 | 按 nodeId 或文档链接获取节点详情 |
| 创建文档/文件夹 | 在指定知识库/目录下新建文档或文件夹 |
| 读取文档内容 | 获取文档正文的 Block 结构（含标题、段落、列表、表格等） |
| 写入/覆盖文档内容 | 用 Block 结构替换文档正文 |
| 删除文档 | 从知识库中删除指定文档 |
| 成员权限管理 | 添加/移除文档协作成员及权限级别 |

> 示例："把这份会议纪要写入知识库'项目文档'下的'2026-03'文件夹" → Agent 自动查目录、建文档、写内容。

#### [dingtalk-ai-table](.agents/skills/dingtalk-ai-table/) — 钉钉 AI 表格

```bash
npx skills add breath57/dingtalk-skills@dingtalk-ai-table
```

| 能力 | 说明 |
|---|---|
| 列出工作表 | 获取 AI 表格内所有工作表及 ID |
| 查询/新建/删除工作表 | 管理 AI 表格内的工作表 |
| 列出字段 | 获取工作表全部字段名称与类型（text / number / date 等） |
| 新建/更新/删除字段 | 管理列定义 |
| 新增记录 | 批量向工作表插入数据行 |
| 查询记录列表 | 分页读取所有记录，支持翻页 |
| 更新记录 | 按 recordId 修改指定字段值 |
| 删除记录 | 按 recordId 批量删除数据行 |

> 示例："查一下任务表里状态是'进行中'的所有记录" → Agent 自动拉取字段定义、翻页读取、过滤返回。

#### [dingtalk-message](.agents/skills/dingtalk-message/) — 钉钉消息发送

```bash
npx skills add breath57/dingtalk-skills@dingtalk-message
```

| 能力 | 说明 |
|---|---|
| Webhook 机器人 - 文本 | 发送纯文本消息到群 |
| Webhook 机器人 - Markdown | 发送富格式 Markdown 通知到群 |
| Webhook 机器人 - ActionCard | 发送带按钮的交互卡片（单按钮/多按钮）|
| Webhook 机器人 - Link/FeedCard | 发送链接消息和多条聚合卡片 |
| Webhook 加签 | 支持加签安全模式（HMAC-SHA256）|
| 机器人单聊 | 通过企业内部应用机器人向指定用户发送消息 |
| 机器人群聊 | 通过机器人向指定群发送消息 |
| 消息撤回 | 撤回单聊/群聊机器人消息 |
| 消息已读查询 | 查询单聊消息的已读/未读状态 |
| 工作通知 | 通过应用向指定用户发送工作通知消息 |
| 工作通知查询/撤回 | 查询发送结果、撤回已发工作通知 |

> 示例："发群消息说今天 v2.1 上线了，Markdown 格式" → Agent 自动构造消息体并发送。

### 🗓️ 计划中

`dingtalk-contact` · `dingtalk-todo` · `dingtalk-approval` · `dingtalk-calendar` · `dingtalk-attendance` · `dingtalk-meeting`

## 快速开始

**第一步：安装技能**

```bash
npx skills add breath57/dingtalk-skills@dingtalk-document
npx skills add breath57/dingtalk-skills@dingtalk-ai-table
npx skills add breath57/dingtalk-skills@dingtalk-message
```

**第二步：开口说话**

Agent 会在首次运行时检查 `~/.dingtalk-skills/config`，缺什么一次性问清楚，自动写入。之后直接对话：

```
"查看我的钉钉知识库列表"
"往 AI 表格的'需求池'工作表添加一条记录：标题=登录优化，优先级=高"
"把'任务表'里所有'已完成'的记录删掉"
```

## 前置条件

1. 在[钉钉开放平台](https://open.dingtalk.com/)创建企业内部应用
2. 开通对应 API 权限（文档/Notable 相关权限）
3. 准备好 `appKey`、`appSecret`，以及操作人的钉钉 `userId`（Agent 会引导你完成配置）

## 项目结构

```
.agents/skills/
├── dingtalk-document/
│   ├── SKILL.md          # 技能主文件（触发条件 + 操作指令）
│   └── references/
│       └── api.md        # 钉钉 API 参考
├── dingtalk-ai-table/
│   ├── SKILL.md
│   └── references/
│       └── api.md
├── dingtalk-message/
│   ├── SKILL.md
│   └── references/
│       └── api.md
├── dingtalk-contact/
│   └── SKILL.md
└── dingtalk-todo/
    └── SKILL.md
```

## 贡献

欢迎 PR。每个技能存放在 `.agents/skills/<技能名>/` 目录下，遵循标准技能结构，参考 `AGENTS.md`。

## 许可证

MIT
