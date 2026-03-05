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
BASE        = "https://api.dingtalk.com"


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
    return _require_env("OPERATOR_ID")


@pytest.fixture(scope="session")
def api_headers(token):
    return {
        "x-acs-dingtalk-access-token": token,
        "Content-Type": "application/json",
    }
