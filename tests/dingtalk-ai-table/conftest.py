"""
dingtalk-ai-table 测试专属 fixtures
  - base_id: AI 表格（.able 文件）nodeId
  - test_sheet: 临时工作表，测试完毕自动删除

配置方式（在 .env 中设置 TEST_NOTABLE_ID）：
  填写 AI 表格（.able）文档的 nodeId，
  即分享链接 https://alidocs.dingtalk.com/i/nodes/<nodeId>?... 中的 nodeId。

所用 API：/v1.0/notable/bases/{base_id}/...（notable_1_0）
"""
import os
import pytest
import requests

BASE_URL = "https://api.dingtalk.com/v1.0/notable"


@pytest.fixture(scope="session")
def base_id():
    """返回 AI 表格 notable base_id（即文件 nodeId）。未设置则跳过全部测试。"""
    bid = os.environ.get("TEST_NOTABLE_ID", "").strip()
    if not bid:
        pytest.skip(
            "未设置 TEST_NOTABLE_ID。"
            "请在 .env 填写 AI 表格（.able）文档的 nodeId，"
            "从 alidocs 分享链接 /nodes/<nodeId> 中提取。"
        )
    return bid


@pytest.fixture(scope="session")
def api_headers(token):
    """返回带鉴权的请求头字典。"""
    return {
        "x-acs-dingtalk-access-token": token,
        "Content-Type": "application/json",
    }


@pytest.fixture(scope="session")
def test_sheet(token, operator_id, base_id, api_headers):
    """
    Session 级别测试工作表：创建一张含 "title" 文本字段的工作表，
    测试结束后自动删除。

    yields: (sheet_id: str, field_name: str)
    """
    resp = requests.post(
        f"{BASE_URL}/bases/{base_id}/sheets?operatorId={operator_id}",
        headers=api_headers,
        json={"name": "__pytest_sheet__", "fields": [{"name": "title", "type": "text"}]},
        timeout=15,
    )
    data = resp.json()
    assert "id" in data, f"创建测试工作表失败：{resp.text}"
    sheet_id = data["id"]

    yield sheet_id, "title"

    # Teardown
    requests.delete(
        f"{BASE_URL}/bases/{base_id}/sheets/{sheet_id}?operatorId={operator_id}",
        headers={k: v for k, v in api_headers.items() if k != "Content-Type"},
        timeout=15,
    )
