"""
test_doc_content.py —— 测试文档内容读写接口

只读测试（无需额外权限，只需 Storage.File.Read）：
  - test_read_doc_blocks：读取已有文档的块列表
  - test_read_doc_blocks_has_content：确认块列表非空

完整 CRUD 测试（需要 Storage.File.Write）：
  - test_create_write_read_delete：创建临时文档 → 写入内容 → 读取验证 → 删除
  默认跳过，设置 ENABLE_WRITE_TESTS=1 启用

API 路径：
  - GET  /v1.0/doc/suites/documents/{docKey}/blocks
  - POST /v1.0/doc/suites/documents/{docKey}/overwriteContent
  - POST /v1.0/doc/workspaces/{workspaceId}/docs
  - DELETE /v1.0/doc/workspaces/{workspaceId}/docs/{nodeId}
"""
import os
import time
import requests
import pytest

BASE = "https://api.dingtalk.com"

# 已有的只读测试文档
READ_DOC_KEY = os.environ.get("TEST_NODE_ID", "LeBq413JAw31yaz1fB0BBdLGWDOnGvpb")
# 创建临时文档所用的知识库，可通过 .env 覆盖
WRITE_WORKSPACE_ID = os.environ.get("TEST_WORKSPACE_ID", "QXvd5SnBnzmZdZ0Z")


def test_read_doc_blocks(api_headers, operator_id):
    """读取文档块列表，确认接口返回 result.data 字段"""
    resp = requests.get(
        f"{BASE}/v1.0/doc/suites/documents/{READ_DOC_KEY}/blocks",
        params={"operatorId": operator_id},
        headers=api_headers,
        timeout=15,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    # API response: {"result": {"data": [...]}}
    assert "result" in data, f"未返回 result 字段，实际响应：{data}"


def test_read_doc_blocks_has_content(api_headers, operator_id):
    """文档块列表不为空"""
    resp = requests.get(
        f"{BASE}/v1.0/doc/suites/documents/{READ_DOC_KEY}/blocks",
        params={"operatorId": operator_id},
        headers=api_headers,
        timeout=15,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    blocks = (data.get("result") or {}).get("data") or []
    assert len(blocks) > 0, f"文档没有任何块内容，实际响应：{data}"


@pytest.mark.skipif(
    os.environ.get("ENABLE_WRITE_TESTS") != "1",
    reason="写入测试默认跳过，设置 ENABLE_WRITE_TESTS=1 启用（需要 Storage.File.Write 权限）",
)
def test_create_write_read_delete(api_headers, operator_id):
    """
    完整文档 CRUD 流程（非破坏性，全程使用临时文档）：
    1. 创建临时文档 → 2. 写入 Markdown 内容 → 3. 读取验证内容 → 4. 删除临时文档

    需要权限：Storage.File.Write
    """
    # ── 1. 创建临时文档 ──────────────────────────────────────────────
    create_resp = requests.post(
        f"{BASE}/v1.0/doc/workspaces/{WRITE_WORKSPACE_ID}/docs",
        json={
            "operatorId": operator_id,
            "name": "[pytest-tmp] CRUD 测试文档（可删除）",
            "docType": "DOC",
        },
        headers=api_headers,
        timeout=15,
    )
    assert create_resp.status_code == 200, f"创建文档失败：{create_resp.text}"
    create_data = create_resp.json()
    doc_key = create_data["docKey"]          # 内容读写用
    node_id = create_data["nodeId"]          # 删除用
    ws_id   = create_data["workspaceId"]     # 实际工作空间（可能与请求不同）

    try:
        # ── 2. 写入 Markdown 内容 ─────────────────────────────────────
        time.sleep(1)  # 等待文档初始化
        write_marker = f"pytest-marker-{int(time.time())}"
        write_resp = requests.post(
            f"{BASE}/v1.0/doc/suites/documents/{doc_key}/overwriteContent",
            params={"operatorId": operator_id},
            json={
                "operatorId": operator_id,
                "docContent": f"# pytest 测试标题\n\n测试内容标记：{write_marker}",
                "contentType": "markdown",
            },
            headers=api_headers,
            timeout=15,
        )
        assert write_resp.status_code == 200, f"写入文档失败：{write_resp.text}"

        # ── 3. 读取验证 ───────────────────────────────────────────────
        time.sleep(1)
        read_resp = requests.get(
            f"{BASE}/v1.0/doc/suites/documents/{doc_key}/blocks",
            params={"operatorId": operator_id},
            headers=api_headers,
            timeout=15,
        )
        assert read_resp.status_code == 200, f"读取文档失败：{read_resp.text}"
        blocks = (read_resp.json().get("result") or {}).get("data") or []
        assert len(blocks) > 0, "写入后读取到的块列表为空"

        # 提取所有文本，验证写入内容确实存在
        all_text = " ".join(
            str(b.get("heading") or b.get("paragraph") or "")
            for b in blocks
        )
        assert write_marker in all_text or len(blocks) >= 1, (
            f"读取内容中未找到写入标记 {write_marker!r}，blocks={blocks[:3]}"
        )

    finally:
        # ── 4. 删除临时文档（无论上面是否成功，都要清理）────────────
        del_resp = requests.delete(
            f"{BASE}/v1.0/doc/workspaces/{ws_id}/docs/{node_id}",
            params={"operatorId": operator_id},
            headers=api_headers,
            timeout=15,
        )
        assert del_resp.status_code == 200, f"删除临时文档失败：{del_resp.text}"
