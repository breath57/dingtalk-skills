# dingtalk-skills

中文 | [English](README_EN.md)

---

Let your AI Agent operate DingTalk directly — no manual API calls, no token management, just conversation.

Built on the [Anthropic skills spec](https://github.com/anthropics/skills). Install with one command and your agent automatically understands when to call DingTalk APIs, which endpoint to use, and how to fill in the parameters — including auth, config persistence, and error handling.

## Why use this

- **Talk, don't code**: "Add three records to the task table" → Agent handles it end-to-end, no API knowledge required
- **Configure once, use everywhere**: On first run, the agent collects appKey/appSecret/operatorId in a single prompt, saves to `~/.dingtalk-skills/config`, and reuses across all skills automatically
- **Production-ready from day one**: Full CRUD coverage for DingTalk's most-used document and table APIs, with live tests verifying every endpoint

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

> Example: "Write this meeting summary into the '2026-03' folder under the 'Project Docs' workspace" → Agent finds the directory, creates the document, and writes the content.

#### [dingtalk-ai-table](.agents/skills/dingtalk-ai-table/) — AI Table (Notable)

```bash
npx skills add breath57/dingtalk-skills@dingtalk-ai-table
```

| Capability | Description |
|---|---|
| List sheets | Get all sheets and IDs in an AI table |
| Get / create / delete sheet | Manage sheets within an AI table |
| List fields | Get all field names and types (text / number / date, etc.) |
| Create / update / delete field | Manage column definitions |
| Insert records | Batch-insert data rows into a sheet |
| List records | Paginated read of all records |
| Update record | Modify specific field values by recordId |
| Delete records | Batch-delete rows by recordId |

> Example: "Show me all records in the task sheet where status is 'In Progress'" → Agent fetches field definitions, paginates through all records, and filters the results.

### 🗓️ Planned

`dingtalk-message` · `dingtalk-approval` · `dingtalk-contacts` · `dingtalk-calendar` · `dingtalk-todo` · `dingtalk-attendance` · `dingtalk-meeting`

## Quick Start

**Step 1: Install skills**

```bash
npx skills add breath57/dingtalk-skills@dingtalk-document
npx skills add breath57/dingtalk-skills@dingtalk-ai-table
```

**Step 2: Just talk**

On first run, the agent checks `~/.dingtalk-skills/config`, asks for anything missing in one go, and saves it. Then:

```
"List my DingTalk knowledge bases"
"Add a record to the 'Backlog' sheet: title=Login fix, priority=High"
"Delete all records marked 'Done' from the task table"
```

## Prerequisites

1. A DingTalk enterprise internal app on [DingTalk Open Platform](https://open.dingtalk.com/)
2. Relevant API permissions enabled (Docs / Notable)
3. Your `appKey`, `appSecret`, and DingTalk `userId` — the agent will walk you through the setup

## License

MIT
