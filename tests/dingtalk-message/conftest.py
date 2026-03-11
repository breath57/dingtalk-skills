"""
dingtalk-message 测试专属 fixtures
  - webhook_url: 群自定义机器人 Webhook 地址
  - webhook_secret: 加签密钥（可选）
  - robot_code: 企业内部机器人 robotCode（通常 = appKey）
  - agent_id: 应用 agentId（工作通知用）
  - test_user_id: 测试目标用户 userId

配置方式（在 .env 中设置）：
  TEST_WEBHOOK_URL       - 群自定义机器人 Webhook 完整 URL
  TEST_WEBHOOK_SECRET    - 加签密钥（选填，不配置则跳过加签测试）
  TEST_ROBOT_CODE        - 机器人 robotCode（选填，不配置则跳过机器人消息测试）
  TEST_USER_ID           - 测试目标用户 userId（机器人单聊用）
  TEST_AGENT_ID          - 应用 agentId（工作通知用）
  TEST_OPEN_CONVERSATION_ID - 群会话 ID（机器人群聊用）
"""
import os
import time
import hmac
import hashlib
import base64
import urllib.parse
import requests
import pytest


def _build_signed_url(url: str, secret: str) -> str:
    """为 Webhook URL 添加 HMAC-SHA256 加签参数。"""
    timestamp = str(int(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code).decode("utf-8"))
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}timestamp={timestamp}&sign={sign}"


@pytest.fixture(scope="session")
def webhook_send(webhook_url):
    """返回一个发送函数，若配置了加签密钥则自动加签。"""
    secret = os.environ.get("TEST_WEBHOOK_SECRET", "").strip() or None

    def _send(payload: dict) -> dict:
        url = _build_signed_url(webhook_url, secret) if secret else webhook_url
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        return resp.json()

    return _send


@pytest.fixture(scope="session")
def webhook_url():
    """返回 Webhook URL。未设置则跳过 Webhook 测试。"""
    url = os.environ.get("TEST_WEBHOOK_URL", "").strip()
    if not url:
        pytest.skip(
            "未设置 TEST_WEBHOOK_URL。"
            "请在 .env 填写群自定义机器人的 Webhook 完整 URL。"
        )
    return url


@pytest.fixture(scope="session")
def webhook_secret():
    """返回 Webhook 加签密钥。未设置则跳过加签测试。"""
    secret = os.environ.get("TEST_WEBHOOK_SECRET", "").strip()
    if not secret:
        pytest.skip("未设置 TEST_WEBHOOK_SECRET，跳过加签测试。")
    return secret


@pytest.fixture(scope="session")
def robot_code():
    """返回机器人 robotCode。未设置则跳过机器人消息测试。"""
    code = os.environ.get("TEST_ROBOT_CODE", "").strip()
    if not code:
        pytest.skip(
            "未设置 TEST_ROBOT_CODE。"
            "请在 .env 填写企业内部应用的 robotCode（通常等于 appKey）。"
        )
    return code


@pytest.fixture(scope="session")
def test_user_id():
    """返回测试目标用户 userId。未设置则跳过单聊测试。"""
    uid = os.environ.get("TEST_USER_ID", "").strip()
    if not uid:
        pytest.skip("未设置 TEST_USER_ID，跳过机器人单聊测试。")
    return uid


@pytest.fixture(scope="session")
def agent_id():
    """返回应用 agentId。未设置则跳过工作通知测试。"""
    aid = os.environ.get("TEST_AGENT_ID", "").strip()
    if not aid:
        pytest.skip(
            "未设置 TEST_AGENT_ID。"
            "请在 .env 填写应用 agentId（开放平台 → 应用管理 → 基本信息）。"
        )
    return aid


@pytest.fixture(scope="session")
def open_conversation_id():
    """返回测试群会话 ID。未设置则跳过群聊测试。"""
    cid = os.environ.get("TEST_OPEN_CONVERSATION_ID", "").strip()
    if not cid:
        pytest.skip("未设置 TEST_OPEN_CONVERSATION_ID，跳过机器人群聊测试。")
    return cid


@pytest.fixture(scope="session")
def old_token():
    """获取旧版 access_token（工作通知使用 oapi.dingtalk.com）。"""
    app_key = os.environ.get("DINGTALK_APP_KEY", "").strip()
    app_secret = os.environ.get("DINGTALK_APP_SECRET", "").strip()
    if not app_key or not app_secret:
        pytest.skip("缺少 DINGTALK_APP_KEY 或 DINGTALK_APP_SECRET")

    import requests
    resp = requests.get(
        "https://oapi.dingtalk.com/gettoken",
        params={"appkey": app_key, "appsecret": app_secret},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    t = data.get("access_token")
    assert t, f"未获取到旧版 access_token：{data}"
    return t
