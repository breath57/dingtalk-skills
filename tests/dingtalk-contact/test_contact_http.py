"""
Phase 3: 纯 HTTP 测试 — dingtalk-contact
覆盖旧版 oapi.dingtalk.com 接口（无 SDK 封装）：
  - 用户详情（topapi/v2/user/get）
  - 部门成员列表（topapi/v2/user/list）
  - 部门 userId 列表（topapi/user/listid）
  - 部门详情（topapi/v2/department/get）
  - 子部门列表（topapi/v2/department/listsub）
  - 子部门 ID 列表（topapi/v2/department/listsubid）
以及两种 token 配合的完整链路：
  - search(name) → userId → user/get → 完整详情
  - search_dept(name) → deptId → dept/get + user/list
"""
import os
import pytest
import requests

OAPI_BASE = "https://oapi.dingtalk.com"
NEW_BASE  = "https://api.dingtalk.com"


@pytest.fixture(scope="session")
def old_token() -> str:
    app_key    = os.environ.get("DINGTALK_APP_KEY", "")
    app_secret = os.environ.get("DINGTALK_APP_SECRET", "")
    if not app_key or not app_secret:
        pytest.skip("缺少 DINGTALK_APP_KEY / DINGTALK_APP_SECRET")
    r = requests.get(f"{OAPI_BASE}/gettoken",
        params={"appkey": app_key, "appsecret": app_secret}, timeout=15)
    r.raise_for_status()
    t = r.json().get("access_token")
    assert t, f"未获取到旧版 access_token：{r.text}"
    return t


# ──────────────────────────────────────────────────────────────────
# 用户相关
# ──────────────────────────────────────────────────────────────────

def test_http_user_get_basic(old_token, my_user_id):
    """按 userId 获取完整用户信息。"""
    r = requests.post(f"{OAPI_BASE}/topapi/v2/user/get?access_token={old_token}",
        json={"userid": my_user_id}, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d.get("errcode") == 0, f"errcode 非 0：{d}"
    result = d["result"]
    assert result.get("name"),    f"缺少 name：{result}"
    assert result.get("userid"),  f"缺少 userid：{result}"
    assert result.get("unionid"), f"缺少 unionid：{result}"


def test_http_user_get_fields(old_token, my_user_id):
    """用户详情包含部门、职位等核心字段。"""
    r = requests.post(f"{OAPI_BASE}/topapi/v2/user/get?access_token={old_token}",
        json={"userid": my_user_id}, timeout=15)
    result = r.json()["result"]
    # 必须包含的字段
    for field in ["name", "userid", "unionid", "dept_id_list"]:
        assert field in result, f"响应缺少字段 {field}：{result}"
    assert isinstance(result["dept_id_list"], list)


def test_http_user_get_invalid_userid(old_token):
    """无效 userId 应返回非 0 errcode，不应 500。"""
    r = requests.post(f"{OAPI_BASE}/topapi/v2/user/get?access_token={old_token}",
        json={"userid": "__invalid_user__"}, timeout=15)
    assert r.status_code == 200
    assert r.json().get("errcode") != 0


# ──────────────────────────────────────────────────────────────────
# 部门相关
# ──────────────────────────────────────────────────────────────────

def test_http_dept_listsub(old_token):
    """获取根部门的直属子部门列表，含 dept_id 和 name。"""
    r = requests.post(f"{OAPI_BASE}/topapi/v2/department/listsub?access_token={old_token}",
        json={"dept_id": 1}, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d.get("errcode") == 0, f"errcode 非 0：{d}"
    dept_list = d["result"]
    assert len(dept_list) > 0, "根部门下应有子部门"
    for dept in dept_list:
        assert "dept_id" in dept, f"缺少 dept_id：{dept}"
        assert "name"    in dept, f"缺少 name：{dept}"


def test_http_dept_get_detail(old_token):
    """按 deptId 获取部门详情（名称、人数、parent_id）。"""
    # 先拿一个真实 deptId
    r0 = requests.post(f"{OAPI_BASE}/topapi/v2/department/listsub?access_token={old_token}",
        json={"dept_id": 1}, timeout=15)
    dept_id = r0.json()["result"][0]["dept_id"]

    r = requests.post(f"{OAPI_BASE}/topapi/v2/department/get?access_token={old_token}",
        json={"dept_id": dept_id, "language": "zh_CN"}, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d.get("errcode") == 0, f"errcode 非 0：{d}"
    result = d["result"]
    assert result.get("name"),      f"缺少 name：{result}"
    assert result.get("dept_id"),   f"缺少 dept_id：{result}"
    assert "parent_id" in result,   f"缺少 parent_id：{result}"
    assert "member_count" in result, f"缺少 member_count：{result}"


def test_http_dept_listsubid_recursive(old_token):
    """获取部门的所有子部门 ID 列表（递归）。"""
    # 用某个有子部门的部门 id
    r0 = requests.post(f"{OAPI_BASE}/topapi/v2/department/listsub?access_token={old_token}",
        json={"dept_id": 1}, timeout=15)
    dept_id = r0.json()["result"][0]["dept_id"]

    r = requests.post(f"{OAPI_BASE}/topapi/v2/department/listsubid?access_token={old_token}",
        json={"dept_id": dept_id}, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d.get("errcode") == 0, f"errcode 非 0：{d}"
    assert "dept_id_list" in d.get("result", {}), f"缺少 dept_id_list：{d}"


def test_http_dept_user_list(old_token, my_user_id):
    """获取用户所在部门的成员列表。"""
    # 先拿用户的部门
    ru = requests.post(f"{OAPI_BASE}/topapi/v2/user/get?access_token={old_token}",
        json={"userid": my_user_id}, timeout=15)
    dept_id = ru.json()["result"]["dept_id_list"][0]

    r = requests.post(f"{OAPI_BASE}/topapi/v2/user/list?access_token={old_token}",
        json={"dept_id": dept_id, "cursor": 0, "size": 5,
              "contain_access_limit": False}, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d.get("errcode") == 0, f"errcode 非 0：{d}"
    members = d["result"]["list"]
    assert len(members) > 0, "部门成员不能为空"
    for m in members:
        assert "userid" in m, f"成员缺少 userid：{m}"
        assert "name"   in m, f"成员缺少 name：{m}"


def test_http_dept_user_listid(old_token, my_user_id):
    """获取部门的 userId 列表（简版）。"""
    ru = requests.post(f"{OAPI_BASE}/topapi/v2/user/get?access_token={old_token}",
        json={"userid": my_user_id}, timeout=15)
    dept_id = ru.json()["result"]["dept_id_list"][0]

    r = requests.post(f"{OAPI_BASE}/topapi/user/listid?access_token={old_token}",
        json={"dept_id": dept_id}, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d.get("errcode") == 0, f"errcode 非 0：{d}"
    assert "userid_list" in d.get("result", {}), f"缺少 userid_list：{d}"


def test_http_unionid_to_userid(old_token, operator_id):
    """unionId → userId 转换（topapi/user/getbyunionid）。"""
    r = requests.post(f"{OAPI_BASE}/topapi/user/getbyunionid?access_token={old_token}",
        json={"unionid": operator_id}, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d.get("errcode") == 0, f"errcode 非 0：{d}"
    assert d["result"].get("userid"), f"缺少 userid：{d}"


def test_http_user_dept_path(old_token, my_user_id):
    """获取用户所在部门路径树（从叶部门到根的 dept_id 列表）。"""
    r = requests.post(f"{OAPI_BASE}/topapi/v2/department/listparentbyuser?access_token={old_token}",
        json={"userid": my_user_id}, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d.get("errcode") == 0, f"errcode 非 0：{d}"
    parent_list = d["result"]["parent_list"]
    assert len(parent_list) > 0, "部门路径不应为空"
    assert "parent_dept_id_list" in parent_list[0], f"缺少 parent_dept_id_list：{parent_list}"


def test_http_user_count(old_token):
    """获取企业员工总人数。"""
    r = requests.post(f"{OAPI_BASE}/topapi/user/count?access_token={old_token}",
        json={"only_active": False}, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d.get("errcode") == 0, f"errcode 非 0：{d}"
    assert isinstance(d["result"].get("count"), int), f"count 应为整数：{d}"
    assert d["result"]["count"] > 0, "企业员工数应大于 0"


# ──────────────────────────────────────────────────────────────────
# 完整链路
# ──────────────────────────────────────────────────────────────────

def test_http_full_chain_search_to_detail(api_headers, old_token):
    """完整链路：按姓名搜索 → userId → 获取完整用户详情。"""
    # Step 1: 新版 search → userId 列表
    r1 = requests.post(f"{NEW_BASE}/v1.0/contact/users/search",
        headers=api_headers,
        json={"queryWord": "张", "offset": 0, "size": 3}, timeout=15)
    assert r1.status_code == 200
    user_ids = r1.json().get("list", [])
    if not user_ids:
        pytest.skip("搜索无结果，跳过链路测试")

    # Step 2: 旧版 user/get → 完整详情
    r2 = requests.post(f"{OAPI_BASE}/topapi/v2/user/get?access_token={old_token}",
        json={"userid": user_ids[0]}, timeout=15)
    assert r2.status_code == 200
    d = r2.json()
    assert d.get("errcode") == 0, f"user/get errcode 非 0：{d}"
    result = d["result"]
    assert result.get("name"),   f"搜索到的用户缺少 name：{result}"
    assert result.get("userid") == user_ids[0], "userId 不一致"


def test_http_unionid_to_userid(old_token, operator_id):
    """unionId → userId 反向转换。"""
    r = requests.post(
        f"{OAPI_BASE}/topapi/user/getbyunionid?access_token={old_token}",
        json={"unionid": operator_id}, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d.get("errcode") == 0, f"errcode 非 0：{d}"
    assert d["result"].get("userid"), f"缺少 userid：{d}"


def test_http_dept_path_traversal(old_token, my_user_id):
    """通过 parent_id 递归拼出用户所在部门的完整路径。"""
    ru = requests.post(f"{OAPI_BASE}/topapi/v2/user/get?access_token={old_token}",
        json={"userid": my_user_id}, timeout=15)
    dept_id = ru.json()["result"]["dept_id_list"][0]

    path = []
    current = dept_id
    for _ in range(10):
        rd = requests.post(f"{OAPI_BASE}/topapi/v2/department/get?access_token={old_token}",
            json={"dept_id": current, "language": "zh_CN"}, timeout=15)
        d = rd.json().get("result", {})
        assert d.get("name"), f"部门缺少 name：{d}"
        path.insert(0, d["name"])
        parent = d.get("parent_id")
        if not parent or parent == 1:
            break
        current = parent
    assert len(path) >= 1, "路径至少应有一级部门"


def test_http_full_chain_dept_search_to_members(api_headers, old_token):
    """完整链路：按名搜索部门 → deptId → 部门详情 + 成员列表。"""
    # Step 1: 新版 search dept → deptId 列表
    r1 = requests.post(f"{NEW_BASE}/v1.0/contact/departments/search",
        headers=api_headers,
        json={"queryWord": "部", "offset": 0, "size": 3}, timeout=15)
    assert r1.status_code == 200
    dept_ids = r1.json().get("list", [])
    if not dept_ids:
        pytest.skip("部门搜索无结果，跳过链路测试")

    dept_id = dept_ids[0]

    # Step 2: 旧版 dept/get → 部门详情
    r2 = requests.post(f"{OAPI_BASE}/topapi/v2/department/get?access_token={old_token}",
        json={"dept_id": dept_id, "language": "zh_CN"}, timeout=15)
    assert r2.status_code == 200
    dept = r2.json()
    assert dept.get("errcode") == 0
    assert dept["result"].get("name"), f"部门缺少 name：{dept}"

    # Step 3: 旧版 user/list → 成员（最多取 3 条）
    r3 = requests.post(f"{OAPI_BASE}/topapi/v2/user/list?access_token={old_token}",
        json={"dept_id": dept_id, "cursor": 0, "size": 3,
              "contain_access_limit": False}, timeout=15)
    assert r3.status_code == 200
    assert r3.json().get("errcode") == 0
