"""
测试：工作通知（Work Notification）
API:
  - POST /topapi/message/corpconversation/asyncsend_v2   — 发送
  - POST /topapi/message/corpconversation/getsendresult  — 查询发送结果
  - POST /topapi/message/corpconversation/recall          — 撤回

工作通知出现在用户的"工作通知"会话中，常用于审批通知、系统告警等。
每个测试独立完成发送→验证→清理的完整生命周期。
"""
import time
import requests
import pytest

OAPI_BASE = "https://oapi.dingtalk.com"


# ─── 工作通知：发送文本 ──────────────────────────────────────────────

def test_work_notification_text(old_token, agent_id, test_user_id):
    """
    POST /topapi/message/corpconversation/asyncsend_v2 (text)
    验证：errcode == 0，task_id 非空。
    """
    resp = requests.post(
        f"{OAPI_BASE}/topapi/message/corpconversation/asyncsend_v2",
        params={"access_token": old_token},
        json={
            "agent_id": agent_id,
            "userid_list": test_user_id,
            "to_all_user": False,
            "msg": {
                "msgtype": "text",
                "text": {"content": f"[pytest] 工作通知文本测试 {time.strftime('%H:%M:%S')}"},
            },
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    assert data.get("errcode") == 0, f"发送失败：{data}"
    assert data.get("task_id"), f"task_id 为空：{data}"

    # 撤回
    time.sleep(1)
    requests.post(
        f"{OAPI_BASE}/topapi/message/corpconversation/recall",
        params={"access_token": old_token},
        json={"agent_id": agent_id, "msg_task_id": data["task_id"]},
        timeout=15,
    )


# ─── 工作通知：发送 Markdown ─────────────────────────────────────────

def test_work_notification_markdown(old_token, agent_id, test_user_id):
    """
    POST /topapi/message/corpconversation/asyncsend_v2 (markdown)
    验证：errcode == 0。
    """
    resp = requests.post(
        f"{OAPI_BASE}/topapi/message/corpconversation/asyncsend_v2",
        params={"access_token": old_token},
        json={
            "agent_id": agent_id,
            "userid_list": test_user_id,
            "to_all_user": False,
            "msg": {
                "msgtype": "markdown",
                "markdown": {
                    "title": "pytest 工作通知",
                    "text": (
                        "## 自动化测试通知\n\n"
                        f"- **时间**：{time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                        "- **状态**：✅ 测试通过\n"
                        "- **来源**：dingtalk-message pytest"
                    ),
                },
            },
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    assert data.get("errcode") == 0, f"发送失败：{data}"
    assert data.get("task_id"), f"task_id 为空：{data}"

    time.sleep(1)
    requests.post(
        f"{OAPI_BASE}/topapi/message/corpconversation/recall",
        params={"access_token": old_token},
        json={"agent_id": agent_id, "msg_task_id": data["task_id"]},
        timeout=15,
    )


# ─── 工作通知：发送 ActionCard ───────────────────────────────────────

def test_work_notification_action_card(old_token, agent_id, test_user_id):
    """
    POST /topapi/message/corpconversation/asyncsend_v2 (action_card)
    验证：errcode == 0。
    """
    resp = requests.post(
        f"{OAPI_BASE}/topapi/message/corpconversation/asyncsend_v2",
        params={"access_token": old_token},
        json={
            "agent_id": agent_id,
            "userid_list": test_user_id,
            "to_all_user": False,
            "msg": {
                "msgtype": "action_card",
                "action_card": {
                    "title": "pytest ActionCard 通知",
                    "markdown": "## ActionCard 测试\n\n来自 dingtalk-message pytest",
                    "single_title": "查看项目",
                    "single_url": "https://github.com/breath57/dingtalk-skills",
                },
            },
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    assert data.get("errcode") == 0, f"发送失败：{data}"
    assert data.get("task_id"), f"task_id 为空：{data}"

    time.sleep(1)
    requests.post(
        f"{OAPI_BASE}/topapi/message/corpconversation/recall",
        params={"access_token": old_token},
        json={"agent_id": agent_id, "msg_task_id": data["task_id"]},
        timeout=15,
    )


# ─── 工作通知：查询发送结果 ──────────────────────────────────────────

def test_work_notification_query_result(old_token, agent_id, test_user_id):
    """
    发送 → 查询发送结果 → 验证 send_result 结构。
    """
    # 发送
    send_resp = requests.post(
        f"{OAPI_BASE}/topapi/message/corpconversation/asyncsend_v2",
        params={"access_token": old_token},
        json={
            "agent_id": agent_id,
            "userid_list": test_user_id,
            "to_all_user": False,
            "msg": {
                "msgtype": "text",
                "text": {"content": f"[pytest] 发送结果查询测试 {time.strftime('%H:%M:%S')}"},
            },
        },
        timeout=15,
    )
    send_resp.raise_for_status()
    send_data = send_resp.json()
    assert send_data.get("errcode") == 0
    task_id = send_data.get("task_id")
    assert task_id

    time.sleep(3)  # 等待消息处理完成

    # 查询结果
    query_resp = requests.post(
        f"{OAPI_BASE}/topapi/message/corpconversation/getsendresult",
        params={"access_token": old_token},
        json={"agent_id": agent_id, "task_id": task_id},
        timeout=15,
    )
    query_resp.raise_for_status()
    query_data = query_resp.json()
    assert query_data.get("errcode") == 0, f"查询失败：{query_data}"
    result = query_data.get("send_result")
    assert result is not None, f"send_result 为空：{query_data}"

    # 验证 send_result 包含预期字段
    for key in ("read_user_id_list", "unread_user_id_list"):
        assert key in result, f"返回缺少 {key}：{result}"

    # 目标用户应在已读或未读列表中
    all_users = (result.get("read_user_id_list") or []) + (result.get("unread_user_id_list") or [])
    assert test_user_id in all_users, f"目标用户不在发送列表中：{result}"

    # 撤回
    requests.post(
        f"{OAPI_BASE}/topapi/message/corpconversation/recall",
        params={"access_token": old_token},
        json={"agent_id": agent_id, "msg_task_id": task_id},
        timeout=15,
    )


# ─── 工作通知：撤回 ──────────────────────────────────────────────────

def test_work_notification_recall(old_token, agent_id, test_user_id):
    """
    发送 → 撤回 → 验证 errcode == 0。
    """
    # 发送
    send_resp = requests.post(
        f"{OAPI_BASE}/topapi/message/corpconversation/asyncsend_v2",
        params={"access_token": old_token},
        json={
            "agent_id": agent_id,
            "userid_list": test_user_id,
            "to_all_user": False,
            "msg": {
                "msgtype": "text",
                "text": {"content": f"[pytest] 撤回测试 {time.strftime('%H:%M:%S')}"},
            },
        },
        timeout=15,
    )
    send_resp.raise_for_status()
    send_data = send_resp.json()
    assert send_data.get("errcode") == 0
    task_id = send_data.get("task_id")
    assert task_id

    time.sleep(2)

    # 撤回
    recall_resp = requests.post(
        f"{OAPI_BASE}/topapi/message/corpconversation/recall",
        params={"access_token": old_token},
        json={"agent_id": agent_id, "msg_task_id": task_id},
        timeout=15,
    )
    recall_resp.raise_for_status()
    recall_data = recall_resp.json()
    assert recall_data.get("errcode") == 0, f"撤回失败：{recall_data}"
