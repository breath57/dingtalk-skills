"""
阶段一：SDK 版测试 — 使用 alibabacloud_dingtalk 官方 SDK 直接调用
SDK 模块：todo_1_0
配置：config.protocol='HTTPS', config.endpoint='api.dingtalk.com'

覆盖：创建 → 获取详情 → 列表查询 → 更新 → 标记完成 → 删除
所需权限：
  - Todo.Todo.Write  (创建/更新/删除)
  - Todo.Todo.Read (列表查询，如未授权则自动 skip)
"""
import time
import pytest
import requests

from alibabacloud_dingtalk.todo_1_0 import client as todo_client, models as todo_models
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models

BASE_URL = "https://api.dingtalk.com"


# ─── SDK client fixture ──────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def sdk_client():
    config = open_api_models.Config()
    config.protocol = "HTTPS"
    config.endpoint = "api.dingtalk.com"
    return todo_client.Client(config)


@pytest.fixture(scope="session")
def sdk_runtime():
    return util_models.RuntimeOptions()


@pytest.fixture(scope="session")
def sdk_token(token):
    """复用全局 token fixture。"""
    return token


# ─── 辅助函数 ─────────────────────────────────────────────────────────────────

def _sdk_create(sdk_client, sdk_runtime, token, union_id, subject, **kwargs):
    h = todo_models.CreateTodoTaskHeaders()
    h.x_acs_dingtalk_access_token = token
    req = todo_models.CreateTodoTaskRequest(
        subject=subject,
        operator_id=union_id,
        **kwargs,
    )
    resp = sdk_client.create_todo_task_with_options(union_id, req, h, sdk_runtime)
    return resp.body


def _sdk_delete(sdk_client, sdk_runtime, token, union_id, task_id):
    h = todo_models.DeleteTodoTaskHeaders()
    h.x_acs_dingtalk_access_token = token
    req = todo_models.DeleteTodoTaskRequest(operator_id=union_id)
    resp = sdk_client.delete_todo_task_with_options(union_id, task_id, req, h, sdk_runtime)
    return resp.body


# ─── 共享测试任务 fixture ──────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def sdk_shared_task(sdk_client, sdk_runtime, sdk_token, union_id):
    """Session 级共享任务，测试结束后自动删除。"""
    body = _sdk_create(
        sdk_client, sdk_runtime, sdk_token, union_id,
        subject=f"[sdk-shared] 共享测试 {time.strftime('%Y%m%d%H%M%S')}",
    )
    task_id = body.id
    assert task_id, f"SDK 共享任务创建失败，无 id"
    yield task_id
    _sdk_delete(sdk_client, sdk_runtime, sdk_token, union_id, task_id)


# ─── 创建 ─────────────────────────────────────────────────────────────────────

def test_sdk_create_basic(sdk_client, sdk_runtime, sdk_token, union_id):
    """SDK 最简创建：只传 subject → 返回有效 id。"""
    task_id = None
    try:
        body = _sdk_create(sdk_client, sdk_runtime, sdk_token, union_id,
                           subject=f"[sdk] 基础创建 {time.strftime('%H:%M:%S')}")
        task_id = body.id
        assert task_id, f"SDK 创建无 id，resp: {body}"
        assert body.subject is not None
        assert body.done is False
    finally:
        if task_id:
            _sdk_delete(sdk_client, sdk_runtime, sdk_token, union_id, task_id)


def test_sdk_create_with_due_time(sdk_client, sdk_runtime, sdk_token, union_id):
    """SDK 创建含 due_time → 返回有效 id。"""
    task_id = None
    try:
        due_ms = (int(time.time()) + 86400) * 1000
        body = _sdk_create(sdk_client, sdk_runtime, sdk_token, union_id,
                           subject=f"[sdk] 含截止时间 {time.strftime('%H:%M:%S')}",
                           due_time=due_ms)
        task_id = body.id
        assert task_id
    finally:
        if task_id:
            _sdk_delete(sdk_client, sdk_runtime, sdk_token, union_id, task_id)


# ─── 获取详情 ─────────────────────────────────────────────────────────────────

def test_sdk_get_task(sdk_client, sdk_runtime, sdk_token, union_id, sdk_shared_task):
    """SDK GET /tasks/{id} → 返回详情，id 与请求一致。"""
    h = todo_models.GetTodoTaskHeaders()
    h.x_acs_dingtalk_access_token = sdk_token
    resp = sdk_client.get_todo_task_with_options(union_id, sdk_shared_task, h, sdk_runtime)
    task = resp.body
    assert task.id == sdk_shared_task, f"id 不匹配：{task.id}"
    assert task.subject is not None


# ─── 列表查询（需 Todo.Todo.Read） ──────────────────────────────────────────

def test_sdk_list_undone(sdk_client, sdk_runtime, sdk_token, union_id, sdk_shared_task):
    """SDK 查询未完成列表，含 sdk_shared_task；缺 Todo.Todo.Read 时自动 skip。"""
    h = todo_models.QueryTodoTasksHeaders()
    h.x_acs_dingtalk_access_token = sdk_token
    req = todo_models.QueryTodoTasksRequest(is_done=False)
    try:
        resp = sdk_client.query_todo_tasks_with_options(union_id, req, h, sdk_runtime)
    except Exception as e:
        if "Todo.Todo.Read" in str(e) or "Custom.Todo.Read" in str(e) or "Forbidden" in str(e):
            pytest.skip("缺少 Todo.Todo.Read / Custom.Todo.Read 权限，跳过列表查询测试")
        raise
    cards = resp.body.todo_cards or []
    ids = [c.task_id for c in cards]
    assert sdk_shared_task in ids, f"shared_task 不在列表中；前10: {ids[:10]}"


# ─── 更新 ─────────────────────────────────────────────────────────────────────

def test_sdk_update_subject(sdk_client, sdk_runtime, sdk_token, union_id):
    """SDK PUT 更新 subject → result=True，GET 验证新标题。"""
    task_id = None
    try:
        body = _sdk_create(sdk_client, sdk_runtime, sdk_token, union_id,
                           subject=f"[sdk] 待更新 {time.strftime('%H:%M:%S')}")
        task_id = body.id
        new_subject = f"[sdk] 已更新 {time.strftime('%H:%M:%S')}"

        h = todo_models.UpdateTodoTaskHeaders()
        h.x_acs_dingtalk_access_token = sdk_token
        req = todo_models.UpdateTodoTaskRequest(subject=new_subject, operator_id=union_id)
        upd = sdk_client.update_todo_task_with_options(union_id, task_id, req, h, sdk_runtime)
        assert upd.body.result is True, f"更新 result 非 True：{upd.body}"

        gh = todo_models.GetTodoTaskHeaders()
        gh.x_acs_dingtalk_access_token = sdk_token
        get_resp = sdk_client.get_todo_task_with_options(union_id, task_id, gh, sdk_runtime)
        assert get_resp.body.subject == new_subject, f"标题未更新：{get_resp.body.subject}"
    finally:
        if task_id:
            _sdk_delete(sdk_client, sdk_runtime, sdk_token, union_id, task_id)


def test_sdk_mark_done(sdk_client, sdk_runtime, sdk_token, union_id):
    """SDK PUT done=True → GET 验证 done=True。"""
    task_id = None
    try:
        body = _sdk_create(sdk_client, sdk_runtime, sdk_token, union_id,
                           subject=f"[sdk] 待完成 {time.strftime('%H:%M:%S')}")
        task_id = body.id

        h = todo_models.UpdateTodoTaskHeaders()
        h.x_acs_dingtalk_access_token = sdk_token
        req = todo_models.UpdateTodoTaskRequest(done=True, operator_id=union_id)
        upd = sdk_client.update_todo_task_with_options(union_id, task_id, req, h, sdk_runtime)
        assert upd.body.result is True

        gh = todo_models.GetTodoTaskHeaders()
        gh.x_acs_dingtalk_access_token = sdk_token
        get_resp = sdk_client.get_todo_task_with_options(union_id, task_id, gh, sdk_runtime)
        assert get_resp.body.done is True, f"done 未变为 True：{get_resp.body.done}"
    finally:
        if task_id:
            _sdk_delete(sdk_client, sdk_runtime, sdk_token, union_id, task_id)


# ─── 删除 ─────────────────────────────────────────────────────────────────────

def test_sdk_delete_task(sdk_client, sdk_runtime, sdk_token, union_id):
    """SDK DELETE → result=True，GET 返回 400（任务不存在）。"""
    body = _sdk_create(sdk_client, sdk_runtime, sdk_token, union_id,
                       subject=f"[sdk] 待删除 {time.strftime('%H:%M:%S')}")
    task_id = body.id

    del_body = _sdk_delete(sdk_client, sdk_runtime, sdk_token, union_id, task_id)
    assert del_body.result is True, f"删除 result 非 True：{del_body}"

    # 验证已删除（SDK GET 应抛出异常）
    gh = todo_models.GetTodoTaskHeaders()
    gh.x_acs_dingtalk_access_token = sdk_token
    with pytest.raises(Exception) as exc_info:
        sdk_client.get_todo_task_with_options(union_id, task_id, gh, sdk_runtime)
    assert "not exist" in str(exc_info.value).lower() or "400" in str(exc_info.value), (
        f"删除后 GET 应报错，实际异常：{exc_info.value}"
    )
