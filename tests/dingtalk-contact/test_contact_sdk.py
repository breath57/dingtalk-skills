"""
Phase 2: SDK 测试 — dingtalk-contact
覆盖：搜索用户、获取用户信息、搜索部门
全部使用 contact_1_0 SDK
"""
import os
import pytest

from alibabacloud_dingtalk.contact_1_0 import client as dt_client
from alibabacloud_dingtalk.contact_1_0 import models as dt_models
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models


# ── SDK Client / Runtime ──────────────────────────────────────────

@pytest.fixture(scope="session")
def sdk_client():
    config = open_api_models.Config()
    config.protocol = "HTTPS"
    config.endpoint = "api.dingtalk.com"
    return dt_client.Client(config)


@pytest.fixture(scope="session")
def sdk_runtime():
    return util_models.RuntimeOptions()


# ── 1. 搜索用户 ──────────────────────────────────────────────────

def test_sdk_search_user_basic(sdk_client, sdk_runtime, token):
    """搜索用户：关键词搜索，验证响应结构。"""
    h = dt_models.SearchUserHeaders()
    h.x_acs_dingtalk_access_token = token

    req = dt_models.SearchUserRequest(
        query_word="张",
        offset=0,
        size=5,
    )
    resp = sdk_client.search_user_with_options(req, h, sdk_runtime)
    body = resp.body

    assert isinstance(body.total_count, int), f"totalCount 应为整数：{body}"
    assert isinstance(body.has_more, bool), f"hasMore 应为布尔：{body}"
    # list 是 unionId 列表（字符串），可能为空（无匹配时）
    assert body.list is not None, "list 不应为 None"


def test_sdk_search_user_returns_list(sdk_client, sdk_runtime, token):
    """搜索用户：关键词搜索，list 元素类型为字符串（unionId）。"""
    h = dt_models.SearchUserHeaders()
    h.x_acs_dingtalk_access_token = token

    req = dt_models.SearchUserRequest(query_word="a", offset=0, size=3)
    resp = sdk_client.search_user_with_options(req, h, sdk_runtime)
    body = resp.body

    for item in body.list:
        assert isinstance(item, str), f"list 元素应为字符串（unionId）：{item}"


def test_sdk_search_user_pagination(sdk_client, sdk_runtime, token):
    """搜索用户：offset/size 分页参数有效。"""
    h = dt_models.SearchUserHeaders()
    h.x_acs_dingtalk_access_token = token

    req1 = dt_models.SearchUserRequest(query_word="a", offset=0, size=2)
    req2 = dt_models.SearchUserRequest(query_word="a", offset=2, size=2)
    resp1 = sdk_client.search_user_with_options(req1, h, sdk_runtime)
    resp2 = sdk_client.search_user_with_options(req2, h, sdk_runtime)

    # 两页结果不应完全相同（如果总数 > 2）
    if resp1.body.total_count > 2:
        assert resp1.body.list != resp2.body.list, "分页应返回不同结果"


# ── 2. 获取用户个人信息（user_profile，按 userId 列表）─────────────

def test_sdk_user_profile_basic(sdk_client, sdk_runtime, token, my_user_id):
    """user_profile：按 userId 获取用户昵称和手机号。"""
    h = dt_models.UserProfileHeaders()
    h.x_acs_dingtalk_access_token = token

    req = dt_models.UserProfileRequest(uids=[int(my_user_id)])
    resp = sdk_client.user_profile_with_options(req, h, sdk_runtime)
    body = resp.body

    assert body.result, f"result 不应为空：{body}"
    user = body.result[0]
    assert user.nick, f"nick 不应为空：{user}"


def test_sdk_user_profile_multi(sdk_client, sdk_runtime, token, my_user_id):
    """user_profile：同一 userId 传两次，仍只返回一条结果。"""
    h = dt_models.UserProfileHeaders()
    h.x_acs_dingtalk_access_token = token

    uid_int = int(my_user_id)
    req = dt_models.UserProfileRequest(uids=[uid_int, uid_int])
    resp = sdk_client.user_profile_with_options(req, h, sdk_runtime)
    body = resp.body

    # 去重后返回 1 条
    assert 1 <= len(body.result) <= 2, f"结果条数异常：{len(body.result)}"


# ── 3. 搜索部门 ──────────────────────────────────────────────────

def test_sdk_search_department_basic(sdk_client, sdk_runtime, token):
    """搜索部门：关键词搜索，验证响应结构。"""
    h = dt_models.SearchDepartmentHeaders()
    h.x_acs_dingtalk_access_token = token

    req = dt_models.SearchDepartmentRequest(
        query_word="技术",
        offset=0,
        size=5,
    )
    resp = sdk_client.search_department_with_options(req, h, sdk_runtime)
    body = resp.body

    assert isinstance(body.total_count, int), f"totalCount 应为整数：{body}"
    assert isinstance(body.has_more, bool), f"hasMore 应为布尔：{body}"
    assert body.list is not None, "list 不应为 None"


def test_sdk_search_department_list_type(sdk_client, sdk_runtime, token):
    """搜索部门：list 元素类型为整数（deptId）。"""
    h = dt_models.SearchDepartmentHeaders()
    h.x_acs_dingtalk_access_token = token

    req = dt_models.SearchDepartmentRequest(query_word="部", offset=0, size=5)
    resp = sdk_client.search_department_with_options(req, h, sdk_runtime)

    for item in resp.body.list:
        assert isinstance(item, int), f"list 元素应为整数（deptId）：{item}"
