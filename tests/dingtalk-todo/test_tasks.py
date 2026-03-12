"""
阶段二：纯 HTTP 请求版测试 — 使用 requests 直接调用 REST API
不依赖任何 DingTalk SDK，验证接口的 HTTP 行为。

覆盖：创建 → 获取详情 → 列表查询 → 更新 → 标记完成 → 删除
响应字段说明（已通过实际调用验证）：
  - 创建：返回完整任务对象，id 字段为任务 ID
  - 获取：返回完整任务对象，含 id / subject / done 等
  - 更新：返回 {requestId, result: True}
  - 删除：返回 {requestId, result: True}；删后 GET 返回 400
  - 列表：返回 {todoCards: [...], nextToken}；需 Todo.Todo.Read 权限

所需权限：
  - Todo.Todo.Write  (创建/更新/删除)
  - Todo.Todo.Read (列表查询，缺失时自动 skip)
"""
import time
import pytest
import requests

BASE_URL = "https://api.dingtalk.com"
TODO_BASE = f"{BASE_URL}/v1.0/todo/users"


# ─── 辅助函数 ─────────────────────────────────────────────────────────────────

def _create(union_id: str, headers: dict, subject: str, **kwargs) -> dict:
    """创建待办，返回响应 JSON（含 id 字段）。"""
    resp = requests.post(
        f"{TODO_BASE}/{union_id}/tasks",
        params={"operatorId": union_id},
        headers=headers,
        json={"subject": subject, **kwargs},
        timeout=15,
    )
    assert resp.status_code == 200, f"创建失败 status={resp.status_code}：{resp.text}"
    data = resp.json()
    assert "id" in data, f"响应缺少 'id' 字段：{data}"
    return data


def _delete(union_id: str, headers: dict, task_id: str) -> dict:
    """删除待办，返回响应 JSON（含 result: True）。"""
    resp = requests.delete(
        f"{TODO_BASE}/{union_id}/tasks/{task_id}",
        params={"operatorId": union_id},
        headers=headers,
        timeout=15,
    )
    assert resp.status_code == 200, f"删除失败 status={resp.status_code}：{resp.text}"
    return resp.json()


def _try_list(union_id: str, headers: dict, is_done: bool = False) -> requests.Response:
    """查询列表，返回 Response（调用方自行处理 403 skip）。"""
    return requests.post(
        f"{TODO_BASE}/{union_id}/tasks/list",
        params={"operatorId": union_id},
        headers=headers,
        json={"isDone": is_done},
        timeout=15,
    )


# ─── 共享测试任务 fixture ──────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def http_shared_task(union_id, api_headers):
    """Session 级共享任务，测试结束后自动删除。"""
    data = _create(union_id, api_headers,
                   subject=f"[http-shared] 共享测试 {time.strftime('%Y%m%d%H%M%S')}")
    task_id = data["id"]
    yield task_id
    _delete(union_id, api_headers, task_id)


# ─── 创建 ─────────────────────────────────────────────────────────────────────

def test_http_create_basic(union_id, api_headers):
    """POST /tasks 只传 subject → 返回含有效 id 的完整任务对象。"""
    task_id = None
    try:
        data = _create(union_id, api_headers, f"[http] 基础创建 {time.strftime('%H:%M:%S')}")
        task_id = data["id"]
        assert isinstance(task_id, str) and len(task_id) > 0
        assert data.get("subject") is not None
        assert data.get("done") is False
    finally:
        if task_id:
            _delete(union_id, api_headers, task_id)


def test_http_create_with_description_and_duetime(union_id, api_headers):
    """POST /tasks 含 description + dueTime → 返回有效 id。"""
    task_id = None
    try:
        due_ms = (int(time.time()) + 86400) * 1000
        data = _create(union_id, api_headers,
                       f"[http] 含描述截止时间 {time.strftime('%H:%M:%S')}",
                       description="自动化测试待办", dueTime=due_ms)
        task_id = data["id"]
        assert task_id
    finally:
        if task_id:
            _delete(union_id, api_headers, task_id)


def test_http_create_with_priority(union_id, api_headers):
    """POST /tasks 含 priority=10 → 返回有效 id。"""
    task_id = None
    try:
        data = _create(union_id, api_headers,
                       f"[http] 高优先级 {time.strftime('%H:%M:%S')}", priority=10)
        task_id = data["id"]
        assert task_id
    finally:
        if task_id:
            _delete(union_id, api_headers, task_id)


# ─── 获取详情 ─────────────────────────────────────────────────────────────────

def test_http_get_task(union_id, api_headers, http_shared_task):
    """GET /tasks/{id} → 返回详情，id / subject 字段存在且值匹配。"""
    resp = requests.get(
        f"{TODO_BASE}/{union_id}/tasks/{http_shared_task}",
        headers=api_headers, timeout=15,
    )
    assert resp.status_code == 200, f"GET 失败：{resp.text}"
    data = resp.json()
    assert data.get("id") == http_shared_task, f"id 不匹配：{data.get('id')}"
    assert "subject" in data


# ─── 列表查询（需 Todo.Todo.Read） ──────────────────────────────────────────

def test_http_list_undone(union_id, api_headers, http_shared_task):
    """POST /tasks/list isDone=false → 含 http_shared_task；缺权时 skip。"""
    resp = _try_list(union_id, api_headers, is_done=False)
    if resp.status_code == 403:
        pytest.skip(f"缺少 Todo.Todo.Read / Custom.Todo.Read 权限 → {resp.json().get('message','')[:120]}")
    assert resp.status_code == 200, f"列表查询失败：{resp.text}"
    data = resp.json()
    assert "todoCards" in data, f"响应缺少 todoCards：{data}"
    ids = [c.get("id") or c.get("taskId") for c in data["todoCards"]]
    assert http_shared_task in ids, f"shared_task 不在列表中；前10: {ids[:10]}"


def test_http_list_done(union_id, api_headers):
    """POST /tasks/list isDone=true → 响应含 todoCards；缺权时 skip。"""
    resp = _try_list(union_id, api_headers, is_done=True)
    if resp.status_code == 403:
        pytest.skip("缺少 Todo.Todo.Read / Custom.Todo.Read 权限")
    assert resp.status_code == 200, f"查询已完成列表失败：{resp.text}"
    assert "todoCards" in resp.json()


# ─── 更新 ─────────────────────────────────────────────────────────────────────

def test_http_update_subject(union_id, api_headers):
    """PUT /tasks/{id} 更新 subject → result=True，GET 验证新标题。"""
    task_id = None
    try:
        data = _create(union_id, api_headers, f"[http] 待更新 {time.strftime('%H:%M:%S')}")
        task_id = data["id"]
        new_subject = f"[http] 已更新 {time.strftime('%H:%M:%S')}"

        upd = requests.put(
            f"{TODO_BASE}/{union_id}/tasks/{task_id}",
            params={"operatorId": union_id}, headers=api_headers,
            json={"subject": new_subject}, timeout=15,
        )
        assert upd.status_code == 200, f"更新失败：{upd.text}"
        assert upd.json().get("result") is True, f"result 非 True：{upd.json()}"

        got = requests.get(f"{TODO_BASE}/{union_id}/tasks/{task_id}",
                           headers=api_headers, timeout=15)
        assert got.json().get("subject") == new_subject, f"标题未更新：{got.json().get('subject')}"
    finally:
        if task_id:
            _delete(union_id, api_headers, task_id)


def test_http_mark_done(union_id, api_headers):
    """PUT /tasks/{id} done=True → result=True，GET 验证 done=True。"""
    task_id = None
    try:
        data = _create(union_id, api_headers, f"[http] 待完成 {time.strftime('%H:%M:%S')}")
        task_id = data["id"]

        upd = requests.put(
            f"{TODO_BASE}/{union_id}/tasks/{task_id}",
            params={"operatorId": union_id}, headers=api_headers,
            json={"done": True}, timeout=15,
        )
        assert upd.status_code == 200, f"标记完成失败：{upd.text}"
        assert upd.json().get("result") is True

        got = requests.get(f"{TODO_BASE}/{union_id}/tasks/{task_id}",
                           headers=api_headers, timeout=15)
        assert got.json().get("done") is True, f"done 未变为 True：{got.json()}"
    finally:
        if task_id:
            _delete(union_id, api_headers, task_id)


# ─── 删除 ─────────────────────────────────────────────────────────────────────

def test_http_delete_task(union_id, api_headers):
    """DELETE /tasks/{id} → result=True，再 GET 返回 400（task not exist）。"""
    data = _create(union_id, api_headers, f"[http] 待删除 {time.strftime('%H:%M:%S')}")
    task_id = data["id"]
    # 删除本身是被测操作，不加 finally（删除成功后无需二次清理）
    del_data = _delete(union_id, api_headers, task_id)
    assert del_data.get("result") is True, f"删除 result 非 True：{del_data}"

    got = requests.get(f"{TODO_BASE}/{union_id}/tasks/{task_id}",
                       headers=api_headers, timeout=15)
    assert got.status_code == 400, f"预期 400，实际 {got.status_code}，body: {got.text}"
    assert "not exist" in got.text.lower() or "paramError" in got.text
