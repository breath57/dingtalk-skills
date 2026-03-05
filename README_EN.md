# dingtalk-skills

中文 | [English](README_EN.md)

---

A collection of [agent skills](https://github.com/anthropics/skills) for DingTalk, enabling AI agents to interact with DingTalk APIs directly — creating documents, reading spreadsheet data, managing approvals, and more.

## Skills

### ✅ Available

| Skill | Description | Install |
|---|---|---|
| [dingtalk-document](.agents/skills/dingtalk-document/) | Knowledge base & document management | `npx skills add breath57/dingtalk-skills@dingtalk-document` |
| [dingtalk-ai-table](.agents/skills/dingtalk-ai-table/) | Spreadsheet read/write, row/column management | `npx skills add breath57/dingtalk-skills@dingtalk-ai-table` |

### 🗓️ TODO

`dingtalk-auth` · `dingtalk-message` · `dingtalk-contacts` · `dingtalk-approval` · `dingtalk-calendar` · `dingtalk-todo` · `dingtalk-attendance` · `dingtalk-meeting` · `dingtalk-ai-agent`

## Prerequisites

1. DingTalk enterprise internal app with relevant API permissions
2. `appKey` and `appSecret` from [DingTalk Open Platform](https://open.dingtalk.com/)

## License

MIT
