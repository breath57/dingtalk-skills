# 钉钉 Agent 技能库（dingtalk-skills）

[English](README_EN.md) | 中文

---

面向 AI Agent 的钉钉开放能力技能集合，基于 [Anthropic skills 规范](https://github.com/anthropics/skills) 实现。

安装技能后，AI Agent 即可自主理解何时、如何调用钉钉 API，完成文档创建、表格读写、审批发起、消息发送等操作。

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

#### [dingtalk-ai-table](.agents/skills/dingtalk-ai-table/) — 钉钉 AI 表格

```bash
npx skills add breath57/dingtalk-skills@dingtalk-ai-table
```

| 能力 | 说明 |
|---|---|
| 列出工作表 | 获取 AI 表格内所有工作表 |
| 查询/新建/删除工作表 | 管理 AI 表格内的工作表 |
| 列出字段 | 获取工作表全部字段及类型（text / number / date 等） |
| 新建/更新/删除字段 | 管理列定义 |
| 新增记录 | 批量向工作表插入数据行 |
| 查询记录列表 | 分页读取所有记录，支持翻页 |
| 更新记录 | 按 recordId 修改指定字段值 |
| 删除记录 | 按 recordId 批量删除数据行 |

### 🗓️ 计划中

`dingtalk-auth` · `dingtalk-message` · `dingtalk-contacts` · `dingtalk-approval` · `dingtalk-calendar` · `dingtalk-todo` · `dingtalk-attendance` · `dingtalk-meeting` · `dingtalk-ai-agent`

## 配置管理

所有技能共享统一的配置文件 `~/.dingtalk-skills/config`（纯键值对格式）：

```
DINGTALK_APP_KEY=dingXXXXXX
DINGTALK_APP_SECRET=XXXXXX
DINGTALK_OPERATOR_ID=XXXXXX
```

**首次使用时**，Agent 会检查配置文件，若缺少所需配置项，则一次性询问用户并自动写入，后续无需重复提供。不同技能各自读取自己需要的键，通用配置（appKey、appSecret、operatorId）只需填写一次对所有技能生效。

## 前置条件

1. 在[钉钉开放平台](https://open.dingtalk.com/)创建企业内部应用，并开通对应 API 权限
2. 准备好应用的 `appKey` 和 `appSecret`

## 快速开始

```bash
# 安装钉钉文档技能
npx skills add breath57/dingtalk-skills@dingtalk-document

# 安装钉钉 AI 表格技能
npx skills add breath57/dingtalk-skills@dingtalk-ai-table
```

安装后直接对 AI Agent 说话即可，例如：
- "帮我在钉钉知识库里新建一个文档"
- "查看这个 AI 表格里有哪些工作表"
- "往任务表里添加三条记录"

## 项目结构

```
.agents/skills/
├── dingtalk-document/
│   ├── SKILL.md          # 技能主文件（触发条件 + 操作指令）
│   └── references/
│       └── api.md        # 钉钉 API 参考文档
└── dingtalk-ai-table/
    ├── SKILL.md
    └── references/
        └── api.md
```

## 贡献

欢迎 PR。每个技能存放在 `.agents/skills/<技能名>/` 目录下，遵循标准技能结构。

## 许可证

MIT
