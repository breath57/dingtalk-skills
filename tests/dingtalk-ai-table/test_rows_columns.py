"""
test_rows_columns.py —— 测试 AI 表格行列操作相关接口
  - POST   .../insertRows             插入行
  - DELETE .../rows/{row}             删除行
  - PUT    .../rows/{row}/visibility  设置行显示/隐藏
  - POST   .../insertColumns          插入列
  - DELETE .../columns/{column}       删除列
  - PUT    .../columns/{column}/visibility  设置列显示/隐藏

所需权限：Doc.Sheet.Write
测试文件：https://alidocs.dingtalk.com/i/nodes/MyQA2dXW7ePBO49BSMwxNm35JzlwrZgb

注意：所有操作均为写操作，需设置 ENABLE_WRITE_TESTS=1 开启。
"""
import os
import requests

BASE = "https://api.dingtalk.com"
TEST_WORKBOOK_ID = os.environ.get("TEST_WORKBOOK_ID", "MyQA2dXW7ePBO49BSMwxNm35JzlwrZgb")
ENABLE_WRITE = os.environ.get("ENABLE_WRITE_TESTS", "0") == "1"


def _first_sheet_id(api_headers: dict) -> str:
    resp = requests.get(
        f"{BASE}/v1.0/doc/workbooks/{TEST_WORKBOOK_ID}/sheets",
        headers=api_headers,
        timeout=15,
    )
    resp.raise_for_status()
    sheets = resp.json().get("sheets", resp.json())
    assert sheets, "工作簿中没有可用工作表"
    return sheets[0]["sheetId"]


def _skip_if_readonly():
    if not ENABLE_WRITE:
        import pytest
        pytest.skip("写入测试未启用，设置 ENABLE_WRITE_TESTS=1 开启")


# ── 行操作 ─────────────────────────────────────────────────────────────


def test_insert_rows(api_headers):
    """在第 2 行（index=1）上方插入 2 行，验证接口响应正常"""
    _skip_if_readonly()
    sheet_id = _first_sheet_id(api_headers)

    resp = requests.post(
        f"{BASE}/v1.0/doc/workbooks/{TEST_WORKBOOK_ID}/sheets/{sheet_id}/insertRows",
        headers=api_headers,
        json={"row": 1, "rowCount": 2},
        timeout=15,
    )
    assert resp.status_code in (200, 204), resp.text


def test_delete_rows(api_headers):
    """删除第 2 行起的 1 行（先插入再删除，保持数据不变）"""
    _skip_if_readonly()
    sheet_id = _first_sheet_id(api_headers)

    # 先插入 1 行，再删除它
    ins_resp = requests.post(
        f"{BASE}/v1.0/doc/workbooks/{TEST_WORKBOOK_ID}/sheets/{sheet_id}/insertRows",
        headers=api_headers,
        json={"row": 1, "rowCount": 1},
        timeout=15,
    )
    assert ins_resp.status_code in (200, 204), ins_resp.text

    del_resp = requests.delete(
        f"{BASE}/v1.0/doc/workbooks/{TEST_WORKBOOK_ID}/sheets/{sheet_id}/rows/1",
        headers=api_headers,
        json={"rowCount": 1},
        timeout=15,
    )
    assert del_resp.status_code in (200, 204), del_resp.text


def test_hide_and_show_row(api_headers):
    """隐藏第 3 行后再显示，验证两次 PUT 均成功"""
    _skip_if_readonly()
    sheet_id = _first_sheet_id(api_headers)

    # 隐藏
    hide_resp = requests.put(
        f"{BASE}/v1.0/doc/workbooks/{TEST_WORKBOOK_ID}/sheets/{sheet_id}/rows/2/visibility",
        headers=api_headers,
        json={"hidden": True, "count": 1},
        timeout=15,
    )
    assert hide_resp.status_code in (200, 204), hide_resp.text

    # 显示
    show_resp = requests.put(
        f"{BASE}/v1.0/doc/workbooks/{TEST_WORKBOOK_ID}/sheets/{sheet_id}/rows/2/visibility",
        headers=api_headers,
        json={"hidden": False, "count": 1},
        timeout=15,
    )
    assert show_resp.status_code in (200, 204), show_resp.text


# ── 列操作 ─────────────────────────────────────────────────────────────


def test_insert_columns(api_headers):
    """在第 2 列（index=1）左侧插入 1 列，验证接口响应正常"""
    _skip_if_readonly()
    sheet_id = _first_sheet_id(api_headers)

    resp = requests.post(
        f"{BASE}/v1.0/doc/workbooks/{TEST_WORKBOOK_ID}/sheets/{sheet_id}/insertColumns",
        headers=api_headers,
        json={"column": 1, "columnCount": 1},
        timeout=15,
    )
    assert resp.status_code in (200, 204), resp.text


def test_delete_columns(api_headers):
    """插入 1 列后立即删除，保持工作表结构不变"""
    _skip_if_readonly()
    sheet_id = _first_sheet_id(api_headers)

    # 先插入
    ins_resp = requests.post(
        f"{BASE}/v1.0/doc/workbooks/{TEST_WORKBOOK_ID}/sheets/{sheet_id}/insertColumns",
        headers=api_headers,
        json={"column": 1, "columnCount": 1},
        timeout=15,
    )
    assert ins_resp.status_code in (200, 204), ins_resp.text

    # 再删除
    del_resp = requests.delete(
        f"{BASE}/v1.0/doc/workbooks/{TEST_WORKBOOK_ID}/sheets/{sheet_id}/columns/1",
        headers=api_headers,
        json={"columnCount": 1},
        timeout=15,
    )
    assert del_resp.status_code in (200, 204), del_resp.text


def test_hide_and_show_column(api_headers):
    """隐藏第 2 列后再显示"""
    _skip_if_readonly()
    sheet_id = _first_sheet_id(api_headers)

    # 隐藏
    hide_resp = requests.put(
        f"{BASE}/v1.0/doc/workbooks/{TEST_WORKBOOK_ID}/sheets/{sheet_id}/columns/1/visibility",
        headers=api_headers,
        json={"hidden": True, "count": 1},
        timeout=15,
    )
    assert hide_resp.status_code in (200, 204), hide_resp.text

    # 显示
    show_resp = requests.put(
        f"{BASE}/v1.0/doc/workbooks/{TEST_WORKBOOK_ID}/sheets/{sheet_id}/columns/1/visibility",
        headers=api_headers,
        json={"hidden": False, "count": 1},
        timeout=15,
    )
    assert show_resp.status_code in (200, 204), show_resp.text
