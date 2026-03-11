"""
测试：群自定义 Webhook 机器人消息
API: POST https://oapi.dingtalk.com/robot/send?access_token=<TOKEN>

覆盖消息类型：text, markdown, actionCard (单按钮/多按钮), link, feedCard
以及 HMAC-SHA256 加签模式。

每个测试独立发送消息，验证返回 errcode == 0。
"""
import time
import pytest


# ─── Text ─────────────────────────────────────────────────────────────

def test_webhook_text(webhook_send):
    """
    发送文本消息 → errcode == 0
    """
    result = webhook_send({
        "msgtype": "text",
        "text": {"content": "[pytest] 文本消息测试 " + time.strftime("%H:%M:%S")},
    })
    assert result.get("errcode") == 0, f"发送失败：{result}"


# ─── Markdown ─────────────────────────────────────────────────────────

def test_webhook_markdown(webhook_send):
    """
    发送 Markdown 消息 → errcode == 0
    """
    result = webhook_send({
        "msgtype": "markdown",
        "markdown": {
            "title": "pytest 测试通知",
            "text": (
                "## 自动化测试通知\n\n"
                f"- **时间**：{time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                "- **状态**：✅ 通过\n"
                "- **来源**：dingtalk-message pytest"
            ),
        },
    })
    assert result.get("errcode") == 0, f"发送失败：{result}"


# ─── ActionCard（整体跳转） ───────────────────────────────────────────

def test_webhook_action_card_single(webhook_send):
    """
    发送 ActionCard（单按钮整体跳转）→ errcode == 0
    """
    result = webhook_send({
        "msgtype": "actionCard",
        "actionCard": {
            "title": "pytest ActionCard 测试",
            "text": "## ActionCard 测试\n\n单按钮整体跳转测试",
            "singleTitle": "查看详情",
            "singleURL": "https://github.com/breath57/dingtalk-skills",
        },
    })
    assert result.get("errcode") == 0, f"发送失败：{result}"


# ─── ActionCard（多按钮） ─────────────────────────────────────────────

def test_webhook_action_card_multi(webhook_send):
    """
    发送 ActionCard（多按钮）→ errcode == 0
    """
    result = webhook_send({
        "msgtype": "actionCard",
        "actionCard": {
            "title": "pytest 多按钮测试",
            "text": "## 多按钮 ActionCard\n\n请选择操作",
            "btnOrientation": "1",
            "btns": [
                {"title": "GitHub", "actionURL": "https://github.com/breath57/dingtalk-skills"},
                {"title": "文档", "actionURL": "https://open.dingtalk.com/document/"},
            ],
        },
    })
    assert result.get("errcode") == 0, f"发送失败：{result}"


# ─── Link ─────────────────────────────────────────────────────────────

def test_webhook_link(webhook_send):
    """
    发送 Link 消息 → errcode == 0
    """
    result = webhook_send({
        "msgtype": "link",
        "link": {
            "title": "pytest Link 测试",
            "text": "这是一条 Link 类型消息测试",
            "messageUrl": "https://github.com/breath57/dingtalk-skills",
            "picUrl": "",
        },
    })
    assert result.get("errcode") == 0, f"发送失败：{result}"


# ─── FeedCard ─────────────────────────────────────────────────────────

def test_webhook_feedcard(webhook_send):
    """
    发送 FeedCard 消息 → errcode == 0
    """
    result = webhook_send({
        "msgtype": "feedCard",
        "feedCard": {
            "links": [
                {
                    "title": "dingtalk-document 技能",
                    "messageURL": "https://github.com/breath57/dingtalk-skills",
                    "picURL": "",
                },
                {
                    "title": "dingtalk-ai-table 技能",
                    "messageURL": "https://github.com/breath57/dingtalk-skills",
                    "picURL": "",
                },
            ],
        },
    })
    assert result.get("errcode") == 0, f"发送失败：{result}"


# ─── 加签 ─────────────────────────────────────────────────────────────

def test_webhook_with_sign(webhook_send, webhook_secret):
    """
    显式验证加签模式：要求 TEST_WEBHOOK_SECRET 已配置 → errcode == 0
    （其他测试已通过 webhook_send 自动加签；本测试额外校验密钥存在）
    """
    result = webhook_send({
        "msgtype": "text",
        "text": {"content": "[pytest] 加签消息测试 " + time.strftime("%H:%M:%S")},
    })
    assert result.get("errcode") == 0, f"加签发送失败：{result}"
