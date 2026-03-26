---
name: dingtalk-message
description: 钉钉消息发送。当用户提到"钉钉消息"、"发消息"、"发通知"、"群通知"、"群消息"、"Webhook"、"机器人消息"、"机器人发消息"、"工作通知"、"单聊消息"、"群聊消息"、"撤回消息"、"消息已读"、"发送Markdown"、"发卡片消息"、"ActionCard"、"@某人"、"@员工"、"at某人"、"提醒某人"、"dingtalk message"、"send message"、"robot message"、"work notification"时使用此技能。支持：群自定义 Webhook 机器人（文本/Markdown/ActionCard/Link/FeedCard + 加签 + @某人）、企业内部应用机器人单聊和群聊发送、消息撤回、已读查询、工作通知等全部消息类操作。
---

# 钉钉消息技能
负责钉钉消息发送的所有操作。本文件为**策略指南**；完整 API 请求格式、场景路由、消息类型速查、身份标识、错误码等见 `references/api.md`。

> `dt_helper.sh` 位于本 `SKILL.md` 同级目录的 `scripts/dt_helper.sh`。

## 四种消息通道

| 通道 | 适用场景 | Token | 特点 |
|---|---|---|---|
| **Webhook 机器人** | 往指定群发通知 | 无需 | 最简单；URL 自带凭证 |
| **企业内部应用机器人** | 单聊私信 / 群聊 | `--token`（新版） | 可撤回、查已读 |
| **工作通知** | 应用推送到"工作通知" | `--old-token`（旧版） | 可推全员/部门 |
| **sessionWebhook** | 回调中直接回复 | 无需 | 回调消息自带临时 URL |

## 工作流程（每次执行前）
1. **识别通道** → 按 api.md「场景路由」判断属于哪个通道
2. **校验配置** → `bash scripts/dt_helper.sh --get KEY` 读取该通道所需键值
3. **收集缺失项** → 一次性询问并 `bash scripts/dt_helper.sh --set KEY=VALUE` 写入
4. **获取 Token** → 机器人用 `--token`；工作通知用 `--old-token`；Webhook/sessionWebhook 无需
5. **执行 API** → 多行逻辑写入 `/tmp/<task>.sh` 再执行；禁止 heredoc

### 各通道所需配置
| 通道 | 所需配置 | 来源说明 |
|---|---|---|
| Webhook | `DINGTALK_WEBHOOK_URL`（加签额外需 `DINGTALK_WEBHOOK_SECRET`） | 群设置 → 智能群助手 → 添加自定义机器人 |
| 机器人消息 | `DINGTALK_APP_KEY` + `DINGTALK_APP_SECRET` | 开放平台 → 应用管理 → 凭证信息 |
| 工作通知 | `DINGTALK_APP_KEY` + `DINGTALK_APP_SECRET` + `DINGTALK_AGENT_ID` | agentId 在应用管理 → 基本信息 |

> - `robotCode` = `appKey`（完全一致，无需额外配置）
> - 凭证禁止在输出中完整打印，确认时仅显示前 4 位 + `****`
> - **消息内容缺失时**：先询问用户想发什么，不要自行编造

### 身份标识
**消息 API 只接受 userId（staffId）**，不接受 unionId。详见 `grep -A 20 "^## 身份标识" references/api.md`。
- **unionId → userId** 转换：`bash scripts/dt_helper.sh --to-userid <unionId>`
- **群消息发送方式选择**：发群消息时须先询问用户用 Webhook 还是企业机器人，详见 `grep -A 20 "^### 群消息发送方式选择" references/api.md`

### 执行脚本模板
```bash
#!/bin/bash
set -e
HELPER="./scripts/dt_helper.sh"
TOKEN=$(bash "$HELPER" --token)
USER_ID=$(bash "$HELPER" --get DINGTALK_MY_USER_ID | cut -d= -f2)

# 机器人单聊示例
RESP=$(curl -s -w '\nHTTP_STATUS:%{http_code}' -X POST "https://api.dingtalk.com/v1.0/robot/oToMessages/batchSend" \
  -H "x-acs-dingtalk-access-token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"robotCode":"'$(bash "$HELPER" --get DINGTALK_APP_KEY | cut -d= -f2)'","userIds":["'$USER_ID'"],"msgKey":"sampleText","msgParam":"{\"content\":\"测试消息\"}"}')
echo "$RESP"
```

```bash
#!/bin/bash
set -e
HELPER="./scripts/dt_helper.sh"
OLD_TOKEN=$(bash "$HELPER" --old-token)
AGENT_ID=$(bash "$HELPER" --get DINGTALK_AGENT_ID | cut -d= -f2)
USER_ID=$(bash "$HELPER" --get DINGTALK_MY_USER_ID | cut -d= -f2)

# 工作通知示例
RESP=$(curl -s -w '\nHTTP_STATUS:%{http_code}' -X POST "https://oapi.dingtalk.com/topapi/message/corpconversation/asyncsend_v2?access_token=$OLD_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"'$AGENT_ID'","userid_list":"'$USER_ID'","msg":{"msgtype":"text","text":{"content":"测试工作通知"}}}')
echo "$RESP"
```

> Token 异常时：`bash "$HELPER" --token --nocache` 或 `bash "$HELPER" --old-token --nocache`

## references/api.md 查阅索引
```bash
grep -A 196 "^## 一、群自定义 Webhook 机器人" references/api.md
grep -A 192 "^## 二、企业内部应用机器人" references/api.md
grep -A 145 "^## 三、工作通知" references/api.md
grep -A 60  "^## 四、sessionWebhook" references/api.md
grep -A 30  "^## 场景路由" references/api.md
grep -A 20  "^### 群消息发送方式选择" references/api.md
grep -A 25  "^## 身份标识" references/api.md
grep -A 30  "^## 消息类型速查" references/api.md
grep -A 33  "^## 错误码" references/api.md
grep -A 12  "^## 所需应用权限" references/api.md
```
