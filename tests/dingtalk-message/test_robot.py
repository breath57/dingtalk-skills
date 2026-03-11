"""
测试：企业内部应用机器人消息
API:
  - POST /v1.0/robot/oToMessages/batchSend     — 批量单聊
  - POST /v1.0/robot/groupMessages/send         — 群聊
  - GET  /v1.0/robot/oToMessages/readStatus     — 已读查询
  - POST /v1.0/robot/otoMessages/batchRecall    — 撤回单聊
  - POST /v1.0/robot/groupMessages/recall       — 撤回群聊

每个测试独立完成发送→验证→清理（撤回）的完整生命周期。
"""
import json
import time
import requests
import pytest

BASE_URL = "https://api.dingtalk.com/v1.0/robot"


def _robot_headers(token: str) -> dict:
    return {
        "x-acs-dingtalk-access-token": token,
        "Content-Type": "application/json",
    }


# ─── 单聊消息：发送 ──────────────────────────────────────────────────

def test_robot_send_text_to_user(token, robot_code, test_user_id):
    """
    POST /oToMessages/batchSend (sampleText)
    验证：返回 processQueryKey 非空，无 invalidStaffIdList。
    """
    headers = _robot_headers(token)
    resp = requests.post(
        f"{BASE_URL}/oToMessages/batchSend",
        headers=headers,
        json={
            "robotCode": robot_code,
            "userIds": [test_user_id],
            "msgKey": "sampleText",
            "msgParam": json.dumps({"content": f"[pytest] 单聊文本测试 {time.strftime('%H:%M:%S')}"}),
        },
        timeout=15,
    )
    assert resp.status_code == 200, f"请求失败 {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data.get("processQueryKey"), f"processQueryKey 为空：{data}"
    invalid = data.get("invalidStaffIdList") or []
    assert test_user_id not in invalid, f"userId 无效：{data}"

    # 撤回消息，避免对测试用户造成干扰
    time.sleep(1)
    requests.post(
        f"{BASE_URL}/otoMessages/batchRecall",
        headers=headers,
        json={
            "robotCode": robot_code,
            "processQueryKeys": [data["processQueryKey"]],
        },
        timeout=15,
    )


def test_robot_send_markdown_to_user(token, robot_code, test_user_id):
    """
    POST /oToMessages/batchSend (sampleMarkdown)
    验证：返回 processQueryKey 非空。
    """
    headers = _robot_headers(token)
    resp = requests.post(
        f"{BASE_URL}/oToMessages/batchSend",
        headers=headers,
        json={
            "robotCode": robot_code,
            "userIds": [test_user_id],
            "msgKey": "sampleMarkdown",
            "msgParam": json.dumps({
                "title": "pytest Markdown 测试",
                "text": f"## 自动化测试\n\n**时间**：{time.strftime('%Y-%m-%d %H:%M:%S')}\n\n来自 dingtalk-message pytest",
            }),
        },
        timeout=15,
    )
    assert resp.status_code == 200, f"请求失败 {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data.get("processQueryKey"), f"processQueryKey 为空：{data}"

    time.sleep(1)
    requests.post(
        f"{BASE_URL}/otoMessages/batchRecall",
        headers=headers,
        json={
            "robotCode": robot_code,
            "processQueryKeys": [data["processQueryKey"]],
        },
        timeout=15,
    )


def test_robot_send_action_card_to_user(token, robot_code, test_user_id):
    """
    POST /oToMessages/batchSend (sampleActionCard)
    验证：返回 processQueryKey 非空。
    """
    headers = _robot_headers(token)
    resp = requests.post(
        f"{BASE_URL}/oToMessages/batchSend",
        headers=headers,
        json={
            "robotCode": robot_code,
            "userIds": [test_user_id],
            "msgKey": "sampleActionCard",
            "msgParam": json.dumps({
                "title": "pytest ActionCard",
                "text": "## ActionCard 测试\n\n点击按钮跳转",
                "singleTitle": "查看项目",
                "singleURL": "https://github.com/breath57/dingtalk-skills",
            }),
        },
        timeout=15,
    )
    assert resp.status_code == 200, f"请求失败 {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data.get("processQueryKey"), f"processQueryKey 为空：{data}"

    time.sleep(1)
    requests.post(
        f"{BASE_URL}/otoMessages/batchRecall",
        headers=headers,
        json={
            "robotCode": robot_code,
            "processQueryKeys": [data["processQueryKey"]],
        },
        timeout=15,
    )


# ─── 单聊消息：已读查询 ──────────────────────────────────────────────

def test_robot_query_read_status(token, robot_code, test_user_id):
    """
    发送 → 查询已读状态 → 验证返回 messageReadInfoList。
    """
    headers = _robot_headers(token)

    # 先发一条
    send_resp = requests.post(
        f"{BASE_URL}/oToMessages/batchSend",
        headers=headers,
        json={
            "robotCode": robot_code,
            "userIds": [test_user_id],
            "msgKey": "sampleText",
            "msgParam": json.dumps({"content": f"[pytest] 已读测试 {time.strftime('%H:%M:%S')}"}),
        },
        timeout=15,
    )
    assert send_resp.status_code == 200
    pqk = send_resp.json().get("processQueryKey")
    assert pqk

    time.sleep(2)  # 等待消息到达

    # 查询已读（GET + query params，不是 POST）
    query_resp = requests.get(
        f"{BASE_URL}/oToMessages/readStatus",
        headers=headers,
        params={
            "robotCode": robot_code,
            "processQueryKey": pqk,
        },
        timeout=15,
    )
    assert query_resp.status_code == 200, f"查询失败: {query_resp.text}"
    data = query_resp.json()
    # messageReadInfoList 可能为空列表（测试期间用户还未读属正常）
    assert "messageReadInfoList" in data, f"返回格式异常：{data}"

    # 清理
    requests.post(
        f"{BASE_URL}/otoMessages/batchRecall",
        headers=headers,
        json={"robotCode": robot_code, "processQueryKeys": [pqk]},
        timeout=15,
    )


# ─── 单聊消息：撤回 ──────────────────────────────────────────────────

def test_robot_recall_oto(token, robot_code, test_user_id):
    """
    发送 → 撤回 → 验证 successResult 包含该 processQueryKey。
    """
    headers = _robot_headers(token)

    # 先发一条
    send_resp = requests.post(
        f"{BASE_URL}/oToMessages/batchSend",
        headers=headers,
        json={
            "robotCode": robot_code,
            "userIds": [test_user_id],
            "msgKey": "sampleText",
            "msgParam": json.dumps({"content": f"[pytest] 撤回测试 {time.strftime('%H:%M:%S')}"}),
        },
        timeout=15,
    )
    assert send_resp.status_code == 200
    pqk = send_resp.json().get("processQueryKey")
    assert pqk

    time.sleep(1)

    # 撤回
    recall_resp = requests.post(
        f"{BASE_URL}/otoMessages/batchRecall",
        headers=headers,
        json={
            "robotCode": robot_code,
            "processQueryKeys": [pqk],
        },
        timeout=15,
    )
    assert recall_resp.status_code == 200, f"撤回失败: {recall_resp.text}"
    data = recall_resp.json()
    success = data.get("successResult") or []
    assert pqk in success, f"processQueryKey 不在 successResult 中：{data}"


# ─── 群聊消息：发送 ──────────────────────────────────────────────────

def test_robot_send_to_group(token, robot_code, open_conversation_id):
    """
    POST /groupMessages/send (sampleText)
    验证：返回 processQueryKey 非空。
    """
    headers = _robot_headers(token)
    resp = requests.post(
        f"{BASE_URL}/groupMessages/send",
        headers=headers,
        json={
            "robotCode": robot_code,
            "openConversationId": open_conversation_id,
            "msgKey": "sampleText",
            "msgParam": json.dumps({"content": f"[pytest] 群聊消息测试 {time.strftime('%H:%M:%S')}"}),
        },
        timeout=15,
    )
    assert resp.status_code == 200, f"请求失败 {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data.get("processQueryKey"), f"processQueryKey 为空：{data}"

    # 撤回
    time.sleep(1)
    requests.post(
        f"{BASE_URL}/groupMessages/recall",
        headers=headers,
        json={
            "robotCode": robot_code,
            "openConversationId": open_conversation_id,
            "processQueryKeys": [data["processQueryKey"]],
        },
        timeout=15,
    )


# ─── 群聊消息：撤回 ──────────────────────────────────────────────────

def test_robot_recall_group(token, robot_code, open_conversation_id):
    """
    发送群消息 → 撤回 → 验证 successResult。
    """
    headers = _robot_headers(token)

    # 发送
    send_resp = requests.post(
        f"{BASE_URL}/groupMessages/send",
        headers=headers,
        json={
            "robotCode": robot_code,
            "openConversationId": open_conversation_id,
            "msgKey": "sampleText",
            "msgParam": json.dumps({"content": f"[pytest] 群撤回测试 {time.strftime('%H:%M:%S')}"}),
        },
        timeout=15,
    )
    assert send_resp.status_code == 200
    pqk = send_resp.json().get("processQueryKey")
    assert pqk

    time.sleep(1)

    # 撤回
    recall_resp = requests.post(
        f"{BASE_URL}/groupMessages/recall",
        headers=headers,
        json={
            "robotCode": robot_code,
            "openConversationId": open_conversation_id,
            "processQueryKeys": [pqk],
        },
        timeout=15,
    )
    assert recall_resp.status_code == 200, f"撤回失败: {recall_resp.text}"
    data = recall_resp.json()
    success = data.get("successResult") or []
    assert pqk in success, f"processQueryKey 不在 successResult 中：{data}"
