"""
共享 pytest fixture：accessToken、operatorId
"""
import os
import pathlib
import pytest
import requests

# ── 读取 .env ─────────────────────────────────────────────────────
_env_file = pathlib.Path(__file__).parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            k, _, v = _line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

def _require_env(key: str) -> str:
    val = os.environ.get(key, "")
    if not val:
        import pytest
        pytest.skip(f"缺少环境变量 {key}，请复制 .env.example 为 .env 并填写")
    return val


APP_KEY     = os.environ.get("DINGTALK_APP_KEY", "")
APP_SECRET  = os.environ.get("DINGTALK_APP_SECRET", "")
OPERATOR_ID = os.environ.get("OPERATOR_ID", "")
USER_ID     = os.environ.get("DINGTALK_USER_ID", "")
BASE        = "https://api.dingtalk.com"


def _userid_to_unionid(app_key: str, app_secret: str, user_id: str) -> str:
    """通过旧版 API 将 userId 转换为 unionId。"""
    r = requests.get(
        "https://oapi.dingtalk.com/gettoken",
        params={"appkey": app_key, "appsecret": app_secret},
        timeout=15,
    )
    r.raise_for_status()
    old_token = r.json()["access_token"]
    r2 = requests.post(
        f"https://oapi.dingtalk.com/topapi/v2/user/get?access_token={old_token}",
        json={"userid": user_id},
        timeout=15,
    )
    r2.raise_for_status()
    data = r2.json()
    assert data.get("errcode") == 0, f"userId→unionId 转换失败：{data}"
    return data["result"]["unionid"]  # 注意：无下划线


@pytest.fixture(scope="session")
def token() -> str:
    app_key = _require_env("DINGTALK_APP_KEY")
    app_secret = _require_env("DINGTALK_APP_SECRET")
    resp = requests.post(
        f"{BASE}/v1.0/oauth2/accessToken",
        json={"appKey": app_key, "appSecret": app_secret},
        timeout=15,
    )
    resp.raise_for_status()
    t = resp.json().get("accessToken")
    assert t, f"未获取到 accessToken，响应：{resp.text}"
    return t


@pytest.fixture(scope="session")
def operator_id() -> str:
    """返回操作者 unionId。优先读 OPERATOR_ID，否则从 DINGTALK_USER_ID 自动转换。"""
    if OPERATOR_ID:
        return OPERATOR_ID
    user_id = _require_env("DINGTALK_USER_ID")
    app_key = _require_env("DINGTALK_APP_KEY")
    app_secret = _require_env("DINGTALK_APP_SECRET")
    return _userid_to_unionid(app_key, app_secret, user_id)


@pytest.fixture(scope="session")
def api_headers(token):
    return {
        "x-acs-dingtalk-access-token": token,
        "Content-Type": "application/json",
    }
