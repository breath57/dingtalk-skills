"""
测试：记录（Record）增删改查
API: /v1.0/notable/bases/{base_id}/sheets/{sheet_id}/records[/list|/delete]
SDK: notable_1_0 - insert_records, list_records, update_records, delete_records

每个测试独立完成完整生命周期（插入→操作→删除），互不依赖。
"""
import requests
import pytest

BASE_URL = "https://api.dingtalk.com/v1.0/notable"


def _records_url(base_id, sheet_id):
    return f"{BASE_URL}/bases/{base_id}/sheets/{sheet_id}/records"


def _insert(base_id, sheet_id, operator_id, headers, records):
    """辅助：插入 records，返回 response JSON。"""
    resp = requests.post(
        f"{_records_url(base_id, sheet_id)}?operatorId={operator_id}",
        headers=headers,
        json={"records": records},
        timeout=15,
    )
    assert resp.status_code == 200, f"insert failed: {resp.text}"
    return resp.json()


def _list(base_id, sheet_id, operator_id, headers, max_results=20):
    """辅助：列举记录，返回 records list。"""
    resp = requests.post(
        f"{_records_url(base_id, sheet_id)}/list?operatorId={operator_id}",
        headers=headers,
        json={"maxResults": max_results},
        timeout=15,
    )
    assert resp.status_code == 200, f"list failed: {resp.text}"
    return resp.json().get("records", [])


def _delete_all(base_id, sheet_id, operator_id, headers):
    """辅助：删除工作表内所有记录（清理用）。"""
    records = _list(base_id, sheet_id, operator_id, headers, max_results=100)
    if not records:
        return
    ids = [r["id"] for r in records]
    resp = requests.post(
        f"{_records_url(base_id, sheet_id)}/delete?operatorId={operator_id}",
        headers=headers,
        json={"recordIds": ids},
        timeout=15,
    )
    assert resp.status_code == 200, f"cleanup delete failed: {resp.text}"


# ─── tests ────────────────────────────────────────────────────────────────


def test_insert_records(token, operator_id, base_id, api_headers, test_sheet):
    """
    POST /records → {"value": [{"id": "..."}, ...]}
    验证：响应包含 value 列表，每项有 id；插入数量与请求一致。
    """
    sheet_id, field = test_sheet
    _delete_all(base_id, sheet_id, operator_id, api_headers)  # ensure clean

    result = _insert(base_id, sheet_id, operator_id, api_headers, [
        {"fields": {field: "row A"}},
        {"fields": {field: "row B"}},
    ])
    assert "value" in result, f"响应缺少 'value'：{result}"
    ids = result["value"]
    assert len(ids) == 2, f"期望插入 2 条，实际：{ids}"
    for item in ids:
        assert "id" in item, f"记录项缺少 'id'：{item}"

    # Cleanup
    _delete_all(base_id, sheet_id, operator_id, api_headers)


def test_list_records(token, operator_id, base_id, api_headers, test_sheet):
    """
    POST /records/list → {"records": [...], "hasMore": false}
    验证：字段值写入后可读回。
    """
    sheet_id, field = test_sheet
    _delete_all(base_id, sheet_id, operator_id, api_headers)

    _insert(base_id, sheet_id, operator_id, api_headers, [
        {"fields": {field: "hello"}},
        {"fields": {field: "world"}},
    ])

    records = _list(base_id, sheet_id, operator_id, api_headers)
    assert len(records) == 2, f"期望 2 条记录，实际：{len(records)}"

    values = {r["fields"].get(field) for r in records}
    assert "hello" in values and "world" in values, f"写入值未读回：{values}"

    for r in records:
        assert "id" in r
        assert "fields" in r
        assert "createdTime" in r

    # Cleanup
    _delete_all(base_id, sheet_id, operator_id, api_headers)


def test_update_record(token, operator_id, base_id, api_headers, test_sheet):
    """
    PUT /records → {"value": [{"id": "..."}]}
    验证：更新后读回字段值已变更。
    """
    sheet_id, field = test_sheet
    _delete_all(base_id, sheet_id, operator_id, api_headers)

    insert_result = _insert(base_id, sheet_id, operator_id, api_headers, [
        {"fields": {field: "original"}},
    ])
    record_id = insert_result["value"][0]["id"]

    # Update
    upd_resp = requests.put(
        f"{_records_url(base_id, sheet_id)}?operatorId={operator_id}",
        headers=api_headers,
        json={"records": [{"id": record_id, "fields": {field: "updated"}}]},
        timeout=15,
    )
    assert upd_resp.status_code == 200, upd_resp.text
    upd_data = upd_resp.json()
    assert "value" in upd_data, f"更新响应缺少 'value'：{upd_data}"
    assert upd_data["value"][0]["id"] == record_id

    # Verify updated value
    records = _list(base_id, sheet_id, operator_id, api_headers)
    values = {r["fields"].get(field) for r in records}
    assert "updated" in values, f"更新后值未读回：{values}"
    assert "original" not in values, f"旧值未被替换：{values}"

    # Cleanup
    _delete_all(base_id, sheet_id, operator_id, api_headers)


def test_delete_records(token, operator_id, base_id, api_headers, test_sheet):
    """
    POST /records/delete → {"success": true}
    验证：删除后列表为空。
    """
    sheet_id, field = test_sheet
    _delete_all(base_id, sheet_id, operator_id, api_headers)

    insert_result = _insert(base_id, sheet_id, operator_id, api_headers, [
        {"fields": {field: "to delete 1"}},
        {"fields": {field: "to delete 2"}},
    ])
    ids = [v["id"] for v in insert_result["value"]]

    del_resp = requests.post(
        f"{_records_url(base_id, sheet_id)}/delete?operatorId={operator_id}",
        headers=api_headers,
        json={"recordIds": ids},
        timeout=15,
    )
    assert del_resp.status_code == 200, del_resp.text
    del_data = del_resp.json()
    assert del_data.get("success") is True, f"删除未返回 success=true：{del_data}"

    # Verify empty
    remaining = _list(base_id, sheet_id, operator_id, api_headers)
    assert len(remaining) == 0, f"删除后仍有记录：{remaining}"
