"""
dingtalk-todo 测试专属 fixtures
  - union_id:  操作者 unionId（即 OPERATOR_ID）
  - shared_task: 会话级共享待办任务，测试结束后自动删除

API 基础路径：/v1.0/todo/users/{unionId}/tasks
认证方式：x-acs-dingtalk-access-token（新版 OAuth2）
"""
import os
import time
import pytest
import requests

BASE_URL = "https://api.dingtalk.com"
TODO_BASE = f"{BASE_URL}/v1.0/todo/users"


@pytest.fixture(scope="session")
def union_id(operator_id) -> str:
    """返回操作者 unionId（与 OPERATOR_ID 相同）。"""
    return operator_id


@pytest.fixture(scope="session")
def shared_task(union_id, api_headers):
    """
    Session 级共享待办任务，测试结束后自动删除。

    yields: task_id (str)
    """
    resp = requests.post(
        f"{TODO_BASE}/{union_id}/tasks",
        params={"operatorId": union_id},
        headers=api_headers,
        json={
            "subject": f"[pytest-shared] 共享测试待办 {time.strftime('%Y%m%d%H%M%S')}",
            "description": "由 pytest conftest 自动创建，测试结束后自动删除",
        },
        timeout=15,
    )
    assert resp.status_code == 200, f"创建共享待办失败：{resp.text}"
    data = resp.json()
    assert "id" in data, f"响应缺少 'id' 字段：{data}"
    task_id = data["id"]

    yield task_id

    # 清理
    requests.delete(
        f"{TODO_BASE}/{union_id}/tasks/{task_id}",
        params={"operatorId": union_id},
        headers=api_headers,
        timeout=15,
    )
