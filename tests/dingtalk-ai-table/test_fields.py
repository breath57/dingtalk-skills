"""
测试：字段（Field / Column）管理
API: /v1.0/notable/bases/{base_id}/sheets/{sheet_id}/fields[/{field_id}]
SDK: notable_1_0 - get_all_fields, create_field, update_field, delete_field

每个测试在 test_sheet 内创建并删除临时字段，不影响 "title" 字段。
"""
import requests
import pytest

BASE_URL = "https://api.dingtalk.com/v1.0/notable"


def _fields_url(base_id, sheet_id):
    return f"{BASE_URL}/bases/{base_id}/sheets/{sheet_id}/fields"


# ─── tests ────────────────────────────────────────────────────────────────


def test_get_all_fields(token, operator_id, base_id, api_headers, test_sheet):
    """
    GET /fields → {"value": [{id, name, type, ...}, ...]}
    验证：响应包含 value 列表，每项有 id、name、type；
    测试工作表初始含 "title" 文本字段。
    """
    sheet_id, field_name = test_sheet
    resp = requests.get(
        f"{_fields_url(base_id, sheet_id)}?operatorId={operator_id}",
        headers=api_headers,
        timeout=15,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "value" in data, f"响应缺少 'value'：{data}"
    fields = data["value"]
    assert isinstance(fields, list), "value 应为列表"
    assert len(fields) >= 1, "至少应有 1 个字段"

    for f in fields:
        assert "id" in f, f"字段缺少 'id'：{f}"
        assert "name" in f, f"字段缺少 'name'：{f}"
        assert "type" in f, f"字段缺少 'type'：{f}"

    names = {f["name"] for f in fields}
    assert field_name in names, f"未找到预期字段 '{field_name}'，实际：{names}"


def test_create_and_delete_field(token, operator_id, base_id, api_headers, test_sheet):
    """
    POST /fields 创建字段 → {id, name, type, property}
    DELETE /fields/{field_id} 删除字段 → {"success": true}
    验证：创建后字段出现在列表，删除后消失。
    """
    sheet_id, _ = test_sheet

    # Create a number field
    create_resp = requests.post(
        f"{_fields_url(base_id, sheet_id)}?operatorId={operator_id}",
        headers=api_headers,
        json={"name": "__pytest_number__", "type": "number"},
        timeout=15,
    )
    assert create_resp.status_code == 200, create_resp.text
    created = create_resp.json()
    assert "id" in created, f"创建响应缺少 'id'：{created}"
    assert created.get("name") == "__pytest_number__"
    assert created.get("type") == "number"
    field_id = created["id"]

    # Verify in list
    list_resp = requests.get(
        f"{_fields_url(base_id, sheet_id)}?operatorId={operator_id}",
        headers=api_headers,
        timeout=15,
    )
    field_ids = [f["id"] for f in list_resp.json().get("value", [])]
    assert field_id in field_ids, f"新字段 {field_id} 未出现在列表中"

    # Delete
    del_resp = requests.delete(
        f"{_fields_url(base_id, sheet_id)}/{field_id}?operatorId={operator_id}",
        headers={k: v for k, v in api_headers.items() if k != "Content-Type"},
        timeout=15,
    )
    assert del_resp.status_code == 200, del_resp.text
    assert del_resp.json().get("success") is True, f"删除未成功：{del_resp.text}"

    # Verify removed
    list_resp2 = requests.get(
        f"{_fields_url(base_id, sheet_id)}?operatorId={operator_id}",
        headers=api_headers,
        timeout=15,
    )
    field_ids2 = [f["id"] for f in list_resp2.json().get("value", [])]
    assert field_id not in field_ids2, "删除后字段仍出现在列表中"


def test_update_field(token, operator_id, base_id, api_headers, test_sheet):
    """
    PUT /fields/{field_id} 更新字段名 → {id, name, type}
    验证：更新后列表中字段名已变更。
    """
    sheet_id, _ = test_sheet

    # Create a field to update
    create_resp = requests.post(
        f"{_fields_url(base_id, sheet_id)}?operatorId={operator_id}",
        headers=api_headers,
        json={"name": "__pytest_before__", "type": "text"},
        timeout=15,
    )
    assert create_resp.status_code == 200, create_resp.text
    field_id = create_resp.json()["id"]

    # Update name
    upd_resp = requests.put(
        f"{_fields_url(base_id, sheet_id)}/{field_id}?operatorId={operator_id}",
        headers=api_headers,
        json={"name": "__pytest_after__"},
        timeout=15,
    )
    assert upd_resp.status_code == 200, upd_resp.text
    upd_data = upd_resp.json()
    # 响应只返回 {"id": "..."}, 通过列表验证名称已更新
    assert "id" in upd_data, f"更新响应缺少 'id'：{upd_data}"

    # Verify in list
    list_resp = requests.get(
        f"{_fields_url(base_id, sheet_id)}?operatorId={operator_id}",
        headers=api_headers,
        timeout=15,
    )
    names = {f["name"] for f in list_resp.json().get("value", [])}
    assert "__pytest_after__" in names, f"更新后字段名未出现在列表：{names}"

    # Cleanup
    requests.delete(
        f"{_fields_url(base_id, sheet_id)}/{field_id}?operatorId={operator_id}",
        headers={k: v for k, v in api_headers.items() if k != "Content-Type"},
        timeout=15,
    )
