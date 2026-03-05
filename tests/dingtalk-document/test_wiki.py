"""
test_wiki.py —— 测试知识库（Wiki）相关接口
  - GET /v2.0/wiki/workspaces
  - GET /v2.0/wiki/nodes/{nodeId}
  - POST /v2.0/wiki/nodes/queryByUrl
  - GET /v2.0/wiki/nodes （列出子节点）

所需权限：Wiki.Node.Read
"""
import os
import requests

BASE = "https://api.dingtalk.com"

# 测试用节点（文档）的 nodeId，可通过 .env 中的 TEST_NODE_ID 覆盖
TEST_NODE_ID = os.environ.get("TEST_NODE_ID", "LeBq413JAw31yaz1fB0BBdLGWDOnGvpb")
TEST_NODE_URL = os.environ.get(
    "TEST_NODE_URL",
    "https://alidocs.dingtalk.com/i/nodes/LeBq413JAw31yaz1fB0BBdLGWDOnGvpb",
)


def test_list_workspaces(api_headers, operator_id):
    """列出当前用户有权限的知识库"""
    resp = requests.get(
        f"{BASE}/v2.0/wiki/workspaces",
        params={"operatorId": operator_id, "maxResults": 10},
        headers=api_headers,
        timeout=15,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "workspaces" in data or "items" in data or isinstance(data, dict), data


def test_get_node_by_id(api_headers, operator_id):
    """通过 nodeId 获取节点详情"""
    resp = requests.get(
        f"{BASE}/v2.0/wiki/nodes/{TEST_NODE_ID}",
        params={"operatorId": operator_id},
        headers=api_headers,
        timeout=15,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    node = data.get("node") or data  # response wrapped in {"node": {...}}
    assert node.get("nodeId") == TEST_NODE_ID, data


def test_get_node_by_url(api_headers, operator_id):
    """通过 URL 查询节点信息"""
    resp = requests.post(
        f"{BASE}/v2.0/wiki/nodes/queryByUrl",
        params={"operatorId": operator_id},
        json={"url": TEST_NODE_URL},
        headers=api_headers,
        timeout=15,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "nodeId" in data or "node" in str(data), data


def test_list_child_nodes(api_headers, operator_id):
    """列出知识库根节点下的子节点（通过 workspaces 接口获取 rootNodeId 作为 parentNodeId）"""
    # 获取工作空间列表，取得 rootNodeId
    ws_resp = requests.get(
        f"{BASE}/v2.0/wiki/workspaces",
        params={"operatorId": operator_id, "maxResults": 5},
        headers=api_headers,
        timeout=15,
    )
    assert ws_resp.status_code == 200, ws_resp.text
    workspaces = ws_resp.json().get("workspaces") or []
    assert workspaces, "没有可用的知识库"

    # 取第一个知识库的 rootNodeId 和 workspaceId
    first_ws = workspaces[0]
    workspace_id = first_ws.get("workspaceId")
    root_node_id = first_ws.get("rootNodeId")
    assert workspace_id and root_node_id, f"工作空间缺少必要字段：{first_ws}"

    resp = requests.get(
        f"{BASE}/v2.0/wiki/nodes",
        params={
            "operatorId": operator_id,
            "workspaceId": workspace_id,
            "parentNodeId": root_node_id,
            "maxResults": 10,
        },
        headers=api_headers,
        timeout=15,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, dict), data
