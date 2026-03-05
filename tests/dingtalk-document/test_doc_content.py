"""
test_doc_content.py —— 测试文档内容读写接口
  - GET /v1.0/doc/suites/documents/{docKey}/blocks  （读取文档块）
  - POST /v1.0/doc/suites/documents/{docKey}/overwriteContent （覆写文档）

所需权限：Storage.File.Read（读）
注意：覆写测试默认跳过（设置环境变量 ENABLE_WRITE_TESTS=1 启用）
"""
import os
import requests
import pytest

BASE = "https://api.dingtalk.com"

DOC_KEY = os.environ.get("TEST_NODE_ID", "LeBq413JAw31yaz1fB0BBdLGWDOnGvpb")


def test_read_doc_blocks(api_headers, operator_id):
    """读取文档块列表，确认接口返回成功且包含 blocks"""
    resp = requests.get(
        f"{BASE}/v1.0/doc/suites/documents/{DOC_KEY}/blocks",
        params={"operatorId": operator_id},
        headers=api_headers,
        timeout=15,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    # API response: {"result": {"data": [...]}}
    assert "result" in data or "blocks" in data, (
        f"未返回 result 字段，实际响应：{data}"
    )


def test_read_doc_blocks_has_content(api_headers, operator_id):
    """文档块列表不为空"""
    resp = requests.get(
        f"{BASE}/v1.0/doc/suites/documents/{DOC_KEY}/blocks",
        params={"operatorId": operator_id},
        headers=api_headers,
        timeout=15,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    # API response: {"result": {"data": [...]}}
    blocks = (data.get("result") or {}).get("data") or data.get("blocks") or []
    assert len(blocks) > 0, f"文档没有任何块内容，实际响应：{data}"


@pytest.mark.skipif(
    os.environ.get("ENABLE_WRITE_TESTS") != "1",
    reason="写入测试默认跳过，设置 ENABLE_WRITE_TESTS=1 启用",
)
def test_overwrite_doc_content(api_headers, operator_id):
    """
    覆写文档内容（破坏性操作，默认跳过）
    设置环境变量 ENABLE_WRITE_TESTS=1 启用此测试
    """
    payload = {
        "operatorId": operator_id,
        "content": [
            {
                "type": "paragraph",
                "elements": [{"type": "text", "text": "【测试写入】pytest overwrite test"}],
            }
        ],
    }
    resp = requests.post(
        f"{BASE}/v1.0/doc/suites/documents/{DOC_KEY}/overwriteContent",
        params={"operatorId": operator_id},
        json=payload,
        headers=api_headers,
        timeout=15,
    )
    assert resp.status_code == 200, resp.text
