---
name: dingtalk-calendar
description: 钉钉日程与日历。当用户提到"钉钉日程"、"日历"、"创建日程"、"新建会议"、"视频会议"、"钉钉会议"、"会议室"、"约会议室"、"会议室忙闲"、"空闲会议室"、"签到"、"签退"、"签到链接"、"签退链接"、"循环日程"、"重复日程"、"recurrence"、"查日程"、"日程列表"、"修改日程"、"删除日程"、"闲忙"、"忙闲"、"querySchedule"、"calendar"、"dingtalk schedule"、"日程提醒"时使用此技能。支持：主日历下日程 CRUD、用户闲忙、视频会议、会议室忙闲与绑定日程、签到/签退与链接、循环规则（recurrence）；订阅公共日历等需 Calendar.Calendar.Write 的能力见 api.md。
---

# 钉钉日程技能

负责钉钉日历（Calendar）API 的操作。本文件为**策略指南**；完整请求格式见 `references/api.md`。

> `dt_helper.sh` 位于本 `SKILL.md` 同级目录的 `scripts/dt_helper.sh`。

## 核心概念

- **路径中的 `userId`**：日程 API 路径 `/v1.0/calendar/users/{userId}/...` 中的 `{userId}` 为 **unionId**（与待办、文档一致），不是 staffId。
- **主日历**：个人默认日历的 `calendarId` 固定使用字符串 **`primary`**（小写）。创建/查询/列表/更新/删除均针对 `.../calendars/primary/events...`。
- **时间格式**：`start` / `end`、闲忙的 `startTime`/`endTime`、列表的 `timeMin`/`timeMax` 须使用 **UTC ISO8601 且含毫秒**，例如 `2026-03-24T07:02:48.000Z`。省略毫秒易触发 `ParsedISO8601TimestampError`。
- **修改日程**：HTTP 方法为 **PUT**（与「部分更新」语义对应的路径相同），请求体需包含日程 `id` 及要改的字段（如 `summary`）。
- **视频会议**：创建日程时在请求体中加 `"onlineMeetingInfo":{"type":"dingtalk"}`，响应含 `onlineMeetingInfo.url` 等。
- **会议室**：先通过 **会议室忙闲** 接口按 `roomIds` + 时间窗查询；再在已有日程上 **添加会议室**（需企业内会议室 `roomId`，管理后台或开放平台可查）。集成测试可用环境变量 `TEST_MEETING_ROOM_IDS`（逗号分隔）。
- **签到/签退**：日程创建后，可 **GET 签到/签退链接** 分发参会人；组织者/参与者 **POST 签到**；详情用 **GET signin / signOut** 列表接口（见 api.md）。是否与线下会议、审批流联动以钉钉侧能力为准。

## 场景路由（先分类再调 API）

| 用户意图 | 优先接口方向 |
|---|---|
| 订会议室、查会议室有没有空 | `POST .../meetingRooms/schedules/query` |
| 给已有日程加会议室 | `POST .../events/{eventId}/meetingRooms` |
| 要签到码、签退链接 | `GET .../signInLinks`、`GET .../signOutLinks` |
| 每周重复、每天重复 | 创建日程时带 `recurrence`（见 api.md） |
| 只看人忙闲（不针对会议室） | `POST .../querySchedule` |

## 工作流程（每次执行前）

1. **识别任务** → 按上表归类后，再选具体 API（见 `references/api.md`）。
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
grep -A 22 "^## 7. 视频会议" references/api.md
grep -A 28 "^## 8. 查询会议室忙闲" references/api.md
grep -A 25 "^## 9. 添加与移除会议室" references/api.md
grep -A 18 "^## 10. 签到与签退链接" references/api.md
grep -A 22 "^## 11. 签到与签退详情列表" references/api.md
grep -A 18 "^## 12. 签到与签退操作" references/api.md
grep -A 35 "^## 13. 循环日程" references/api.md
grep -A 15 "^## 14. 订阅日历" references/api.md
grep -A 15 "^## 错误码" references/api.md
grep -A 18 "^## 所需应用权限" references/api.md
```
