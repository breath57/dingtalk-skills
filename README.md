# 钉钉 Agent 技能库（dingtalk-skills）

[English](README_EN.md) | 中文

---

面向 AI Agent 的钉钉开放能力技能集合，基于 [Anthropic skills 规范](https://github.com/anthropics/skills) 实现。

安装技能后，AI Agent 即可自主理解何时、如何调用钉钉 API，完成文档创建、表格读写、审批发起、消息发送等操作。

## 技能列表

### ✅ 已上线

| 技能 | 功能描述 | 安装命令 |
|---|---|---|
| [dingtalk-document](.agents/skills/dingtalk-document/) | 钉钉知识库 & 文档管理 — 创建/查询知识库、新建文档、管理成员权限 | `npx skills add breath57/dingtalk-skills@dingtalk-document` |
| [dingtalk-ai-table](.agents/skills/dingtalk-ai-table/) | 钉钉 AI 表格 — 读写单元格数据、管理工作表、插入/删除行列 | `npx skills add breath57/dingtalk-skills@dingtalk-ai-table` |

### 🗓️ 计划中

| 技能 | 功能描述 |
|---|---|
| `dingtalk-auth` | 获取企业内部应用 access_token |
| `dingtalk-message` | 发送工作通知 / 机器人消息 / 互动卡片 |
| `dingtalk-contacts` | 查询用户、部门、角色信息 |
| `dingtalk-approval` | OA 审批发起、查询、处理 |
| `dingtalk-calendar` | 日程创建、查询、忙闲查询 |
| `dingtalk-todo` | 待办任务创建与管理 |
| `dingtalk-attendance` | 考勤打卡结果、排班、假期余额 |
| `dingtalk-meeting` | 创建 / 查询视频会议 |
| `dingtalk-ai-agent` | 钉钉 AI 助理消息发送与更新 |

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
- "读取这个钉钉表格 A1:C10 的数据"

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
