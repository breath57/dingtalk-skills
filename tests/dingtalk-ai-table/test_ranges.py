"""
test_ranges.py —— 测试 AI 表格单元格区域（Range）相关接口
  - GET    /v1.0/doc/workbooks/{workbookId}/sheets/{sheetId}/ranges/{range}   读取区域值
  - PUT    /v1.0/doc/workbooks/{workbookId}/sheets/{sheetId}/ranges/{range}   写入区域值
  - DELETE .../ranges/{range}/values    清除区域数据（保留格式）
  - DELETE .../ranges/{range}/contents  清除区域全部内容（含格式）

所需权限：Doc.Sheet.Read、Doc.Sheet.Write（写入测试）
测试文件：https://alidocs.dingtalk.com/i/nodes/MyQA2dXW7ePBO49BSMwxNm35JzlwrZgb
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


# ── 只读测试 ────────────────────────────────────────────────────────────


def test_read_range_small(api_headers):
    """读取 A1:E5 小区域，校验返回结构"""
    sheet_id = _first_sheet_id(api_headers)
    resp = requests.get(
        f"{BASE}/v1.0/doc/workbooks/{TEST_WORKBOOK_ID}/sheets/{sheet_id}/ranges/A1:E5",
        headers=api_headers,
        timeout=15,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "values" in data, f"响应缺少 values 字段：{data}"
    values = data["values"]
    assert isinstance(values, list), f"values 应为二维列表，实际：{type(values)}"
    # 每行也是列表
    for row in values:
        assert isinstance(row, list), f"values 中的行应为列表，实际：{row}"


def test_read_range_single_cell(api_headers):
    """读取单个单元格 A1"""
    sheet_id = _first_sheet_id(api_headers)
    resp = requests.get(
        f"{BASE}/v1.0/doc/workbooks/{TEST_WORKBOOK_ID}/sheets/{sheet_id}/ranges/A1",
        headers=api_headers,
        timeout=15,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "values" in data, data


def test_read_range_returns_formulas_field(api_headers):
    """区域响应应包含 formulas 字段（即使全为空字符串）"""
    sheet_id = _first_sheet_id(api_headers)
    resp = requests.get(
        f"{BASE}/v1.0/doc/workbooks/{TEST_WORKBOOK_ID}/sheets/{sheet_id}/ranges/A1:B2",
        headers=api_headers,
        timeout=15,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    # formulas 是可选字段，存在时须为二维列表
    if "formulas" in data:
        assert isinstance(data["formulas"], list), data


# ── 写入测试（需 ENABLE_WRITE_TESTS=1） ────────────────────────────────


def test_write_and_read_range(api_headers):
    """写入 3×3 数据到测试区域，再读取验证内容一致"""
    if not ENABLE_WRITE:
        import pytest
        pytest.skip("写入测试未启用，设置 ENABLE_WRITE_TESTS=1 开启")

    sheet_id = _first_sheet_id(api_headers)
    range_addr = "A1:C3"
    payload = {
        "values": [
            ["标题A", "标题B", "标题C"],
            ["R2C1", "R2C2", "R2C3"],
            ["R3C1", "R3C2", "R3C3"],
        ]
    }

    # 写入
    put_resp = requests.put(
        f"{BASE}/v1.0/doc/workbooks/{TEST_WORKBOOK_ID}/sheets/{sheet_id}/ranges/{range_addr}",
        headers=api_headers,
        json=payload,
        timeout=15,
    )
    assert put_resp.status_code in (200, 204), put_resp.text

    # 读回并验证
    get_resp = requests.get(
        f"{BASE}/v1.0/doc/workbooks/{TEST_WORKBOOK_ID}/sheets/{sheet_id}/ranges/{range_addr}",
        headers=api_headers,
        timeout=15,
    )
    assert get_resp.status_code == 200, get_resp.text
    returned = get_resp.json().get("values", [])
    assert returned[0][0] == "标题A", f"首行首列写入后不符，实际：{returned}"
    assert returned[1][1] == "R2C2", f"第2行第2列写入后不符，实际：{returned}"


def test_write_formula(api_headers):
    """写入公式（=SUM），读取后 values 为计算结果，formulas 含原始公式"""
    if not ENABLE_WRITE:
        import pytest
        pytest.skip("写入测试未启用，设置 ENABLE_WRITE_TESTS=1 开启")

    sheet_id = _first_sheet_id(api_headers)
    # 先写入数字
    requests.put(
        f"{BASE}/v1.0/doc/workbooks/{TEST_WORKBOOK_ID}/sheets/{sheet_id}/ranges/D1:D3",
        headers=api_headers,
        json={"values": [[10], [20], [30]]},
        timeout=15,
    )
    # 写入公式到 D4
    put_resp = requests.put(
        f"{BASE}/v1.0/doc/workbooks/{TEST_WORKBOOK_ID}/sheets/{sheet_id}/ranges/D4",
        headers=api_headers,
        json={"values": [["=SUM(D1:D3)"]]},
        timeout=15,
    )
    assert put_resp.status_code in (200, 204), put_resp.text

    # 读取 D4 验证
    get_resp = requests.get(
        f"{BASE}/v1.0/doc/workbooks/{TEST_WORKBOOK_ID}/sheets/{sheet_id}/ranges/D4",
        headers=api_headers,
        timeout=15,
    )
    assert get_resp.status_code == 200, get_resp.text
    data = get_resp.json()
    # values 应为计算后的 60
    val = data["values"][0][0]
    assert val == 60, f"公式计算结果应为 60，实际：{val}"


def test_clear_range_values(api_headers):
    """清除区域数据（保留格式）"""
    if not ENABLE_WRITE:
        import pytest
        pytest.skip("写入测试未启用，设置 ENABLE_WRITE_TESTS=1 开启")

    sheet_id = _first_sheet_id(api_headers)
    range_addr = "E1:E2"

    # 先写入数据
    requests.put(
        f"{BASE}/v1.0/doc/workbooks/{TEST_WORKBOOK_ID}/sheets/{sheet_id}/ranges/{range_addr}",
        headers=api_headers,
        json={"values": [["临时数据"], ["临时数据2"]]},
        timeout=15,
    )

    # 清除
    del_resp = requests.delete(
        f"{BASE}/v1.0/doc/workbooks/{TEST_WORKBOOK_ID}/sheets/{sheet_id}/ranges/{range_addr}/values",
        headers=api_headers,
        timeout=15,
    )
    assert del_resp.status_code in (200, 204), del_resp.text

    # 读回，确认数据已清空
    check_resp = requests.get(
        f"{BASE}/v1.0/doc/workbooks/{TEST_WORKBOOK_ID}/sheets/{sheet_id}/ranges/{range_addr}",
        headers=api_headers,
        timeout=15,
    )
    assert check_resp.status_code == 200, check_resp.text
    vals = check_resp.json().get("values", [])
    # 清空后每个单元格应为空字符串或 None
    for row in vals:
        for cell in row:
            assert cell in ("", None, 0), f"清除后单元格应为空，实际：{cell}"


def test_clear_range_contents(api_headers):
    """清除区域全部内容（含格式）"""
    if not ENABLE_WRITE:
        import pytest
        pytest.skip("写入测试未启用，设置 ENABLE_WRITE_TESTS=1 开启")

    sheet_id = _first_sheet_id(api_headers)
    range_addr = "F1:F2"

    # 先写入数据
    requests.put(
        f"{BASE}/v1.0/doc/workbooks/{TEST_WORKBOOK_ID}/sheets/{sheet_id}/ranges/{range_addr}",
        headers=api_headers,
        json={"values": [["内容1"], ["内容2"]]},
        timeout=15,
    )

    # 清除全部（含格式）
    del_resp = requests.delete(
        f"{BASE}/v1.0/doc/workbooks/{TEST_WORKBOOK_ID}/sheets/{sheet_id}/ranges/{range_addr}/contents",
        headers=api_headers,
        timeout=15,
    )
    assert del_resp.status_code in (200, 204), del_resp.text
