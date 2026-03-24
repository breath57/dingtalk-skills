---
name: dingtalk-calendar
description: 钉钉日程与日历。当用户提到"钉钉日程"、"日历"、"创建日程"、"新建会议"、"添加日程"、"查日程"、"日程列表"、"修改日程"、"删除日程"、"取消日程"、"闲忙"、"忙闲"、"querySchedule"、"calendar"、"dingtalk schedule"、"日程提醒"时使用此技能。支持：主日历下创建/查询/列表/更新/删除日程事件，以及按用户查询闲忙时间。
---

# 钉钉日程技能

负责钉钉日历（Calendar）API 的操作。本文件为**策略指南**；完整请求格式见 `references/api.md`。

> `dt_helper.sh` 位于本 `SKILL.md` 同级目录的 `scripts/dt_helper.sh`。

## 核心概念

- **路径中的 `userId`**：日程 API 路径 `/v1.0/calendar/users/{userId}/...` 中的 `{userId}` 为 **unionId**（与待办、文档一致），不是 staffId。
- **主日历**：个人默认日历的 `calendarId` 固定使用字符串 **`primary`**（小写）。创建/查询/列表/更新/删除均针对 `.../calendars/primary/events...`。
- **时间格式**：`start` / `end`、闲忙的 `startTime`/`endTime`、列表的 `timeMin`/`timeMax` 须使用 **UTC ISO8601 且含毫秒**，例如 `2026-03-24T07:02:48.000Z`。省略毫秒易触发 `ParsedISO8601TimestampError`。
- **修改日程**：HTTP 方法为 **PUT**（与「部分更新」语义对应的路径相同），请求体需包含日程 `id` 及要改的字段（如 `summary`）。

## 工作流程（每次执行前）

1. **识别任务** → 创建日程 / 查详情 / 列表 / 改标题时间 / 删日程 / 查闲忙。
2. **校验配置** → `bash scripts/dt_helper.sh --get` 读取 `DINGTALK_APP_KEY`、`DINGTALK_APP_SECRET`、`DINGTALK_MY_USER_ID`、`DINGTALK_MY_OPERATOR_ID`（缺 unionId 时 `--to-unionid`）。
3. **收集缺失项** → 一次性询问并 `--set` 写入 `~/.dingtalk-skills/config`。
4. **获取新版 Token** → `NEW_TOKEN=$(bash scripts/dt_helper.sh --token)`，请求头 `x-acs-dingtalk-access-token`。
5. **执行 API** → 多行逻辑写入 `/tmp/<task>.sh` 再执行；禁止 heredoc。

### 按任务校验配置

- **通用必需**：`DINGTALK_APP_KEY`、`DINGTALK_APP_SECRET`、`DINGTALK_MY_USER_ID`；调用前需 **unionId**（`DINGTALK_MY_OPERATOR_ID` 或通过 `--to-unionid` 生成）。

> 未通过校验前不得调用 API。凭证展示仅前 4 位 + `****`。

### 所需配置

| 配置键 | 必填 | 说明 |
|---|---|---|
| `DINGTALK_APP_KEY` | ✅ | Client ID（AppKey） |
| `DINGTALK_APP_SECRET` | ✅ | Client Secret |
| `DINGTALK_MY_USER_ID` | ✅ | 当前用户 userId（管理后台通讯录） |
| `DINGTALK_MY_OPERATOR_ID` | ✅ | 当前用户 unionId（`--to-unionid` 可写入） |

### 身份标识说明

| 标识 | 说明 |
|---|---|
| `userId` | 企业员工 ID，管理后台可见 |
| `unionId` | **日程路径参数与 body 中的用户标识均使用 unionId** |

userId → unionId：使用**旧版** `access_token` 调 `POST https://oapi.dingtalk.com/topapi/v2/user/get`（见 `references/api.md`），取 `result.unionid`（无下划线）。

### 执行脚本模板

```bash
#!/bin/bash
set -e
HELPER="./scripts/dt_helper.sh"
NEW_TOKEN=$(bash "$HELPER" --token)
UNION_ID=$(bash "$HELPER" --get DINGTALK_MY_OPERATOR_ID)
CAL_ID="primary"

curl -s -X POST "https://api.dingtalk.com/v1.0/calendar/users/${UNION_ID}/calendars/${CAL_ID}/events" \
  -H "x-acs-dingtalk-access-token: $NEW_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"summary":"周会","start":{"dateTime":"2026-03-25T02:00:00.000Z","timeZone":"UTC"},"end":{"dateTime":"2026-03-25T03:00:00.000Z","timeZone":"UTC"}}'
```

> Token 异常时：`bash "$HELPER" --token --nocache`

## references/api.md 查阅索引

```bash
grep -A 35 "^## 1. 创建日程" references/api.md
grep -A 25 "^## 2. 查询单个日程" references/api.md
grep -A 30 "^## 3. 查询日程列表" references/api.md
grep -A 25 "^## 4. 更新日程" references/api.md
grep -A 15 "^## 5. 删除日程" references/api.md
grep -A 28 "^## 6. 查询闲忙" references/api.md
grep -A 15 "^## 错误码" references/api.md
grep -A 12 "^## 所需应用权限" references/api.md
```
