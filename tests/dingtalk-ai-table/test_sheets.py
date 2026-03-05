"""
test_sheets.py —— 测试 AI 表格工作表（Sheet）相关接口
  - GET  /v1.0/doc/workbooks/{workbookId}/sheets          列出所有工作表
  - GET  /v1.0/doc/workbooks/{workbookId}/sheets/{sheetId}  查询单个工作表
  - POST /v1.0/doc/workbooks/{workbookId}/sheets          创建工作表
  - DELETE /v1.0/doc/workbooks/{workbookId}/sheets/{sheetId}  删除工作表

所需权限：Doc.Sheet.Read、Doc.Sheet.Write（写入测试）
测试文件：https://alidocs.dingtalk.com/i/nodes/MyQA2dXW7ePBO49BSMwxNm35JzlwrZgb
"""
import os
import requests

BASE = "https://api.dingtalk.com"
TEST_WORKBOOK_ID = os.environ.get("TEST_WORKBOOK_ID", "MyQA2dXW7ePBO49BSMwxNm35JzlwrZgb")
ENABLE_WRITE = os.environ.get("ENABLE_WRITE_TESTS", "0") == "1"


# ── 只读测试 ────────────────────────────────────────────────────────────


def test_list_sheets(api_headers):
    """列出工作簿中所有工作表，校验至少存在一个工作表"""
    resp = requests.get(
        f"{BASE}/v1.0/doc/workbooks/{TEST_WORKBOOK_ID}/sheets",
        headers=api_headers,
        timeout=15,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    sheets = data.get("sheets", data)
    assert isinstance(sheets, list), f"期望返回列表，实际：{data}"
    assert len(sheets) >= 1, "工作簿中应至少有一个工作表"

    # 校验字段结构
    first = sheets[0]
    assert "sheetId" in first, f"工作表缺少 sheetId 字段：{first}"
    assert "name" in first, f"工作表缺少 name 字段：{first}"


def test_get_single_sheet(api_headers):
    """先获取工作表列表，再查询第一个工作表的详情"""
    # Step 1：获取列表，取第一个 sheetId
    list_resp = requests.get(
        f"{BASE}/v1.0/doc/workbooks/{TEST_WORKBOOK_ID}/sheets",
        headers=api_headers,
        timeout=15,
    )
    assert list_resp.status_code == 200, list_resp.text
    sheets = list_resp.json().get("sheets", list_resp.json())
    assert sheets, "获取工作表列表为空，无法继续"
    sheet_id = sheets[0]["sheetId"]
    sheet_name = sheets[0]["name"]

    # Step 2：查询单个工作表
    resp = requests.get(
        f"{BASE}/v1.0/doc/workbooks/{TEST_WORKBOOK_ID}/sheets/{sheet_id}",
        headers=api_headers,
        timeout=15,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("sheetId") == sheet_id, data
    assert data.get("name") == sheet_name, data


# ── 写入测试（需 ENABLE_WRITE_TESTS=1） ────────────────────────────────


def test_create_and_delete_sheet(api_headers):
    """创建一个临时工作表，验证返回结构后立即删除"""
    if not ENABLE_WRITE:
        import pytest
        pytest.skip("写入测试未启用，设置 ENABLE_WRITE_TESTS=1 开启")

    new_name = "pytest_临时工作表"

    # 创建
    create_resp = requests.post(
        f"{BASE}/v1.0/doc/workbooks/{TEST_WORKBOOK_ID}/sheets",
        headers=api_headers,
        json={"name": new_name},
        timeout=15,
    )
    assert create_resp.status_code in (200, 201), create_resp.text
    created = create_resp.json()
    new_sheet_id = created.get("sheetId")
    assert new_sheet_id, f"创建工作表未返回 sheetId：{created}"
    assert created.get("name") == new_name, created

    # 验证出现在列表中
    list_resp = requests.get(
        f"{BASE}/v1.0/doc/workbooks/{TEST_WORKBOOK_ID}/sheets",
        headers=api_headers,
        timeout=15,
    )
    assert list_resp.status_code == 200, list_resp.text
    sheet_ids = [s["sheetId"] for s in list_resp.json().get("sheets", [])]
    assert new_sheet_id in sheet_ids, f"新工作表未出现在列表中：{sheet_ids}"

    # 删除
    del_resp = requests.delete(
        f"{BASE}/v1.0/doc/workbooks/{TEST_WORKBOOK_ID}/sheets/{new_sheet_id}",
        headers=api_headers,
        timeout=15,
    )
    assert del_resp.status_code in (200, 204), del_resp.text

    # 验证已删除
    list_resp2 = requests.get(
        f"{BASE}/v1.0/doc/workbooks/{TEST_WORKBOOK_ID}/sheets",
        headers=api_headers,
        timeout=15,
    )
    assert list_resp2.status_code == 200, list_resp2.text
    sheet_ids2 = [s["sheetId"] for s in list_resp2.json().get("sheets", [])]
    assert new_sheet_id not in sheet_ids2, f"工作表删除后仍出现在列表中：{sheet_ids2}"
