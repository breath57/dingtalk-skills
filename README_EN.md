# dingtalk-skills 

中文 | [English](README_EN.md)

---

**Adapted for [OpenClaw](https://openclaw.ai) 🦞** — install from [ClawHub](https://clawhub.ai) with one click.

Let your AI Agent operate DingTalk directly — no manual API calls, no token management, just conversation.

Built on the [Anthropic skills spec](https://github.com/anthropics/skills), with **zero dependencies — only `curl`** for HTTP requests, no Python, no SDK, nothing extra to install. Install with one command and your agent automatically understands when to call DingTalk APIs, which endpoint to use, and how to fill in the parameters — including **automatic config management**, and error handling.

## Why use this

- **Talk, don't code**: "Add three records to the task table" → Agent handles it end-to-end, no API knowledge required
- **Zero dependencies**: Only `curl` for HTTP requests — no Python, no SDK, no extra languages to install
- **Configure once, use everywhere**: On first run, the agent collects appKey/appSecret/operatorId in a single prompt, saves to `~/.dingtalk-skills/config`, and reuses across all skills automatically
- **Production-ready from day one**: Full CRUD coverage for DingTalk's most-used document and table APIs, with live tests verifying every endpoint

## Long-term Goals

This project pursues two parallel long-term objectives:

**1. Always only `curl`**
No SDKs, no runtimes, no third-party dependencies — ever. If the system has `curl`, the skill runs. This guarantees maximum portability and zero-install operation in any agent environment.

**2. Push token cost to the absolute minimum**
Every task execution loads skill files into the agent's context window — **the skill file itself is a cost**. Our goal isn't just correctness; it's writing `SKILL.md` and `references/api.md` as concisely as possible while maintaining full accuracy. Strip every redundant explanation. Express complete semantics with the shortest possible instructions. Every token must earn its place.

## Skills

### ✅ Available

#### [dingtalk-document](.agents/skills/dingtalk-document/) — Knowledge Base & Documents

🦞 [ClawHub · dingtalk-document](https://clawhub.ai/breath57/dingtalk-document)

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

🦞 [ClawHub · dingtalk-ai-table](https://clawhub.ai/breath57/dingtalk-ai-table-only-curl)

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

#### [dingtalk-message](.agents/skills/dingtalk-message/) — Message Sending

🦞 [ClawHub · dingtalk-message](https://clawhub.ai/breath57/dingtalk-message)

```bash
npx skills add breath57/dingtalk-skills@dingtalk-message
```

| Capability | Description |
|---|---|
| Webhook robot - text | Send plain text messages to a group |
| Webhook robot - Markdown | Send rich Markdown notifications to a group |
| Webhook robot - ActionCard | Send interactive cards with buttons (single/multi) |
| Webhook robot - Link/FeedCard | Send link messages and aggregated feed cards |
| Webhook signing | Support HMAC-SHA256 signature security mode |
| Robot single chat | Send messages to specific users via internal app robot |
| Robot group chat | Send messages to groups via robot |
| Message recall | Recall single-chat / group-chat robot messages |
| Read status query | Query read/unread status of single-chat messages |
| Work notification | Send work notifications to specific users via app |
| Work notification query/recall | Query send results and recall sent notifications |

> Example: "Send a group message saying v2.1 is live today, use Markdown" → Agent constructs the message body and sends it.

#### [dingtalk-todo](.agents/skills/dingtalk-todo/) — DingTalk Todo

🦞 [ClawHub · dingtalk-todo](https://clawhub.ai/breath57/dingtalk-todo)

```bash
npx skills add breath57/dingtalk-skills@dingtalk-todo
```

| Capability | Description |
|---|---|
| Create todo | Create a task with title, description, due date, and priority |
| Get todo detail | Fetch task details by taskId |
| List todos / completed | Paginated list of undone or completed tasks |
| Update todo | Modify title, description, due date, priority, etc. |
| Mark done / reopen | Mark a task as complete or reopen it |
| Delete todo | Remove a specific todo task |

> Example: "Create a todo: finish competitive analysis by next Friday" → Agent auto-sets the due date and creates the task.

#### [dingtalk-contact](.agents/skills/dingtalk-contact/) — DingTalk Directory

🦞 [ClawHub · dingtalk-contact](https://clawhub.ai/breath57/dingtalk-contact)

```bash
npx skills add breath57/dingtalk-skills@dingtalk-contact
```

| Capability | Description |
|---|---|
| Search users by keyword | Search by name/job number, returns userId list |
| Get full user details | Name, mobile, job number, title, department, unionId, etc. |
| unionId → userId lookup | Resolve userId from a given unionId |
| List department members | Paginated full member details for a department |
| List member userId list | Lightweight version — userId list only |
| Search departments by keyword | Search by name, returns deptId list |
| List sub-departments | Direct child departments with details |
| Get department details | Name, parent dept, member count, order, etc. |
| Get user's department path | Full deptId chain from leaf to root |
| Total employee count | Count all or active employees in the org |

> Example: "Find Zhang San's mobile number and department" → Agent searches the user, fetches details, and returns the info.

### 🗓️ Planned

`dingtalk-approval` · `dingtalk-calendar` · `dingtalk-attendance` · `dingtalk-meeting`

## Quick Start

**Step 1: Install skills**

```bash
npx skills add breath57/dingtalk-skills@dingtalk-document
npx skills add breath57/dingtalk-skills@dingtalk-ai-table
npx skills add breath57/dingtalk-skills@dingtalk-message
npx skills add breath57/dingtalk-skills@dingtalk-todo
npx skills add breath57/dingtalk-skills@dingtalk-contact
```

**Step 2: Just talk**

On first run, the agent checks `~/.dingtalk-skills/config`, asks for anything missing in one go, and saves it. Then:

```
"List my DingTalk knowledge bases"
"Add a record to the 'Backlog' sheet: title=Login fix, priority=High"
"Send a group message saying v2.1 is live, use Markdown format"
"Create a todo: finish competitive analysis by next Friday"
```

## Prerequisites

1. A DingTalk enterprise internal app on [DingTalk Open Platform](https://open.dingtalk.com/)
2. Relevant API permissions enabled (Knowledge Base / AI Table / Robot Message / Todo, etc.)
3. Your `appKey`, `appSecret`, and DingTalk `userId` — the agent will walk you through the setup

## License

MIT
