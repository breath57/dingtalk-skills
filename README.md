# 钉钉 Agent 技能库（dingtalk-skills）

[English](README_EN.md) | 中文

---

**已适配 [OpenClaw](https://openclaw.ai) 🦞**，可从 [ClawHub](https://clawhub.ai) · [Skills.sh](https://skills.sh/breath57/dingtalk-skills) 一键安装。

让 AI Agent 直接操作钉钉——无需手写 API 调用，无需手动管理 Token，对话即操作。

基于 [Anthropic skills 规范](https://github.com/anthropics/skills) 构建，**仅依赖 `curl`**，无需安装 Python、SDK 或任何第三方库。安装一行命令，Agent 即可理解"什么时候该调钉钉 API、该调哪个、参数怎么填"，并**自动管理配置**、错误处理。

## 为什么用这个

- **对话即操作**："帮我在任务表里加三条记录" → Agent 自动完成，无需你知道任何 API
- **零依赖**：仅使用 `curl` 发起 HTTP 请求，无需安装 Python、SDK 或任何第三方库
- **一次配置，永久生效**：首次使用时 Agent 统一询问 appKey/appSecret/operatorId，写入 `~/.dingtalk-skills/config`，后续所有技能直接复用，不再重复问

## 长期目标

本项目有两条并行的长期主线：

**1. 永远只依赖 `curl`**
不引入任何 SDK、运行时或第三方库。只要系统有 `curl`，技能就能运行。这保证了最大的可移植性，也让技能在任何 Agent 环境中都能免安装直接使用。

**2. 将每次调用消耗的 Token 压到极限**
Agent 每次执行任务都需要将技能文件装入上下文，**skill 文件本身就是成本**。我们的目标不只是「能用」，而是在保证正确率的前提下，把 `SKILL.md` 和 `references/api.md` 写得尽可能精炼——删掉所有冗余解释，用最短的指令表达最完整的语义。每一个字都要赚回自己的位置。

## 技能纵览

| 技能 | 状态 | 说明 | 已上架平台 |
|---|---|---|---|
| [dingtalk-document](#dingtalk-document--钉钉知识库--文档) | ✅ 已上线 | 知识库与文档的创建、查询、目录浏览、内容读写、成员管理 | [🦞 ClawHub](https://clawhub.ai/breath57/dingtalk-document) · [<img src="https://avatars.githubusercontent.com/u/108547162?s=200&v=4" height="16"> Skills.sh](https://skills.sh/breath57/dingtalk-skills/dingtalk-document) |
| [dingtalk-ai-table](#dingtalk-ai-table--钉钉-ai-表格) | ✅ 已上线 | AI 表格的工作表管理、字段管理、记录增删改查 | [🦞 ClawHub](https://clawhub.ai/breath57/dingtalk-ai-table) · [<img src="https://avatars.githubusercontent.com/u/108547162?s=200&v=4" height="16"> Skills.sh](https://skills.sh/breath57/dingtalk-skills/dingtalk-ai-table) |
| [dingtalk-message](#dingtalk-message--钉钉消息发送) | ✅ 已上线 | 消息发送：Webhook 机器人、单聊/群聊、工作通知 | [🦞 ClawHub](https://clawhub.ai/breath57/dingtalk-message) · [<img src="https://avatars.githubusercontent.com/u/108547162?s=200&v=4" height="16"> Skills.sh](https://skills.sh/breath57/dingtalk-skills/dingtalk-message) |
| [dingtalk-todo](#dingtalk-todo--钉钉待办) | ✅ 已上线 | 待办管理：创建、查询、更新、完成、删除 | [🦞 ClawHub](https://clawhub.ai/breath57/dingtalk-todo) · [<img src="https://avatars.githubusercontent.com/u/108547162?s=200&v=4" height="16"> Skills.sh](https://skills.sh/breath57/dingtalk-skills/dingtalk-todo) |
| [dingtalk-contact](#dingtalk-contact--钉钉通讯录) | ✅ 已上线 | 通讯录：搜索用户/部门、用户详情、部门树、成员列表 | [🦞 ClawHub](https://clawhub.ai/breath57/dingtalk-contact) · [<img src="https://avatars.githubusercontent.com/u/108547162?s=200&v=4" height="16"> Skills.sh](https://skills.sh/breath57/dingtalk-skills/dingtalk-contact) |
| [dingtalk-ai-web-search](#dingtalk-ai-web-search--网页搜索) | ✅ 已上线 | 网页搜索：关键词搜索、时间过滤、JSON 输出 | [🦞 ClawHub](https://clawhub.ai/breath57/dingtalk-ai-web-search) · [<img src="https://avatars.githubusercontent.com/u/108547162?s=200&v=4" height="16"> Skills.sh](https://skills.sh/breath57/dingtalk-skills/dingtalk-ai-web-search) |
| [dingtalk-calendar](#dingtalk-calendar--钉钉日程) | ✅ 已上线 | 日程：CRUD、闲忙、视频会议、会议室、签到签退 | [🦞 ClawHub](https://clawhub.ai/breath57/dingtalk-calendar) · [<img src="https://avatars.githubusercontent.com/u/108547162?s=200&v=4" height="16"> Skills.sh](https://skills.sh/breath57/dingtalk-skills/dingtalk-calendar) |
| dingtalk-approval | 🗓️ 计划中 | 审批流程管理 | — |
| dingtalk-attendance | 🗓️ 计划中 | 考勤打卡管理 | — |
| dingtalk-meeting | 🗓️ 计划中 | 视频会议管理 | — |

## 快速开始

### 前置条件

1. 在[钉钉开放平台](https://open.dingtalk.com/)创建企业内部应用
2. 开通对应 API 权限（知识库 / AI 表格 / 机器人消息 / 待办 等）
3. 准备好 `appKey`、`appSecret`，以及操作人的钉钉 `userId`（Agent 会引导你完成配置）

### 安装技能

每个技能支持两种安装方式：

**1. ClawHub**
```bash
clawhub install breath57/dingtalk-document
```

**2. skills.sh**（全通用方式，支持 Cursor、Claude、Copilot、🦞 OpenClaw 等几乎所有 Agent）
```bash
npx skills add breath57/dingtalk-skills@dingtalk-document
```

**一键安装全部**（排除开发者专用技能）：
```bash
npx skills add breath57/dingtalk-skills \
  -s 'dingtalk-document,dingtalk-ai-table,dingtalk-message,dingtalk-todo,dingtalk-contact,dingtalk-ai-web-search,dingtalk-calendar' \
  -y
```

> `dingtalk-skill-creator` 和 `skill-creator` 为开发者工具，不在批量安装范围内。

### 开口说话

安装后，Agent 会在首次运行时检查 `~/.dingtalk-skills/config`，缺什么一次性问清楚，自动写入。之后直接对话：

```
"查看我的钉钉知识库列表"
"往 AI 表格的'需求池'工作表添加一条记录：标题=登录优化，优先级=高"
"发群消息说明天上午十点开周会，Markdown 格式"
"帮我建一个待办：下周五前完成竞品分析报告"
```

---

## 技能详情

### dingtalk-document — 钉钉知识库 & 文档

🦞 [ClawHub · dingtalk-document](https://clawhub.ai/breath57/dingtalk-document)

**安装**
```bash
# 1. ClawHub
clawhub install breath57/dingtalk-document

# 2. skills.sh（全通用方式，支持 Cursor / Claude / Copilot / 🦞 OpenClaw 等几乎所有 Agent）
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

---

### dingtalk-ai-table — 钉钉 AI 表格

🦞 [ClawHub · dingtalk-ai-table](https://clawhub.ai/breath57/dingtalk-ai-table)

**安装**
```bash
# 1. ClawHub
clawhub install breath57/dingtalk-ai-table

# 2. skills.sh（全通用方式，支持 Cursor / Claude / Copilot / 🦞 OpenClaw 等几乎所有 Agent）
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

---

### dingtalk-message — 钉钉消息发送

🦞 [ClawHub · dingtalk-message](https://clawhub.ai/breath57/dingtalk-message)

**安装**
```bash
# 1. ClawHub
clawhub install breath57/dingtalk-message

# 2. skills.sh（全通用方式，支持 Cursor / Claude / Copilot / 🦞 OpenClaw 等几乎所有 Agent）
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

---

### dingtalk-todo — 钉钉待办

🦞 [ClawHub · dingtalk-todo](https://clawhub.ai/breath57/dingtalk-todo)

**安装**
```bash
# 1. ClawHub
clawhub install breath57/dingtalk-todo

# 2. skills.sh（全通用方式，支持 Cursor / Claude / Copilot / 🦞 OpenClaw 等几乎所有 Agent）
npx skills add breath57/dingtalk-skills@dingtalk-todo
```

| 能力 | 说明 |
|---|---|
| 创建待办 | 新建待办任务，支持标题、描述、截止时间、优先级 |
| 查询待办详情 | 按 taskId 获取任务详情 |
| 列出待办/已完成 | 分页获取用户的未完成或已完成任务列表 |
| 更新待办 | 修改标题、描述、截止时间、优先级等 |
| 标记完成/撤销 | 将任务标记为已完成或重新打开 |
| 删除待办 | 删除指定待办任务 |

> 示例："帮我新建一个待办：下周五前完成竞品分析" → Agent 自动设置截止时间并创建任务。

---

### dingtalk-contact — 钉钉通讯录

🦞 [ClawHub · dingtalk-contact](https://clawhub.ai/breath57/dingtalk-contact)

**安装**
```bash
# 1. ClawHub
clawhub install breath57/dingtalk-contact

# 2. skills.sh（全通用方式，支持 Cursor / Claude / Copilot / 🦞 OpenClaw 等几乎所有 Agent）
npx skills add breath57/dingtalk-skills@dingtalk-contact
```

| 能力 | 说明 |
|---|---|
| 按关键词搜索用户 | 按姓名/工号等关键词搜索，返回 userId 列表 |
| 获取用户完整详情 | 姓名/手机/工号/职位/部门/unionId 等全字段 |
| unionId → userId 转换 | 通过 unionId 查询对应的 userId |
| 获取部门成员完整列表 | 按部门分页拉取全体成员详情 |
| 获取部门成员 userId 列表 | 轻量版，仅返回 userId 列表 |
| 按关键词搜索部门 | 按名称关键词搜索部门，返回 deptId 列表 |
| 获取子部门列表 | 获取指定部门的直接子部门（含详情） |
| 获取部门详情 | 名称/父部门/成员数/排序等完整信息 |
| 获取用户部门路径 | 从叶部门到根的完整 deptId 路径 |
| 企业员工总人数 | 统计全部/激活员工总数 |

> 示例："查一下张三的手机号和所在部门" → Agent 搜索用户、获取详情并返回。

---

### dingtalk-ai-web-search — 网页搜索

🦞 [ClawHub · dingtalk-ai-web-search](https://clawhub.ai/breath57/dingtalk-ai-web-search)

**安装**
```bash
# 1. ClawHub
clawhub install breath57/dingtalk-ai-web-search

# 2. skills.sh（全通用方式，支持 Cursor / Claude / Copilot / 🦞 OpenClaw 等几乎所有 Agent）
npx skills add breath57/dingtalk-skills@dingtalk-ai-web-search
```

| 能力 | 说明 |
|---|---|
| 关键词搜索 | 搜索互联网公开信息，返回标题、链接、摘要 |
| 时间范围过滤 | 限定搜索时间：一天/一周/一月/一年 |
| 自定义结果数量 | 指定返回条数（默认 5 条） |
| JSON 输出 | 结构化输出，便于程序后续处理 |

> 示例："帮我搜一下 Python asyncio 最佳实践" → Agent 自动搜索并返回最新结果摘要。

---

### dingtalk-calendar — 钉钉日程

🦞 [ClawHub · dingtalk-calendar](https://clawhub.ai/breath57/dingtalk-calendar)

**安装**
```bash
# 1. ClawHub
clawhub install breath57/dingtalk-calendar

# 2. skills.sh（全通用方式，支持 Cursor / Claude / Copilot / 🦞 OpenClaw 等几乎所有 Agent）
npx skills add breath57/dingtalk-skills@dingtalk-calendar
```

| 能力 | 说明 |
|---|---|
| 创建/更新/删除日程 | 主日历 `primary` 下创建会议、修改标题与时间、删除事件 |
| 查询日程详情与列表 | 按事件 ID 查询；按时间窗分页列出日程 |
| 查询闲忙 | 对指定 unionId 列表查询忙闲（querySchedule） |
| 视频会议 / 会议室 | 钉钉视频会议；会议室忙闲查询；日程上添加会议室（需 roomId） |
| 签到 / 签退 | 获取签到与签退链接；API 签到、签退（见 api.md） |
| 循环日程 | 创建时带 `recurrence`；订阅日历需额外权限 |

> 示例："明天下午三点加一小时日程，标题写评审" → Agent 按 UTC ISO8601 构造并创建。

---

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
├── dingtalk-todo/
│   ├── SKILL.md
│   └── references/
│       └── api.md
├── dingtalk-contact/
│   ├── SKILL.md
│   └── references/
│       └── api.md
├── dingtalk-ai-web-search/
│   ├── SKILL.md
│   └── scripts/
│       └── search.sh
├── dingtalk-calendar/
│   ├── SKILL.md
│   ├── scripts/
│   │   └── dt_helper.sh
│   └── references/
│       └── api.md
└── dingtalk-skill-creator/
    └── SKILL.md
```

## 贡献

欢迎 PR。每个技能存放在 `.agents/skills/<技能名>/` 目录下，遵循标准技能结构，参考 `AGENTS.md`。

## 许可证

MIT
