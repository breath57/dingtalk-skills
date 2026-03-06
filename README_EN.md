# dingtalk-skills

中文 | [English](README_EN.md)

---

A collection of [agent skills](https://github.com/anthropics/skills) for DingTalk, enabling AI agents to interact with DingTalk APIs directly — creating documents, reading table data, managing approvals, sending messages, and more.

## Skills

### ✅ Available

#### [dingtalk-document](.agents/skills/dingtalk-document/) — Knowledge Base & Documents

```bash
npx skills add breath57/dingtalk-skills@dingtalk-document
```

| Capability | Description |
|---|---|
| List workspaces | Get all knowledge bases the user can access |
| Get workspace info | Fetch workspace details by workspaceId |
| Browse directory | List document/folder nodes under a workspace |
| Get node info | Fetch node details by nodeId or document URL |
| Create document/folder | Create a new document or folder in a workspace |
| Read document content | Get document body as Block structure (headings, paragraphs, lists, tables, etc.) |
| Write document content | Replace document body with Block structure |
| Delete document | Remove a document from a workspace |
| Manage members | Add/remove collaborators and set permission levels |

#### [dingtalk-ai-table](.agents/skills/dingtalk-ai-table/) — AI Table (Notable)

```bash
npx skills add breath57/dingtalk-skills@dingtalk-ai-table
```

| Capability | Description |
|---|---|
| List sheets | Get all sheets in an AI table |
| Get / create / delete sheet | Manage sheets within an AI table |
| List fields | Get all field definitions and types (text / number / date, etc.) |
| Create / update / delete field | Manage column definitions |
| Insert records | Batch-insert data rows into a sheet |
| List records | Paginated read of all records |
| Update record | Modify specific field values by recordId |
| Delete records | Batch-delete rows by recordId |

### 🗓️ Planned

`dingtalk-auth` · `dingtalk-message` · `dingtalk-contacts` · `dingtalk-approval` · `dingtalk-calendar` · `dingtalk-todo` · `dingtalk-attendance` · `dingtalk-meeting` · `dingtalk-ai-agent`

## Configuration Management

All skills share a single config file at `~/.dingtalk-skills/config` (plain key=value format):

```
DINGTALK_APP_KEY=dingXXXXXX
DINGTALK_APP_SECRET=XXXXXX
DINGTALK_OPERATOR_ID=XXXXXX
```

**On first use**, the agent checks the config file, asks for any missing values in a single prompt, and writes them automatically. Common credentials (appKey, appSecret, operatorId) only need to be entered once and apply to all skills.

## Prerequisites

1. DingTalk enterprise internal app with relevant API permissions
2. `appKey` and `appSecret` from [DingTalk Open Platform](https://open.dingtalk.com/)

## License

MIT
