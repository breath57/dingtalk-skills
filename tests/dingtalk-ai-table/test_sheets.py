"""
测试：工作表（Sheet）管理
API: /v1.0/notable/bases/{base_id}/sheets[/{sheet_id}]
SDK: notable_1_0 - get_all_sheets, get_sheet, create_sheet, delete_sheet
"""
import requests
import pytest

BASE_URL = "https://api.dingtalk.com/v1.0/notable"


def test_list_sheets(token, operator_id, base_id, api_headers):
    """GET /sheets → value 列表，每项有 id 和 name"""
    resp = requests.get(
        f"{BASE_URL}/bases/{base_id}/sheets?operatorId={operator_id}",
        headers=api_headers,
        timeout=15,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "value" in data, f"响应缺少 'value' 字段：{data}"
    sheets = data["value"]
    assert isinstance(sheets, list), "value 应为列表"
    assert len(sheets) > 0, "工作表列表不应为空"
    for sheet in sheets:
        assert "id" in sheet, f"工作表缺少 'id'：{sheet}"
        assert "name" in sheet, f"工作表缺少 'name'：{sheet}"


def test_get_sheet(token, operator_id, base_id, api_headers, test_sheet):
    """GET /sheets/{sheet_id} → 返回 id 和 name"""
    sheet_id, _ = test_sheet
    resp = requests.get(
        f"{BASE_URL}/bases/{base_id}/sheets/{sheet_id}?operatorId={operator_id}",
        headers=api_headers,
        timeout=15,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("id") == sheet_id, f"返回的 id 不匹配：{data}"
    assert "name" in data, f"响应缺少 'name'：{data}"


def test_create_and_delete_sheet(token, operator_id, base_id, api_headers):
    """POST /sheets 创建，验证存在，DELETE 删除，验证不再存在"""
    # Create
    create_resp = requests.post(
        f"{BASE_URL}/bases/{base_id}/sheets?operatorId={operator_id}",
        headers=api_headers,
        json={"name": "__pytest_create_delete__", "fields": [{"name": "col1", "type": "text"}]},
        timeout=15,
    )
    assert create_resp.status_code == 200, create_resp.text
    created = create_resp.json()
    assert "id" in created, f"创建响应缺少 'id'：{created}"
    assert created.get("name") == "__pytest_create_delete__"
    new_id = created["id"]

    # Verify in list
    list_resp = requests.get(
        f"{BASE_URL}/bases/{base_id}/sheets?operatorId={operator_id}",
        headers=api_headers,
        timeout=15,
    )
    ids = [s["id"] for s in list_resp.json().get("value", [])]
    assert new_id in ids, f"新创建的工作表 {new_id} 未出现在列表中"

    # Delete
    del_resp = requests.delete(
        f"{BASE_URL}/bases/{base_id}/sheets/{new_id}?operatorId={operator_id}",
        headers={k: v for k, v in api_headers.items() if k != "Content-Type"},
        timeout=15,
    )
    assert del_resp.status_code == 200, del_resp.text
    assert del_resp.json().get("success") is True, f"删除未成功：{del_resp.text}"

    # Verify removed
    list_resp2 = requests.get(
        f"{BASE_URL}/bases/{base_id}/sheets?operatorId={operator_id}",
        headers=api_headers,
        timeout=15,
    )
    ids2 = [s["id"] for s in list_resp2.json().get("value", [])]
    assert new_id not in ids2, "删除后工作表仍出现在列表中"
